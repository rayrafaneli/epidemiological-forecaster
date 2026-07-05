"""
src/extract/inmet_extractor.py
===============================================================================
CAMADA: extract

O QUE ESTE ARQUIVO FAZ
-----------------------
Busca duas coisas no INMET, usando DUAS fontes diferentes (explicado abaixo):

1) get_stations(uf)            -> metadados das estações automáticas (API "apitempo")
2) get_hourly_history(...)     -> série histórica horária, lida dos pacotes
                                    anuais oficiais em ZIP (portal.inmet.gov.br)

POR QUE DUAS FONTES DIFERENTES PARA O INMET?
-----------------------
A API "apitempo.inmet.gov.br" tem dois tipos de endpoint:
  - /estacoes/T           -> metadados das estações (nome, UF, lat/lon...).
                             Este CONTINUA funcionando (testado e confirmado).
  - /estacao/diaria/...   -> histórico diário "pronto".
                             Este endpoint foi DESCONTINUADO/alterado pelo
                             INMET (confirmado: retorna 404 mesmo com a URL
                             documentada). Vários pacotes de terceiros que
                             dependiam dele estão marcados como "deprecated".

Por isso, para o HISTÓRICO (o que realmente importa para o TCC: dados desde
2021), usamos a fonte oficial e estável feita exatamente para isso: os
pacotes anuais do BDMEP (Banco de Dados Meteorológicos para Ensino e
Pesquisa), publicados em:

    https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip

Cada ZIP contém um arquivo CSV por estação meteorológica do Brasil inteiro,
com dados HORÁRIOS daquele ano. É essa a fonte de dados usada por
pesquisadores e outros projetos acadêmicos brasileiros que trabalham com
dados do INMET - portanto, mais estável para um TCC do que uma API que já
demonstrou mudar sem aviso.

Como o CSV é horário, e nosso banco guarda dados DIÁRIOS (ver sql/ddl.sql),
a agregação hora -> dia acontece na camada transform
(src/transform/inmet_transformer.py), não aqui. Aqui só extraímos e
padronizamos nomes de coluna - é papel do Extract entregar dado estruturado,
não ainda validado/agregado.

ATENÇÃO (IMPORTANTE PARA QUEM FOR RODAR/AJUSTAR):
-----------------------
- Cada ZIP anual tem dezenas de MB (todas as estações do Brasil). O download
  pode demorar um pouco - é normal.
- O layout exato das colunas do CSV pode variar ligeiramente entre anos
  (o próprio INMET já mudou nomes de coluna ao longo do tempo). A função
  `_rename_inmet_column` mapeia por padrão (regex) em vez de nome exato,
  para tolerar pequenas variações.
===============================================================================
"""

import io
import re
import zipfile
from datetime import date

import pandas as pd

from src.extract.base_extractor import BaseExtractor
from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)

# Quantas colunas do CSV original vamos considerar. O arquivo tem uma coluna
# extra "vazia" no final (por causa de um ';' sobrando no cabeçalho da fonte
# original) - por isso lemos só as 19 primeiras, prática documentada por
# quem já trabalhou com esses arquivos.
COLUNAS_CSV_ESPERADAS = 19

# Quantas linhas de metadados existem antes da tabela de dados propriamente
# dita (região, UF, nome da estação, código OMM, latitude, longitude,
# altitude, data de fundação).
LINHAS_METADADOS = 8


def _rename_inmet_column(nome_coluna: str) -> str:
    """
    Padroniza os nomes de coluna (verbosos e em português) do CSV do INMET
    para nomes curtos em snake_case. Usamos REGEX (padrão), não igualdade
    exata, porque o INMET já mudou pequenos detalhes de acentuação/redação
    dessas colunas ao longo dos anos - casar por padrão é mais resiliente.

    Colunas que não reconhecemos (radiação, direção do vento, etc.) são
    mantidas com o nome original e simplesmente ignoradas mais adiante,
    pois não são necessárias para o cruzamento com dengue neste projeto.
    """
    nome = nome_coluna.lower().strip()
    if re.match(r"^data", nome):
        return "data"
    if re.match(r"^hora", nome):
        return "hora"
    if re.match(r"precipita[çc][ãa]o", nome):
        return "precipitacao"
    if re.match(r"press[ãa]o atmosf[ée]rica ao n[íi]vel", nome):
        return "pressao_atmosferica"
    if re.match(r"temperatura do ar", nome):
        return "temperatura_ar"
    if re.match(r"umidade relativa do ar", nome):
        return "umidade_relativa"
    if re.match(r"vento, velocidade", nome):
        return "vento_velocidade"
    return nome_coluna  # coluna não usada - mantém nome original, será descartada depois


class InmetExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()
        self.base_url = config.inmet.base_url
        self.historical_data_base_url = config.inmet.historical_data_base_url
        # Guarda os metadados de cada estação (nome, UF, lat/lon, altitude,
        # data de fundação) lidos do CABEÇALHO dos próprios arquivos
        # históricos, coletados como efeito colateral de get_hourly_history().
        # Ver get_stations_from_history_metadata() e o comentário lá embaixo
        # sobre por que isso é necessário (evita violação de FK em clima_diario).
        self.station_metadata_from_history: dict[str, dict] = {}

    def get_stations(self, uf: str) -> pd.DataFrame:
        """
        Busca os metadados das estações automáticas.

        Endpoint: /estacoes/T  (T = estações automáticas, M = manuais)
        - devolve TODAS as estações do Brasil; filtramos por UF aqui no
          Python usando a coluna "SG_ESTADO". Confirmado funcionando.
        """
        url = f"{self.base_url}/estacoes/T"
        logger.info(f"Buscando todas as estações automáticas do INMET (filtrando depois por UF={uf})...")
        raw = self._get(url)

        if not raw:
            logger.warning("Nenhuma estação retornada pela API do INMET.")
            return pd.DataFrame()

        df = pd.DataFrame(raw)

        if "SG_ESTADO" in df.columns:
            df = df[df["SG_ESTADO"] == uf].reset_index(drop=True)
        else:
            logger.warning(
                "Coluna 'SG_ESTADO' não encontrada na resposta da API - "
                "retornando todas as estações sem filtrar por UF."
            )

        logger.info(f"{len(df)} estação(ões) encontrada(s) para UF={uf}.")
        return df

    def _download_year_zip(self, year: int) -> bytes:
        """Baixa o pacote anual de dados históricos (todas as estações do Brasil)."""
        url = f"{self.historical_data_base_url}/{year}.zip"
        logger.info(f"Baixando pacote de dados históricos do INMET para o ano {year}...")
        conteudo = self._get_bytes(url)
        logger.info(f"Ano {year}: download concluído ({len(conteudo) / 1_000_000:.1f} MB).")
        return conteudo

    def _find_station_files(self, zip_bytes: bytes, station_codes: list[str]) -> dict[str, str]:
        """
        Localiza, dentro do ZIP, o arquivo CSV de cada estação desejada.
        Os nomes de arquivo seguem o padrão:
            INMET_<REGIAO>_<UF>_<CODIGO_ESTACAO>_<NOME_ESTACAO>_<DATA_INI>_<DATA_FIM>.CSV
        Por isso procuramos pelo código da estação cercado por "_" no nome
        do arquivo, para não confundir "A301" com "A3010", por exemplo.
        """
        encontrados: dict[str, str] = {}
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            nomes_arquivos = zf.namelist()
            for codigo in station_codes:
                for nome_arquivo in nomes_arquivos:
                    if f"_{codigo}_" in nome_arquivo.upper():
                        encontrados[codigo] = nome_arquivo
                        break
        return encontrados

    def _read_station_csv(self, zip_bytes: bytes, filename: str, station_code: str) -> pd.DataFrame:
        """
        Lê o CSV de uma estação específica de dentro do ZIP (sem precisar
        extrair para o disco), já renomeando as colunas conhecidas.
        """
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            with zf.open(filename) as arquivo:
                df = pd.read_csv(
                    arquivo,
                    sep=";",
                    decimal=",",
                    na_values=["-9999", "-9999,0", ""],
                    encoding="latin-1",
                    skiprows=LINHAS_METADADOS,
                    usecols=range(COLUNAS_CSV_ESPERADAS),
                )
        df = df.rename(columns=_rename_inmet_column)
        df["codigo_estacao"] = station_code
        return df

    def _parse_station_metadata(self, zip_bytes: bytes, filename: str, station_code: str) -> dict:
        """
        Lê as LINHAS_METADADOS (8) linhas que ficam ANTES da tabela de dados
        no CSV de uma estação (região, UF, nome, código OMM, latitude,
        longitude, altitude, data de fundação) e devolve como dict, já no
        formato de coluna usado por `transform_inmet_stations`.

        POR QUE ISSO EXISTE (leia antes de remover "por achar redundante"):
        `estacoes_inmet.codigo_estacao` é referenciado por
        `clima_diario.codigo_estacao` (chave estrangeira). Se uma estação
        configurada em INMET_STATION_CODES tiver dado histórico no ZIP anual,
        mas NÃO aparecer na lista de estações "automáticas ativas hoje" da
        API apitempo (`get_stations`) - por exemplo, por ter sido desativada,
        reclassificada ou realocada -, o INSERT em clima_diario falha com
        "violates foreign key constraint", porque a estação nunca chegou a
        ser inserida em estacoes_inmet. Lendo os metadados direto do próprio
        arquivo histórico (que sempre existe, já que é de lá que vieram os
        dados de clima), garantimos que toda estação com dado climático
        também tenha uma linha correspondente em estacoes_inmet.
        """
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            with zf.open(filename) as arquivo:
                linhas_metadados = [
                    arquivo.readline().decode("latin-1").strip()
                    for _ in range(LINHAS_METADADOS)
                ]

        def _valor(linha: str, numerico: bool = False) -> str | None:
            """Extrai o valor após o ';' de uma linha 'CHAVE:;valor'. Números
            no arquivo do INMET usam vírgula decimal (padrão BR) - convertemos
            para ponto, senão pd.to_numeric() descartaria o valor como NaN."""
            if ";" not in linha:
                return None
            valor = linha.split(";", 1)[1].strip().strip(";")
            return valor.replace(",", ".") if numerico else valor

        return {
            "codigo_estacao": station_code,
            "uf": _valor(linhas_metadados[1]),
            "nome": _valor(linhas_metadados[2]),
            "latitude": _valor(linhas_metadados[4], numerico=True),
            "longitude": _valor(linhas_metadados[5], numerico=True),
            "altitude_m": _valor(linhas_metadados[6], numerico=True),
            "data_inicio_operacao": _valor(linhas_metadados[7]),
            # Não sabemos a situação atual (Operante/Pane) só pelo arquivo
            # histórico - marcamos explicitamente em vez de inventar um
            # valor. IMPORTANTE: estacoes_inmet.situacao é VARCHAR(20) no
            # DDL (ver sql/ddl.sql) - o texto aqui precisa caber nesse limite.
            "situacao": "HISTORICO",
        }

    def get_stations_from_history_metadata(self) -> pd.DataFrame:
        """
        Devolve, como DataFrame pronto para `transform_inmet_stations`, os
        metadados coletados como efeito colateral de `get_hourly_history()`.
        Chame DEPOIS de `get_hourly_history()` (senão vem vazio).
        """
        if not self.station_metadata_from_history:
            return pd.DataFrame()
        return pd.DataFrame(self.station_metadata_from_history.values())

    def get_hourly_history(
        self,
        station_codes: list[str] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> pd.DataFrame:
        """
        Busca o histórico HORÁRIO das estações informadas, ano a ano, a
        partir dos pacotes oficiais do INMET. A agregação para dados
        DIÁRIOS acontece na camada transform.
        """
        station_codes = station_codes or config.inmet.station_codes
        start_year = start_year or int(config.inmet.start_date[:4])
        end_year = end_year or date.today().year

        frames: list[pd.DataFrame] = []

        for year in range(start_year, end_year + 1):
            try:
                zip_bytes = self._download_year_zip(year)
            except Exception as exc:
                # Um ano com problema (ex: arquivo daquele ano fora do ar)
                # não deve impedir os demais anos de serem processados.
                logger.error(f"Falha ao baixar o pacote do ano {year}: {exc}. Pulando este ano.")
                continue

            arquivos_por_estacao = self._find_station_files(zip_bytes, station_codes)
            faltantes = set(station_codes) - set(arquivos_por_estacao)
            if faltantes:
                logger.warning(
                    f"Ano {year}: estação(ões) {sorted(faltantes)} não encontrada(s) no pacote "
                    f"(pode não ter operado nesse ano, ou o código mudou)."
                )

            for codigo, nome_arquivo in arquivos_por_estacao.items():
                # Só precisa ler o cabeçalho de metadados uma vez por estação
                # (não muda de ano para ano) - por isso o cache no dict.
                if codigo not in self.station_metadata_from_history:
                    try:
                        self.station_metadata_from_history[codigo] = self._parse_station_metadata(
                            zip_bytes, nome_arquivo, codigo
                        )
                    except Exception as exc:
                        logger.warning(
                            f"Não foi possível ler os metadados da estação {codigo} (ano {year}): {exc}."
                        )
                try:
                    df_estacao = self._read_station_csv(zip_bytes, nome_arquivo, codigo)
                    frames.append(df_estacao)
                    logger.info(f"Ano {year}, estação {codigo}: {len(df_estacao)} registro(s) horário(s) lidos.")
                except Exception as exc:
                    logger.error(f"Falha ao ler o CSV da estação {codigo} no ano {year}: {exc}.")

        if not frames:
            logger.warning("Nenhum dado histórico foi obtido para as estações solicitadas.")
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    # Uso: python -m src.extract.inmet_extractor
    # Ajuda a inspecionar rapidamente o formato bruto retornado.
    extractor = InmetExtractor()
    stations_df = extractor.get_stations(config.ibge.uf)
    print(stations_df.head())

    if not stations_df.empty:
        sample_code = stations_df.iloc[0]["CD_ESTACAO"]
        # Baixa só 1 ano para o teste manual não demorar demais.
        history_df = extractor.get_hourly_history([sample_code], start_year=2024, end_year=2024)
        print(history_df.head())
        print(history_df.columns.tolist())
