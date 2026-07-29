"""
src/transform/ibge_transformer.py
===============================================================================
CAMADA: transform

O QUE ESTE ARQUIVO FAZ
-----------------------
Junta (merge) os três DataFrames vindos do IbgeExtractor - municípios,
população e área territorial - em uma única tabela, calcula a densidade
demográfica e valida os dados antes de seguirem para o Load.

POR QUE CALCULAR A DENSIDADE AQUI, E NÃO PEDIR PRONTA AO IBGE?
-----------------------
A densidade demográfica (habitantes / km²) é derivada de duas informações
que já buscamos separadamente (população e área). Calcular localmente
evita uma chamada de API a mais e garante que o número bate exatamente com
os dois componentes que estão salvos no banco (rastreabilidade: dá para
conferir a conta).
===============================================================================
"""

import pandas as pd

from src.logger import get_logger

logger = get_logger(__name__)


def transform_ibge_municipios(
    municipios_df: pd.DataFrame,
    populacao_df: pd.DataFrame,
    area_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combina os três DataFrames pelo código IBGE do município e calcula a
    densidade demográfica. Retorna um DataFrame pronto para a tabela
    `municipios`.
    """
    if municipios_df.empty:
        logger.warning("transform_ibge_municipios recebeu municipios_df vazio.")
        return municipios_df

    df = municipios_df.copy()

    # how="left": mesmo que população ou área não venham (ex: API do SIDRA
    # fora do ar naquele dia), o município ainda é salvo - só com esses
    # campos nulos, que podem ser atualizados numa execução futura.
    if not populacao_df.empty:
        df = df.merge(populacao_df, on="codigo_ibge", how="left")
    else:
        logger.warning("populacao_df vazio - municípios serão salvos sem população.")
        df["populacao_estimada"] = pd.NA
        df["ano_referencia_populacao"] = pd.NA

    if not area_df.empty:
        df = df.merge(area_df, on="codigo_ibge", how="left")
    else:
        logger.warning("area_df vazio - municípios serão salvos sem área territorial.")
        df["area_km2"] = pd.NA

    # Tipagem numérica explícita (o merge pode trazer strings dependendo da API)
    df["populacao_estimada"] = pd.to_numeric(df["populacao_estimada"], errors="coerce")
    df["area_km2"] = pd.to_numeric(df["area_km2"], errors="coerce")

    # ano_referencia_populacao vem como texto (ex: "2024") do SIDRA - convertemos
    # para inteiro (a coluna no banco é SMALLINT). errors="coerce" evita quebrar
    # o pipeline caso algum valor venha em formato inesperado.
    if "ano_referencia_populacao" in df.columns:
        df["ano_referencia_populacao"] = pd.to_numeric(
            df["ano_referencia_populacao"], errors="coerce"
        ).astype("Int64")  # Int64 (maiúsculo) do pandas aceita nulos, ao contrário do int comum

    # Densidade demográfica = população / área. Protegemos contra divisão
    # por zero/NaN usando .where(), que resulta em NaN em vez de erro.
    df["densidade_demografica"] = (df["populacao_estimada"] / df["area_km2"]).where(
        df["area_km2"] > 0
    )

    # VALIDAÇÃO: código IBGE é a chave primária da tabela - não pode faltar.
    antes = len(df)
    df = df.dropna(subset=["codigo_ibge"])
    if len(df) < antes:
        logger.warning(f"{antes - len(df)} linha(s) descartada(s) por falta de codigo_ibge.")

    df["codigo_ibge"] = df["codigo_ibge"].astype("int64")

    colunas_finais = [
        "codigo_ibge", "nome", "uf", "regiao",
        "populacao_estimada", "area_km2", "densidade_demografica",
        "ano_referencia_populacao",
    ]
    colunas_presentes = [c for c in colunas_finais if c in df.columns]
    df = df[colunas_presentes]

    logger.info(f"Transform IBGE concluído: {len(df)} município(s) prontos para carga.")
    return df.reset_index(drop=True)
