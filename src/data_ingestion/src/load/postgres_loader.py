"""
src/load/postgres_loader.py
===============================================================================
CAMADA: load

O QUE ESTE ARQUIVO FAZ
-----------------------
Insere um DataFrame já limpo (vindo da camada transform) em uma tabela do
PostgreSQL, EVITANDO DUPLICIDADE, usando a cláusula nativa do Postgres:

    INSERT INTO tabela (...) VALUES (...)
    ON CONFLICT (colunas_unicas) DO NOTHING   -- ou DO UPDATE

POR QUE NÃO USAR df.to_sql(..., if_exists="append") DIRETO?
-----------------------
`to_sql` com "append" simplesmente insere tudo, e se uma linha já existir
(mesma estação + mesma data, por exemplo), o banco lançaria um erro de
violação da UNIQUE constraint e a carga inteira falharia. Isso é o oposto
do que o requisito pede ("insira apenas novos registros, evitando
duplicidades"). Por isso implementamos um upsert manual usando o driver
psycopg2 (`execute_values`), que é extremamente mais rápido do que inserir
linha a linha, e conseguimos usar `ON CONFLICT`.

POR QUE ESSA CLASSE É "GENÉRICA" (RECEBE nome da tabela, colunas etc.)?
-----------------------
Em vez de escrever uma função load_clima(), outra load_municipios() etc,
quase idênticas, escrevemos uma única função parametrizável. Isso segue o
princípio DRY e facilita adicionar uma nova tabela no futuro (ex: quando a
integração com a Prefeitura do Recife estiver pronta) sem duplicar lógica.
===============================================================================
"""

import math
import numpy as np
import pandas as pd
from psycopg2.extras import execute_values

from src.database.connection import engine
from src.logger import get_logger

logger = get_logger(__name__)


def _sanitize_value(value):
    """
    Converte valores do pandas/numpy (NaN, NaT, np.int64, np.float64...)
    para tipos nativos do Python que o psycopg2 sabe serializar.

    Por que isso é necessário?
    Quando o pandas lê uma coluna inteira (ex: codigo_ibge), cada valor
    individual não é um "int" comum do Python - é um "numpy.int64". O
    psycopg2 não sabe, por padrão, como transformar um numpy.int64 em algo
    que o PostgreSQL entenda, e lança o erro "can't adapt type 'numpy.int64'".
    O mesmo vale para numpy.float64 e numpy.bool_. Por isso, para qualquer
    valor numérico do numpy, chamamos `.item()`, que converte para o tipo
    nativo equivalente do Python (int, float ou bool).
    """
    if value is None:
        return None
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        value = value.item()  # numpy.int64(5) -> 5 (int nativo do Python)
        if isinstance(value, float) and math.isnan(value):
            return None
        return value
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    return value


def upsert_dataframe(
    df: pd.DataFrame,
    table_name: str,
    unique_columns: list[str],
    update_on_conflict: bool = False,
    schema: str = "dengue",
) -> dict:
    """
    Insere as linhas de `df` na tabela `schema.table_name`, ignorando (ou
    atualizando, se update_on_conflict=True) linhas que já existirem
    segundo `unique_columns`.

    Parâmetros
    ----------
    df : DataFrame já limpo, cujas colunas têm EXATAMENTE os mesmos nomes
         das colunas da tabela de destino.
    table_name : nome da tabela, sem o schema (ex: "clima_diario").
    unique_columns : colunas que formam a constraint UNIQUE da tabela
         (ex: ["codigo_estacao", "data_medicao"]). É contra essa
         combinação que o ON CONFLICT vai verificar duplicidade.
    update_on_conflict : se True, atualiza as colunas não-chave quando o
         registro já existe (útil para dados que podem ser corrigidos,
         como o INMET revisando uma medição). Se False, apenas ignora
         (DO NOTHING) - comportamento padrão para clima/casos históricos.

    Retorna um dicionário com métricas da carga (extraídos, inseridos etc),
    usado depois para popular a tabela `etl_execution_log`.
    """
    resultado = {"linhas_recebidas": len(df), "linhas_inseridas_ou_atualizadas": 0}

    if df.empty:
        logger.warning(f"[{table_name}] DataFrame vazio - nada para carregar.")
        return resultado

    colunas = list(df.columns)
    colunas_sql = ", ".join(colunas)
    placeholders = ", ".join(colunas)  # usado só para gerar a lista de %s dinamicamente

    conflict_cols_sql = ", ".join(unique_columns)

    if update_on_conflict:
        colunas_para_atualizar = [c for c in colunas if c not in unique_columns]
        set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in colunas_para_atualizar)
        on_conflict_sql = f"ON CONFLICT ({conflict_cols_sql}) DO UPDATE SET {set_clause}"
    else:
        on_conflict_sql = f"ON CONFLICT ({conflict_cols_sql}) DO NOTHING"

    insert_sql = (
        f"INSERT INTO {schema}.{table_name} ({colunas_sql}) VALUES %s "
        f"{on_conflict_sql}"
    )

    # Converte o DataFrame em uma lista de tuplas, já "sanitizadas"
    # (NaN -> None), que é o formato que execute_values espera.
    valores = [
        tuple(_sanitize_value(v) for v in row)
        for row in df[colunas].itertuples(index=False, name=None)
    ]

    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            # execute_values monta um único comando INSERT com múltiplos
            # VALUES (...), (...), (...) - muito mais rápido do que rodar
            # um INSERT por linha (que geraria uma viagem de rede por linha).
            execute_values(cursor, insert_sql, valores, page_size=1000)
            linhas_afetadas = cursor.rowcount
        raw_conn.commit()
        resultado["linhas_inseridas_ou_atualizadas"] = linhas_afetadas
        logger.info(
            f"[{table_name}] {len(valores)} linha(s) processada(s); "
            f"{linhas_afetadas} efetivamente inserida(s)/atualizada(s) "
            f"({len(valores) - linhas_afetadas} já existiam e foram ignoradas)."
        )
    except Exception as exc:
        raw_conn.rollback()
        logger.error(f"[{table_name}] Erro durante o upsert: {exc}")
        raise
    finally:
        raw_conn.close()

    return resultado
