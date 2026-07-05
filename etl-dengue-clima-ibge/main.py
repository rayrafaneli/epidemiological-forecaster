"""
main.py
===============================================================================
ORQUESTRADOR DO PIPELINE ETL

O QUE ESTE ARQUIVO FAZ
-----------------------
É o ponto de entrada do projeto. Ele NÃO contém regra de negócio (não sabe
"como" limpar dados do INMET, nem "como" inserir no banco) - ele apenas
CHAMA, na ordem certa, as funções das camadas extract, transform e load.
Essa separação é o que permite testar cada camada isoladamente e trocar
uma peça (ex: trocar PostgreSQL por outro banco) sem reescrever tudo.

ORDEM DE EXECUÇÃO E POR QUE ELA IMPORTA
-----------------------
1) IBGE primeiro: a tabela `municipios` precisa existir antes, porque
   `estacoes_inmet.municipio_codigo_ibge` e `casos_dengue.municipio_codigo_ibge`
   são chaves estrangeiras para ela.
2) INMET depois, e dentro dele: estações antes do clima diário, pela mesma
   razão (FK de clima_diario -> estacoes_inmet).

COMO RODAR
-----------------------
    python main.py --pipeline all       # roda IBGE + INMET uma vez
    python main.py --pipeline ibge      # roda só IBGE
    python main.py --pipeline inmet     # roda só INMET
    python main.py --schedule           # inicia o agendador diário (não retorna)
===============================================================================
"""

import argparse

from src.database.schema_setup import run_ddl
from src.database.connection import test_connection

from src.extract.ibge_extractor import IbgeExtractor
from src.extract.inmet_extractor import InmetExtractor

from src.transform.ibge_transformer import transform_ibge_municipios
from src.transform.inmet_transformer import transform_inmet_stations, transform_inmet_daily

from src.load.postgres_loader import upsert_dataframe
from src.load.etl_log import etl_run

from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)


def run_ibge_pipeline() -> None:
    """Pipeline completo: Extract -> Transform -> Load dos dados do IBGE."""
    with etl_run("ibge") as metrics:
        extractor = IbgeExtractor()

        municipios_raw = extractor.get_municipios(config.ibge.uf)
        metrics["registros_extraidos"] = len(municipios_raw)

        codigos = municipios_raw["codigo_ibge"].tolist() if not municipios_raw.empty else []
        populacao_raw = extractor.get_populacao(codigos) if codigos else municipios_raw
        area_raw = extractor.get_area_territorial(codigos) if codigos else municipios_raw

        municipios_clean = transform_ibge_municipios(municipios_raw, populacao_raw, area_raw)

        resultado = upsert_dataframe(
            df=municipios_clean,
            table_name="municipios",
            unique_columns=["codigo_ibge"],
            update_on_conflict=True,  # população/área podem ser atualizadas em execuções futuras
        )
        metrics["registros_inseridos"] = resultado["linhas_inseridas_ou_atualizadas"]
        metrics["registros_ignorados_duplicados"] = (
            resultado["linhas_recebidas"] - resultado["linhas_inseridas_ou_atualizadas"]
        )


def run_inmet_pipeline() -> None:
    """Pipeline completo: Extract -> Transform -> Load dos dados do INMET."""
    with etl_run("inmet") as metrics:
        extractor = InmetExtractor()

        # 1) Estações primeiro (dependência de chave estrangeira)
        stations_raw = extractor.get_stations(config.ibge.uf)
        stations_clean = transform_inmet_stations(stations_raw)
        upsert_dataframe(
            df=stations_clean,
            table_name="estacoes_inmet",
            unique_columns=["codigo_estacao"],
            update_on_conflict=True,
        )

        # 2) Histórico horário das estações configuradas (a agregação para
        #    diário acontece dentro de transform_inmet_daily). Durante essa
        #    chamada, o extractor também coleta os metadados de cada estação
        #    direto do cabeçalho dos arquivos históricos (ver
        #    InmetExtractor._parse_station_metadata).
        clima_raw = extractor.get_hourly_history(config.inmet.station_codes)
        metrics["registros_extraidos"] = len(clima_raw)

        # 2.1) GARANTIA DE INTEGRIDADE REFERENCIAL: se alguma estação tiver
        #      dado histórico mas não constar na lista "ativa hoje" da API
        #      apitempo usada no passo 1 (ex: desativada/realocada), ela é
        #      inserida aqui a partir do próprio arquivo histórico.
        #      update_on_conflict=False -> só insere quem AINDA NÃO existe,
        #      sem sobrescrever os dados "oficiais" já carregados no passo 1.
        #      Sem este passo, o upsert de clima_diario logo abaixo pode
        #      falhar com "violates foreign key constraint" para qualquer
        #      estação que não esteja na lista de estações "atuais".
        stations_from_history = transform_inmet_stations(
            extractor.get_stations_from_history_metadata()
        )
        upsert_dataframe(
            df=stations_from_history,
            table_name="estacoes_inmet",
            unique_columns=["codigo_estacao"],
            update_on_conflict=False,
        )

        clima_clean = transform_inmet_daily(clima_raw)

        resultado = upsert_dataframe(
            df=clima_clean,
            table_name="clima_diario",
            unique_columns=["codigo_estacao", "data_medicao"],
            update_on_conflict=False,  # histórico diário: não sobrescreve, só ignora duplicata
        )
        metrics["registros_inseridos"] = resultado["linhas_inseridas_ou_atualizadas"]
        metrics["registros_ignorados_duplicados"] = (
            resultado["linhas_recebidas"] - resultado["linhas_inseridas_ou_atualizadas"]
        )


def run_all() -> None:
    logger.info("=== Iniciando pipeline completo (IBGE -> INMET) ===")
    run_ibge_pipeline()
    run_inmet_pipeline()
    logger.info("=== Pipeline completo finalizado ===")


def main():
    parser = argparse.ArgumentParser(description="Pipeline ETL - Clima (INMET) e Municípios (IBGE)")
    parser.add_argument(
        "--pipeline", choices=["all", "ibge", "inmet"], default="all",
        help="Qual pipeline rodar (padrão: all)",
    )
    parser.add_argument(
        "--setup-db", action="store_true",
        help="Executa o DDL (cria as tabelas) antes de rodar o pipeline.",
    )
    parser.add_argument(
        "--schedule", action="store_true",
        help="Inicia o agendador diário em vez de rodar uma única vez.",
    )
    args = parser.parse_args()

    if not test_connection():
        logger.error("Não foi possível conectar ao banco. Verifique o arquivo .env. Abortando.")
        return

    if args.setup_db:
        run_ddl()

    if args.schedule:
        # Importação tardia (só quando necessário) para não obrigar quem
        # roda o pipeline uma vez a ter a lib 'schedule' importada à toa.
        from src.scheduler.daily_job import start_scheduler
        start_scheduler()
        return

    if args.pipeline == "all":
        run_all()
    elif args.pipeline == "ibge":
        run_ibge_pipeline()
    elif args.pipeline == "inmet":
        run_inmet_pipeline()


if __name__ == "__main__":
    main()
