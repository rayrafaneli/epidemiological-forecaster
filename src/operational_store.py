"""Persistencia PostgreSQL/Supabase usada pelo pipeline operacional."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert


POPULATION_TABLE = "ef_ibge_populacao_bairro"
CLIMATE_TABLE = "ef_inmet_semanal_recife"
DENGUE_WEEKLY_TABLE = "ef_dengue_semanal_bairro"
PREDICTION_TABLE = "ef_previsoes_xgboost_dashboard"
METRICS_TABLE = "ef_metricas_xgboost"
PIPELINE_RUN_TABLE = "ef_pipeline_execucoes"


def create_database_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True, pool_recycle=300)


def execute_migration(engine, migration_path: Path) -> None:
    sql = migration_path.read_text(encoding="utf-8")
    with engine.begin() as connection:
        connection.exec_driver_sql(sql)


def _database_records(frame: pd.DataFrame) -> list[dict]:
    cleaned = frame.copy()
    cleaned = cleaned.replace({np.nan: None})
    records = cleaned.to_dict(orient="records")
    for record in records:
        for key, value in list(record.items()):
            if pd.isna(value) if not isinstance(value, (list, dict, tuple)) else False:
                record[key] = None
            elif isinstance(value, np.generic):
                record[key] = value.item()
    return records


def upsert_frame(engine, table_name: str, frame: pd.DataFrame, key_columns: list[str]) -> int:
    """Faz upsert em lotes sem criar SQL a partir de nomes fornecidos externamente."""
    if frame.empty:
        return 0
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    valid_columns = [column.name for column in table.columns]
    missing_keys = set(key_columns).difference(valid_columns)
    if missing_keys:
        raise ValueError(f"Chaves inexistentes em {table_name}: {sorted(missing_keys)}")
    selected = frame[[column for column in frame.columns if column in valid_columns]].copy()
    records = _database_records(selected)
    update_columns = [column for column in selected.columns if column not in key_columns]
    total = 0
    with engine.begin() as connection:
        for start in range(0, len(records), 1000):
            batch = records[start : start + 1000]
            statement = postgresql_insert(table).values(batch)
            statement = statement.on_conflict_do_update(
                index_elements=key_columns,
                set_={column: getattr(statement.excluded, column) for column in update_columns},
            )
            connection.execute(statement)
            total += len(batch)
    return total


def read_table(engine, table_name: str) -> pd.DataFrame:
    return pd.read_sql_table(table_name, engine)


def read_production_predictions(engine) -> pd.DataFrame:
    return pd.read_sql_query(
        text(f"SELECT * FROM {PREDICTION_TABLE} WHERE modo_resultado = :mode"),
        engine,
        params={"mode": "producao"},
    )


def record_pipeline_run(
    engine,
    status: str,
    details: str,
    origin_week: str | None = None,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {PIPELINE_RUN_TABLE} (status, detalhes, semana_origem)
                VALUES (:status, :details, :origin_week)
                """
            ),
            {"status": status, "details": details, "origin_week": origin_week},
        )
