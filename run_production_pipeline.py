"""Rotina diária: detecta dados completos, prevê e avalia resultados anteriores."""

from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import pandas as pd
import xgboost as xgb
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")

from src.config import CRITICALITY_MODELS_DIR
from src.criticality_pipeline import CRITICALITY_NUMERIC_FEATURES
from src.operational_pipeline import (
    build_operational_base,
    build_operational_features,
    evaluate_operational_predictions,
    feature_rows_for_origin,
    format_predictions,
    latest_origin,
    production_metrics,
)
from src.operational_store import (
    CLIMATE_TABLE,
    DENGUE_WEEKLY_TABLE,
    METRICS_TABLE,
    POPULATION_TABLE,
    PREDICTION_TABLE,
    create_database_engine,
    read_production_predictions,
    read_table,
    record_pipeline_run,
    upsert_frame,
)


FEATURES = CRITICALITY_NUMERIC_FEATURES + ["bairro_norm"]
PREDICTION_KEYS = [
    "modo_resultado", "epi_year_origem", "epi_week_origem",
    "horizonte_semanas", "bairro_norm",
]


def production_artifacts():
    directory = CRITICALITY_MODELS_DIR / "production"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    return directory, manifest


def origins_to_predict(base: pd.DataFrame, existing: pd.DataFrame) -> list[tuple[int, int]]:
    weeks = base[["epi_year", "epi_week", "time_index"]].drop_duplicates().sort_values("time_index")
    if existing.empty:
        latest = weeks.iloc[-1]
        return [(int(latest["epi_year"]), int(latest["epi_week"]))]
    existing_keys = existing[["epi_year_origem", "epi_week_origem"]].drop_duplicates()
    existing_keys = existing_keys.rename(
        columns={"epi_year_origem": "epi_year", "epi_week_origem": "epi_week"}
    )
    merged = weeks.merge(existing_keys.assign(_exists=True), on=["epi_year", "epi_week"], how="left")
    last_existing_index = merged.loc[merged["_exists"].eq(True), "time_index"].max()
    if pd.isna(last_existing_index):
        latest = weeks.iloc[-1]
        return [(int(latest["epi_year"]), int(latest["epi_week"]))]
    pending = weeks.loc[weeks["time_index"].gt(int(last_existing_index))]
    return [(int(row.epi_year), int(row.epi_week)) for row in pending.itertuples()]


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL não foi configurada.")
    engine = create_database_engine(database_url)
    origin_label = None
    try:
        population = read_table(engine, POPULATION_TABLE)
        climate = read_table(engine, CLIMATE_TABLE)
        dengue = read_table(engine, DENGUE_WEEKLY_TABLE)
        base = build_operational_base(population, climate, dengue)
        existing = read_production_predictions(engine)
        origins = origins_to_predict(base, existing)
        directory, manifest = production_artifacts()
        generated_parts: list[pd.DataFrame] = []

        for horizon in range(1, 5):
            features = build_operational_features(base, horizon)
            model = xgb.XGBClassifier()
            model.load_model(directory / manifest["horizontes"][str(horizon)]["modelo"])
            selector = joblib.load(directory / manifest["horizontes"][str(horizon)]["preprocessador"])
            for origin_year, origin_week in origins:
                selected = feature_rows_for_origin(features, origin_year, origin_week)
                transformed = selector.transform(selected[FEATURES])
                probabilities = model.predict_proba(transformed)
                generated_parts.append(
                    format_predictions(
                        selected,
                        probabilities,
                        horizon,
                        manifest["versao_modelo"],
                    )
                )

        generated = pd.concat(generated_parts, ignore_index=True) if generated_parts else pd.DataFrame()
        if not generated.empty:
            upsert_frame(engine, PREDICTION_TABLE, generated, PREDICTION_KEYS)
            existing = pd.concat([existing, generated], ignore_index=True)
            existing = existing.drop_duplicates(PREDICTION_KEYS, keep="last")

        evaluated = evaluate_operational_predictions(existing, base)
        if not evaluated.empty:
            upsert_frame(engine, PREDICTION_TABLE, evaluated, PREDICTION_KEYS)
        metrics = production_metrics(evaluated)
        if not metrics.empty:
            upsert_frame(
                engine,
                METRICS_TABLE,
                metrics,
                ["fonte", "versao_modelo", "horizonte_semanas"],
            )

        latest_year, latest_week = latest_origin(build_operational_features(base, 1))
        origin_label = f"{latest_year}-{latest_week:02d}"
        detail = (
            f"{len(origins)} nova(s) semana(s), {len(generated):,} previsões geradas, "
            f"{int(evaluated['status_avaliacao'].eq('Consolidado').sum()) if not evaluated.empty else 0:,} "
            "previsões consolidadas."
        )
        record_pipeline_run(engine, "sucesso", detail, origin_label)
        print(detail)
    except Exception as exc:
        try:
            record_pipeline_run(engine, "erro", str(exc), origin_label)
        finally:
            raise


if __name__ == "__main__":
    main()
