"""Utilitarios para validacao por origem temporal expansiva."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import PROGRESSIVE_VALIDATION_YEARS
from src.criticality_evaluation import classification_metrics


def progressive_masks(panel: pd.DataFrame):
    years = panel["target_epi_year"].astype(int)
    for validation_year in PROGRESSIVE_VALIDATION_YEARS:
        train_mask = years.lt(validation_year).to_numpy()
        validation_mask = years.eq(validation_year).to_numpy()
        if train_mask.any() and validation_mask.any():
            yield validation_year, train_mask, validation_mask


def fold_metric_row(validation_year: int, actual: np.ndarray, probabilities: np.ndarray) -> dict:
    metrics = classification_metrics(actual, probabilities)
    counts = np.bincount(np.asarray(actual, dtype=int), minlength=4)
    return {
        "ano_validacao": validation_year,
        "n_treino_anos": validation_year - 2015,
        "n_validacao": len(actual),
        "suporte_baixo": int(counts[0]),
        "suporte_medio": int(counts[1]),
        "suporte_alto": int(counts[2]),
        "suporte_critico": int(counts[3]),
        **metrics,
    }


def pooled_validation_metrics(actual_parts, probability_parts) -> dict[str, float]:
    return classification_metrics(np.concatenate(actual_parts), np.vstack(probability_parts))


def robust_epoch_choice(best_epochs: list[int]) -> int:
    """Mediana reduz a influencia de um unico ano atipico."""
    return max(1, int(np.rint(np.median(best_epochs))))
