"""Gera uma previsão operacional local para validar a interface antes do deploy."""

from __future__ import annotations

import json

import joblib
import pandas as pd
import xgboost as xgb

from scripts.bootstrap_supabase import dengue_weekly_export, historical_predictions
from src.config import CRITICALITY_MODELS_DIR, CRITICALITY_RESULTS_DIR, DATA_DIR
from src.criticality_pipeline import CRITICALITY_NUMERIC_FEATURES
from src.operational_pipeline import (
    build_operational_base,
    build_operational_features,
    evaluate_operational_predictions,
    feature_rows_for_origin,
    format_predictions,
    latest_origin,
)


FEATURES = CRITICALITY_NUMERIC_FEATURES + ["bairro_norm"]


def main() -> None:
    population = pd.read_csv(DATA_DIR / "populacao_censo_2022_processada.csv")
    climate = pd.read_csv(DATA_DIR / "clima_2015_2021_processado.csv")
    dengue = dengue_weekly_export()
    base = build_operational_base(population, climate, dengue)
    directory = CRITICALITY_MODELS_DIR / "production"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    predictions = []
    for horizon in range(1, 5):
        features = build_operational_features(base, horizon)
        origin_year, origin_week = latest_origin(features)
        selected = feature_rows_for_origin(features, origin_year, origin_week)
        selector = joblib.load(directory / manifest["horizontes"][str(horizon)]["preprocessador"])
        model = xgb.XGBClassifier()
        model.load_model(directory / manifest["horizontes"][str(horizon)]["modelo"])
        probabilities = model.predict_proba(selector.transform(selected[FEATURES]))
        predictions.append(
            format_predictions(selected, probabilities, horizon, manifest["versao_modelo"])
        )
    operational = evaluate_operational_predictions(pd.concat(predictions, ignore_index=True), base)
    historical = historical_predictions()
    combined = pd.concat([historical, operational], ignore_index=True)
    keys = [
        "modo_resultado", "epi_year_origem", "epi_week_origem",
        "horizonte_semanas", "bairro_norm",
    ]
    combined = combined.drop_duplicates(keys, keep="last").sort_values(
        ["epi_year_origem", "epi_week_origem", "horizonte_semanas", "bairro_norm"]
    )
    output = CRITICALITY_RESULTS_DIR / "previsoes_xgboost_dashboard.csv"
    combined.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"{len(operational):,} previsões operacionais adicionadas em {output}")


if __name__ == "__main__":
    main()
