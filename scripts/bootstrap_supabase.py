"""Cria o schema operacional e envia somente os dados necessários à aplicação."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from src.config import CRITICALITY_RESULTS_DIR, DATA_DIR, PROJECT_ROOT
from src.operational_store import (
    CLIMATE_TABLE,
    DENGUE_WEEKLY_TABLE,
    METRICS_TABLE,
    POPULATION_TABLE,
    PREDICTION_TABLE,
    create_database_engine,
    execute_migration,
    upsert_frame,
)


def dengue_weekly_export() -> pd.DataFrame:
    panel = pd.read_csv(
        DATA_DIR / "painel_semanal_2015_2021_h1.csv",
        usecols=["bairro_norm", "epi_year", "epi_week", "time_index", "casos_totais"],
    )
    weekly = panel.drop_duplicates(["bairro_norm", "epi_year", "epi_week"]).copy()
    weekly["casos_totais"] = pd.to_numeric(weekly["casos_totais"], errors="raise").astype(int)
    weekly["atualizado_em"] = datetime.now().astimezone().isoformat(timespec="seconds")
    return weekly


def historical_predictions() -> pd.DataFrame:
    frame = pd.read_csv(CRITICALITY_RESULTS_DIR / "previsoes_xgboost_dashboard.csv")
    historical = frame["modo_resultado"].eq("validacao_historica_2021")
    if "status_avaliacao" not in frame:
        frame["status_avaliacao"] = "Pendente"
    if "data_avaliacao" not in frame:
        frame["data_avaliacao"] = pd.NA
    frame.loc[historical, "status_avaliacao"] = "Consolidado"
    frame.loc[historical, "data_avaliacao"] = frame.loc[historical, "data_geracao"]
    return frame


def validation_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    comparison = pd.read_csv(CRITICALITY_RESULTS_DIR / "comparacao_todos_horizontes.csv")
    metrics = comparison.loc[comparison["modelo"].eq("XGBoost")].copy()
    rows = []
    for row in metrics.itertuples(index=False):
        subset = predictions.loc[predictions["horizonte_semanas"].eq(int(row.horizonte_semanas))]
        targets = subset[["target_epi_year", "target_epi_week"]].drop_duplicates().sort_values(
            ["target_epi_year", "target_epi_week"]
        )
        rows.append(
            {
                "modelo": "XGBoost",
                "versao_modelo": "criticidade_v2_avaliacao_2015_2020",
                "fonte": "validacao_2021",
                "horizonte_semanas": int(row.horizonte_semanas),
                "n_amostras_teste": int(row.n_amostras_teste),
                "semanas_avaliadas": int(len(targets)),
                "periodo_inicio": f"{int(targets.iloc[0, 0])}-{int(targets.iloc[0, 1]):02d}",
                "periodo_fim": f"{int(targets.iloc[-1, 0])}-{int(targets.iloc[-1, 1]):02d}",
                "acuracia": float(row.acuracia),
                "acuracia_balanceada": float(row.acuracia_balanceada),
                "f1_macro": float(row.f1_macro),
                "f2_macro": float(row.f2_macro),
                "atualizado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
        )
    return pd.DataFrame(rows)


def load_exports() -> dict[str, pd.DataFrame]:
    population = pd.read_csv(DATA_DIR / "populacao_censo_2022_processada.csv")
    climate = pd.read_csv(DATA_DIR / "clima_2015_2021_processado.csv")
    climate["atualizado_em"] = datetime.now().astimezone().isoformat(timespec="seconds")
    predictions = historical_predictions()
    return {
        POPULATION_TABLE: population,
        CLIMATE_TABLE: climate,
        DENGUE_WEEKLY_TABLE: dengue_weekly_export(),
        PREDICTION_TABLE: predictions,
        METRICS_TABLE: validation_metrics(predictions),
    }


def validate_exports(exports: dict[str, pd.DataFrame]) -> None:
    if len(exports[POPULATION_TABLE]) != 94:
        raise ValueError("A exportação populacional não possui 94 bairros.")
    weekly = exports[DENGUE_WEEKLY_TABLE]
    coverage = weekly.groupby(["epi_year", "epi_week"])["bairro_norm"].nunique()
    if not coverage.eq(94).all():
        raise ValueError("Existem semanas sem os 94 bairros explícitos na exportação de dengue.")
    predictions = exports[PREDICTION_TABLE]
    duplicate_keys = [
        "modo_resultado", "epi_year_origem", "epi_week_origem",
        "horizonte_semanas", "bairro_norm",
    ]
    if predictions.duplicated(duplicate_keys).any():
        raise ValueError("A exportação de previsões contém chaves duplicadas.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Valida os arquivos sem acessar o Supabase.")
    args = parser.parse_args()
    exports = load_exports()
    validate_exports(exports)
    for table, frame in exports.items():
        print(f"{table}: {len(frame):,} linhas")
    if args.dry_run:
        return

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Configure DATABASE_URL como segredo antes de executar o bootstrap.")
    engine = create_database_engine(database_url)
    execute_migration(engine, PROJECT_ROOT / "supabase" / "migrations" / "001_operational_schema.sql")
    keys = {
        POPULATION_TABLE: ["bairro_norm"],
        CLIMATE_TABLE: ["epi_year", "epi_week"],
        DENGUE_WEEKLY_TABLE: ["bairro_norm", "epi_year", "epi_week"],
        PREDICTION_TABLE: [
            "modo_resultado", "epi_year_origem", "epi_week_origem",
            "horizonte_semanas", "bairro_norm",
        ],
        METRICS_TABLE: ["fonte", "versao_modelo", "horizonte_semanas"],
    }
    for table, frame in exports.items():
        count = upsert_frame(engine, table, frame, keys[table])
        print(f"{table}: {count:,} linhas enviadas")


if __name__ == "__main__":
    main()
