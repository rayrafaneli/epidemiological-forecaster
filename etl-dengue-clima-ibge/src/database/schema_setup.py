"""
src/database/schema_setup.py
===============================================================================
CAMADA: database

O QUE ESTE ARQUIVO FAZ
-----------------------
Lê o arquivo sql/ddl.sql e executa seu conteúdo no banco configurado no
.env. É uma alternativa conveniente a rodar `psql -f sql/ddl.sql` na mão -
útil especialmente em ambientes Windows, onde nem todo mundo tem o psql
no PATH.

Este script é IDEMPOTENTE: como o DDL usa "CREATE TABLE IF NOT EXISTS",
rodá-lo várias vezes não causa erro nem duplica nada.
===============================================================================
"""

from pathlib import Path
from sqlalchemy import text

from src.database.connection import engine
from src.logger import get_logger

logger = get_logger(__name__)

DDL_PATH = Path(__file__).resolve().parent.parent.parent / "sql" / "ddl.sql"


def run_ddl() -> None:
    logger.info(f"Lendo script DDL em: {DDL_PATH}")
    sql_script = DDL_PATH.read_text(encoding="utf-8")

    # O driver psycopg2 não executa múltiplos comandos separados por ";"
    # de uma vez através do SQLAlchemy 'text()' de forma confiável em todas
    # as versões, então usamos a conexão bruta (raw connection) e deixamos
    # o psycopg2 processar o script inteiro, que já sabe lidar com isso.
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            cursor.execute(sql_script)
        raw_conn.commit()
        logger.info("DDL executado com sucesso. Tabelas criadas/atualizadas.")
    except Exception as exc:
        raw_conn.rollback()
        logger.error(f"Erro ao executar o DDL: {exc}")
        raise
    finally:
        raw_conn.close()


if __name__ == "__main__":
    # Uso: python -m src.database.schema_setup
    run_ddl()
