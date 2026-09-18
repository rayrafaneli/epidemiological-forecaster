"""Metricas identicas para XGBoost, RNA e LSTM."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_fscore_support,
    r2_score,
)

from src.config import RISK_LABELS


def risk_category(incidence: np.ndarray | pd.Series) -> np.ndarray:
    values = np.asarray(incidence, dtype=float)
    return np.select(
        [values < 100, values < 300, values < 500],
        RISK_LABELS[:3],
        default=RISK_LABELS[3],
    )


def evaluate_predictions(
    model_name: str,
    frame: pd.DataFrame,
    prediction: np.ndarray,
    horizon: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    output = frame[
        [
            "bairro_norm",
            "epi_year",
            "epi_week",
            "target_epi_year",
            "target_epi_week",
            "populacao",
            "casos_alvo",
            "taxa_incidencia_alvo_100k",
        ]
    ].copy()
    output["modelo"] = model_name
    output["horizonte_semanas"] = horizon
    output["casos_previstos_continuo"] = np.clip(np.asarray(prediction, dtype=float), 0, None)
    output["casos_previstos"] = np.rint(output["casos_previstos_continuo"]).astype(int)
    output["taxa_incidencia_prevista_100k"] = (
        output["casos_previstos"] / output["populacao"] * 100_000
    )
    output["categoria_real"] = risk_category(output["taxa_incidencia_alvo_100k"])
    output["categoria_prevista"] = risk_category(output["taxa_incidencia_prevista_100k"])

    y_true = output["casos_alvo"].to_numpy(dtype=float)
    y_pred = output["casos_previstos_continuo"].to_numpy(dtype=float)
    class_true = output["categoria_real"]
    class_pred = output["categoria_prevista"]
    metrics = pd.DataFrame(
        [
            {
                "modelo": model_name,
                "horizonte_semanas": horizon,
                "n_amostras_teste": len(output),
                "mae_casos": mean_absolute_error(y_true, y_pred),
                "rmse_casos": math_sqrt_mse(y_true, y_pred),
                "r2_casos": r2_score(y_true, y_pred),
                "acuracia_categoria": accuracy_score(class_true, class_pred),
                "acuracia_balanceada_categoria": balanced_accuracy_score(class_true, class_pred),
                "f1_macro_categoria": f1_score(
                    class_true, class_pred, labels=RISK_LABELS, average="macro", zero_division=0
                ),
            }
        ]
    )
    precision, recall, f1, support = precision_recall_fscore_support(
        class_true, class_pred, labels=RISK_LABELS, zero_division=0
    )
    by_class = pd.DataFrame(
        {
            "modelo": model_name,
            "horizonte_semanas": horizon,
            "categoria": RISK_LABELS,
            "precisao": precision,
            "recall": recall,
            "f1": f1,
            "suporte": support,
        }
    )
    return output, metrics, by_class


def math_sqrt_mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def save_evaluation(
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    by_class: pd.DataFrame,
    results_dir: Path,
    slug: str,
    horizon: int,
) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(results_dir / f"previsoes_{slug}_h{horizon}.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(results_dir / f"metricas_{slug}_h{horizon}.csv", index=False, encoding="utf-8-sig")
    by_class.to_csv(results_dir / f"metricas_por_categoria_{slug}_h{horizon}.csv", index=False, encoding="utf-8-sig")
