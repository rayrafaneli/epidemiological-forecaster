"""Avaliacao comum da classificacao de criticidade em quatro niveis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    fbeta_score,
    log_loss,
    precision_recall_fscore_support,
    recall_score,
)
from sklearn.preprocessing import label_binarize

from src.config import RISK_LABELS


def classification_metrics(actual: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    """Metricas globais reutilizadas no teste e na validacao progressiva."""
    actual = np.asarray(actual, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    probabilities = np.clip(probabilities, 1e-9, 1.0)
    probabilities = probabilities / probabilities.sum(axis=1, keepdims=True)
    predicted = probabilities.argmax(axis=1)
    binary_actual = label_binarize(actual, classes=[0, 1, 2, 3])
    present = np.unique(actual)
    return {
        "acuracia": accuracy_score(actual, predicted),
        "acuracia_balanceada": recall_score(actual, predicted, labels=present, average="macro", zero_division=0),
        "f1_macro": f1_score(actual, predicted, labels=[0, 1, 2, 3], average="macro", zero_division=0),
        "f2_macro": fbeta_score(actual, predicted, beta=2, labels=[0, 1, 2, 3], average="macro", zero_division=0),
        "f1_ponderado": f1_score(actual, predicted, labels=[0, 1, 2, 3], average="weighted", zero_division=0),
        "pr_auc_macro": average_precision_score(binary_actual[:, present], probabilities[:, present], average="macro"),
        "log_loss": log_loss(actual, probabilities, labels=[0, 1, 2, 3]),
        "erro_absoluto_nivel_medio": np.mean(np.abs(actual - predicted)),
        "acuracia_ate_um_nivel": np.mean(np.abs(actual - predicted) <= 1),
        "kappa_quadratico": cohen_kappa_score(actual, predicted, labels=[0, 1, 2, 3], weights="quadratic"),
        "subestimacao_grave_taxa": np.mean((actual - predicted) >= 2),
    }


def evaluate_criticality(model_name: str, frame: pd.DataFrame, probabilities: np.ndarray, horizon: int):
    probabilities = np.asarray(probabilities, dtype=float)
    probabilities = np.clip(probabilities, 1e-9, 1.0)
    probabilities = probabilities / probabilities.sum(axis=1, keepdims=True)
    actual = frame["categoria_criticidade_id"].to_numpy(dtype=int)
    predicted = probabilities.argmax(axis=1)
    precision, recall, f1, support = precision_recall_fscore_support(
        actual, predicted, labels=[0, 1, 2, 3], zero_division=0
    )
    f2 = [fbeta_score(actual == index, predicted == index, beta=2, zero_division=0) for index in range(4)]
    metrics = pd.DataFrame([{
        "modelo": model_name,
        "horizonte_semanas": horizon,
        "janela_incidencia_semanas": 4,
        "n_amostras_teste": len(frame),
        **classification_metrics(actual, probabilities),
    }])
    by_class = pd.DataFrame({
        "modelo": model_name,
        "horizonte_semanas": horizon,
        "categoria": RISK_LABELS,
        "precisao": precision,
        "recall_sensibilidade": recall,
        "f1": f1,
        "f2": f2,
        "suporte": support,
    })
    output = frame[[
        "bairro_norm", "epi_year", "epi_week", "target_epi_year", "target_epi_week",
        "populacao", "casos_acumulados_4s_alvo", "incidencia_4s_alvo_100k",
        "categoria_criticidade_alvo", "incidencia_recente_4s_100k",
    ]].copy()
    output["modelo"] = model_name
    output["categoria_prevista"] = [RISK_LABELS[value] for value in predicted]
    for index, label in enumerate(RISK_LABELS):
        output[f"prob_{label.lower()}"] = probabilities[:, index]
    matrix = confusion_matrix(actual, predicted, labels=[0, 1, 2, 3])
    confusion = pd.DataFrame(matrix, index=RISK_LABELS, columns=RISK_LABELS).rename_axis("real").reset_index()
    confusion.insert(0, "modelo", model_name)
    return output, metrics, by_class, confusion


def evaluate_reference(model_name: str, frame: pd.DataFrame, predicted: np.ndarray, horizon: int):
    probabilities = np.full((len(frame), 4), 1e-6, dtype=float)
    probabilities[np.arange(len(frame)), predicted] = 1.0 - 3e-6
    return evaluate_criticality(model_name, frame, probabilities, horizon)


def save_criticality_evaluation(parts, slug: str, horizon: int, results_dir: Path) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    names = ["previsoes", "metricas", "metricas_por_categoria", "matriz_confusao"]
    for name, frame in zip(names, parts):
        frame.to_csv(results_dir / f"{name}_{slug}_h{horizon}.csv", index=False, encoding="utf-8-sig")
