"""
src/load/etl_log.py
===============================================================================
CAMADA: load

O QUE ESTE ARQUIVO FAZ
-----------------------
Fornece um context manager (`etl_run`) que registra automaticamente, na
tabela `etl_execution_log`, o início, o fim, o status (sucesso/falha) e as
métricas de cada execução de um pipeline (INMET ou IBGE).

POR QUE ISSO É IMPORTANTE PARA O TCC?
-----------------------
O requisito pede uma "rotina automática de atualização diária". Para
COMPROVAR, na defesa do TCC, que essa rotina realmente roda todo dia e
funciona, é muito mais forte mostrar uma tabela `etl_execution_log` com o
histórico de execuções do que apenas dizer "ela roda". É evidência.
===============================================================================
"""

from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import text

from src.database.connection import engine
from src.logger import get_logger

logger = get_logger(__name__)


@contextmanager
def etl_run(pipeline_name: str):
    """
    Uso:
        with etl_run("inmet") as run:
            ... roda o pipeline ...
            run["registros_extraidos"] = 500
            run["registros_inseridos"] = 480

    Ao sair do bloco `with` sem exceção -> grava status SUCESSO.
    Se uma exceção acontecer dentro do bloco -> grava status FALHA com a
    mensagem de erro, e RELANÇA a exceção (para o chamador saber que falhou).
    """
    run_metrics = {
        "registros_extraidos": 0,
        "registros_inseridos": 0,
        "registros_ignorados_duplicados": 0,
    }
    started_at = datetime.now()

    try:
        yield run_metrics
    except Exception as exc:
        _persist_log(pipeline_name, started_at, "FALHA", run_metrics, str(exc))
        raise
    else:
        _persist_log(pipeline_name, started_at, "SUCESSO", run_metrics, None)


def _persist_log(pipeline_name, started_at, status, metrics, error_message):
    finished_at = datetime.now()
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO dengue.etl_execution_log
                        (pipeline_name, iniciado_em, finalizado_em, status,
                         registros_extraidos, registros_inseridos,
                         registros_ignorados_duplicados, mensagem_erro)
                    VALUES
                        (:pipeline_name, :iniciado_em, :finalizado_em, :status,
                         :registros_extraidos, :registros_inseridos,
                         :registros_ignorados_duplicados, :mensagem_erro)
                    """
                ),
                {
                    "pipeline_name": pipeline_name,
                    "iniciado_em": started_at,
                    "finalizado_em": finished_at,
                    "status": status,
                    "registros_extraidos": metrics.get("registros_extraidos", 0),
                    "registros_inseridos": metrics.get("registros_inseridos", 0),
                    "registros_ignorados_duplicados": metrics.get("registros_ignorados_duplicados", 0),
                    "mensagem_erro": error_message,
                },
            )
        logger.info(f"[{pipeline_name}] Execução registrada em etl_execution_log com status={status}.")
    except Exception as exc:
        # Se falhar até para registrar o log, apenas logamos - não queremos
        # que um problema na auditoria mascare o resultado real do pipeline.
        logger.error(f"Não foi possível gravar o log de execução: {exc}")
