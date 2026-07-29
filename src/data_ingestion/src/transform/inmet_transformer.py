"""
src/transform/inmet_transformer.py
===============================================================================
CAMADA: transform

O QUE ESTE ARQUIVO FAZ
-----------------------
Recebe o DataFrame HORÁRIO devolvido pelo InmetExtractor.get_hourly_history()
e:
1) Limpa e tipa os dados (datas, números, valor sentinela -9999 -> nulo)
2) AGREGA de horário para diário (é isso que vai para o banco - ver
   sql/ddl.sql, tabela `clima_diario`)
3) Valida faixas fisicamente plausíveis, descartando outliers

POR QUE AGREGAR AQUI (TRANSFORM) E NÃO NO EXTRACT?
-----------------------
O Extract entrega dado "cru, mas estruturado" (achou o CSV certo, leu,
renomeou colunas). Decidir COMO resumir 24 horas em 1 dia (média? soma?
máximo?) já é uma regra de negócio/qualidade de dados - e regra de negócio
é responsabilidade do Transform, não do Extract.
===============================================================================
"""

import pandas as pd

from src.logger import get_logger

logger = get_logger(__name__)

# Colunas horárias que esperamos existir após o rename feito no Extract.
COLUNAS_NUMERICAS_HORARIAS = [
    "precipitacao", "pressao_atmosferica", "temperatura_ar", "umidade_relativa", "vento_velocidade",
]


def transform_inmet_daily(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Ponto de entrada da transformação. Recebe o DataFrame horário bruto e
    devolve um DataFrame DIÁRIO já limpo, pronto para o Load, com as
    colunas da tabela `clima_diario` (exceto `id` e `criado_em`, gerados
    pelo banco).
    """
    if df_raw.empty:
        logger.warning("transform_inmet_daily recebeu um DataFrame vazio. Nada a transformar.")
        return df_raw

    df = df_raw.copy()
    linhas_horarias_antes = len(df)

    # 1) Data: o CSV do INMET traz "data" e "hora" separados; para dado
    #    DIÁRIO só precisamos da data (a hora já cumpriu seu papel de
    #    diferenciar as leituras dentro do mesmo dia, para a agregação).
    if "data" not in df.columns:
        logger.error("Coluna 'data' não encontrada nos dados brutos do INMET - abortando transformação.")
        return pd.DataFrame()

    df["data_medicao"] = pd.to_datetime(df["data"], errors="coerce").dt.date

    # 2) Tipagem numérica. O CSV já usa "-9999" como valor de "sem medição"
    #    e o Extract já configurou pandas para ler isso como NaN
    #    (na_values=["-9999", ...]) - aqui só reforçamos a conversão numérica
    #    de colunas que possam ter vindo como texto.
    for col in COLUNAS_NUMERICAS_HORARIAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            logger.warning(f"Coluna horária '{col}' não encontrada nos dados brutos do INMET.")

    # 3) VALIDAÇÃO: descarta linhas sem chave de negócio (estação + data).
    antes_validacao = len(df)
    df = df.dropna(subset=["codigo_estacao", "data_medicao"])
    descartadas_chave = antes_validacao - len(df)
    if descartadas_chave:
        logger.warning(f"{descartadas_chave} linha(s) horária(s) descartada(s) por falta de estação/data.")

    if df.empty:
        logger.warning("Após a validação de chave, não sobrou nenhuma linha horária para agregar.")
        return df

    # 4) AGREGAÇÃO horária -> diária.
    #    - temperatura: máxima, mínima e média do dia, a partir da
    #      temperatura instantânea horária.
    #    - precipitação: SOMA das leituras horárias (cada leitura já é o
    #      total chovido naquela hora), resultando no total do dia.
    #      min_count=1 garante que, se TODAS as horas do dia estiverem
    #      nulas, o resultado seja nulo (não zero “falso”).
    #    - umidade, vento, pressão: média do dia.
    agrupado = df.groupby(["codigo_estacao", "data_medicao"])
    colunas_agregadas = {}
    if "temperatura_ar" in df.columns:
        colunas_agregadas["temp_max_c"] = agrupado["temperatura_ar"].max()
        colunas_agregadas["temp_min_c"] = agrupado["temperatura_ar"].min()
        colunas_agregadas["temp_media_c"] = agrupado["temperatura_ar"].mean()
    if "precipitacao" in df.columns:
        colunas_agregadas["precipitacao_total_mm"] = agrupado["precipitacao"].sum(min_count=1)
    if "umidade_relativa" in df.columns:
        colunas_agregadas["umidade_relativa_media_pct"] = agrupado["umidade_relativa"].mean()
    if "vento_velocidade" in df.columns:
        colunas_agregadas["velocidade_vento_media_ms"] = agrupado["vento_velocidade"].mean()
    if "pressao_atmosferica" in df.columns:
        colunas_agregadas["pressao_atm_media_mb"] = agrupado["pressao_atmosferica"].mean()

    diario = pd.DataFrame(colunas_agregadas).reset_index()

    # 5) VALIDAÇÃO: faixas fisicamente plausíveis, descartando outliers
    #    claramente errados (erro de sensor/transmissão).
    if "temp_max_c" in diario.columns:
        fora_da_faixa = diario["temp_max_c"].notna() & ~diario["temp_max_c"].between(-10, 55)
        if fora_da_faixa.any():
            logger.warning(f"{fora_da_faixa.sum()} dia(s) com temp_max_c fora da faixa plausível (-10 a 55°C) zerado(s).")
            diario.loc[fora_da_faixa, "temp_max_c"] = pd.NA

    if "precipitacao_total_mm" in diario.columns:
        negativa = diario["precipitacao_total_mm"].notna() & (diario["precipitacao_total_mm"] < 0)
        if negativa.any():
            logger.warning(f"{negativa.sum()} dia(s) com precipitação negativa zerado(s).")
            diario.loc[negativa, "precipitacao_total_mm"] = pd.NA

    diario["fonte"] = "INMET"

    logger.info(
        f"Transform INMET concluído: {linhas_horarias_antes} leitura(s) horária(s) "
        f"-> {len(diario)} dia(s)-estação válido(s)."
    )
    return diario.reset_index(drop=True)


def transform_inmet_stations(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma os metadados brutos das estações (InmetExtractor.get_stations)
    para o formato da tabela `estacoes_inmet`.

    Por que essa transformação existe separada da de clima diário?
    Porque `clima_diario.codigo_estacao` é uma chave estrangeira para
    `estacoes_inmet.codigo_estacao` (ver DDL). Ou seja: as estações
    PRECISAM ser carregadas antes do clima, senão o banco rejeita a
    inserção por violação de integridade referencial. Essa ordem é
    garantida no orquestrador (main.py).
    """
    if df_raw.empty:
        return df_raw

    df = df_raw.copy()
    rename_map = {
        "CD_ESTACAO": "codigo_estacao",
        "DC_NOME": "nome",
        "SG_ESTADO": "uf",
        "VL_LATITUDE": "latitude",
        "VL_LONGITUDE": "longitude",
        "VL_ALTITUDE": "altitude_m",
        "DT_INICIO_OPERACAO": "data_inicio_operacao",
        "CD_SITUACAO": "situacao",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    colunas_finais = [
        "codigo_estacao", "nome", "uf", "latitude", "longitude",
        "altitude_m", "data_inicio_operacao", "situacao",
    ]
    df = df[[c for c in colunas_finais if c in df.columns]]

    # VALIDAÇÃO: sem código da estação não há como relacionar com o clima.
    df = df.dropna(subset=["codigo_estacao"])

    for col in ["latitude", "longitude", "altitude_m"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "data_inicio_operacao" in df.columns:
        df["data_inicio_operacao"] = pd.to_datetime(
            df["data_inicio_operacao"], errors="coerce"
        ).dt.date

    df = df.drop_duplicates(subset=["codigo_estacao"], keep="last")
    logger.info(f"Transform de estações INMET concluído: {len(df)} estação(ões).")
    return df.reset_index(drop=True)
