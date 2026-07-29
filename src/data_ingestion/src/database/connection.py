"""
src/database/connection.py
===============================================================================
CAMADA: database (infraestrutura de acesso a dados)

O QUE ESTE ARQUIVO FAZ
-----------------------
Cria e expõe UMA ÚNICA "engine" do SQLAlchemy - o objeto responsável por
gerenciar o pool de conexões com o PostgreSQL. Todo o resto do projeto
(camada load, scheduler, etc.) importa essa engine em vez de criar a sua
própria conexão.

POR QUE UMA ENGINE SÓ (E NÃO UMA CONEXÃO NOVA A CADA OPERAÇÃO)?
-----------------------
Abrir uma conexão TCP com o banco é uma operação relativamente cara. A
`Engine` do SQLAlchemy mantém um "pool" de conexões já abertas e as
reaproveita, o que deixa o pipeline mais rápido e evita esgotar o limite
de conexões do PostgreSQL.
===============================================================================
"""

from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)

# echo=False -> não imprime todo SQL executado (deixe True só quando for debugar)
# pool_pre_ping=True -> antes de reusar uma conexão do pool, o SQLAlchemy
#   testa se ela ainda está viva. Evita erros de "conexão perdida" em
#   pipelines que rodam por longos períodos (como o scheduler diário).
engine = create_engine(
    config.db.sqlalchemy_url,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

# sessionmaker cria uma "fábrica" de sessões. Uma Session é o objeto que
# usamos para conversar com o banco de forma transacional (commit/rollback).
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def get_session():
    """
    Context manager que entrega uma Session pronta para uso e garante que:
    - em caso de sucesso -> commit automático
    - em caso de exceção -> rollback automático (nenhuma escrita parcial fica no banco)
    - ao final -> a conexão é sempre devolvida ao pool (session.close())

    Uso típico:
        with get_session() as session:
            session.execute(...)
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_connection() -> bool:
    """
    Testa se conseguimos falar com o banco. Útil para rodar logo depois de
    configurar o .env, antes de tentar rodar o pipeline inteiro.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexão com o PostgreSQL estabelecida com sucesso.")
        return True
    except Exception as exc:
        logger.error(f"Falha ao conectar no PostgreSQL: {exc}")
        return False


if __name__ == "__main__":
    # Permite testar a conexão isoladamente: python -m src.database.connection
    test_connection()
