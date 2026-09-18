"""Treina e testa o XGBoost no protocolo temporal comum."""

import argparse

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from src.config import (
    FORECAST_HORIZON_WEEKS,
    MODELS_DIR,
    RANDOM_SEED,
    RESULTS_DIR,
    TEST_YEAR,
    VALIDATION_YEAR,
)
from src.data_pipeline import TABULAR_NUMERIC_FEATURES, load_model_panel
from src.evaluation import evaluate_predictions, save_evaluation
from src.modeling import make_tabular_preprocessor, set_seed


FEATURES = TABULAR_NUMERIC_FEATURES + ["bairro_norm"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=FORECAST_HORIZON_WEEKS, choices=range(1, 5))
    args = parser.parse_args()
    set_seed(RANDOM_SEED)
    panel = load_model_panel(args.horizon)
    train_full = panel.loc[panel["target_epi_year"].le(VALIDATION_YEAR)].copy()
    fit = train_full.loc[train_full["target_epi_year"].lt(VALIDATION_YEAR)].copy()
    validation = train_full.loc[train_full["target_epi_year"].eq(VALIDATION_YEAR)].copy()
    test = panel.loc[panel["target_epi_year"].eq(TEST_YEAR)].copy()

    selector = make_tabular_preprocessor()
    x_fit = selector.fit_transform(fit[FEATURES]).astype(np.float32)
    x_validation = selector.transform(validation[FEATURES]).astype(np.float32)
    model = xgb.XGBRegressor(
        objective="reg:squarederror",
        random_state=RANDOM_SEED,
        n_estimators=1200,
        learning_rate=0.035,
        max_depth=6,
        min_child_weight=3,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        early_stopping_rounds=50,
        n_jobs=-1,
    )
    model.fit(
        x_fit,
        fit["casos_alvo"],
        eval_set=[(x_validation, validation["casos_alvo"])],
        verbose=False,
    )
    best_trees = int(model.best_iteration) + 1

    final_selector = make_tabular_preprocessor()
    x_train_full = final_selector.fit_transform(train_full[FEATURES]).astype(np.float32)
    x_test = final_selector.transform(test[FEATURES]).astype(np.float32)
    final_model = xgb.XGBRegressor(
        objective="reg:squarederror",
        random_state=RANDOM_SEED,
        n_estimators=best_trees,
        learning_rate=0.035,
        max_depth=6,
        min_child_weight=3,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=1.0,
        n_jobs=-1,
    )
    final_model.fit(x_train_full, train_full["casos_alvo"], verbose=False)
    prediction = final_model.predict(x_test)
    predictions, metrics, by_class = evaluate_predictions("XGBoost", test, prediction, args.horizon)
    metrics["epocas_ou_arvores_selecionadas"] = best_trees
    save_evaluation(predictions, metrics, by_class, RESULTS_DIR, "xgboost", args.horizon)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    final_model.save_model(MODELS_DIR / f"xgboost_h{args.horizon}.json")
    joblib.dump(final_selector, MODELS_DIR / f"preprocessador_xgboost_h{args.horizon}.joblib")
    pd.DataFrame(
        {"feature": final_selector.get_feature_names_out(), "importancia": final_model.feature_importances_}
    ).sort_values("importancia", ascending=False).to_csv(
        RESULTS_DIR / f"importancia_features_xgboost_h{args.horizon}.csv", index=False, encoding="utf-8-sig"
    )
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
