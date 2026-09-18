"""Consolida metricas e matrizes de confusao dos tres modelos."""

import argparse

import pandas as pd

from src.config import FORECAST_HORIZON_WEEKS, RESULTS_DIR, RISK_LABELS


MODELS = [("xgboost", "XGBoost"), ("rna", "RNA"), ("lstm", "LSTM")]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=FORECAST_HORIZON_WEEKS, choices=range(1, 5))
    args = parser.parse_args()
    metrics = []
    category_metrics = []
    confusion = []
    for slug, display_name in MODELS:
        metrics.append(pd.read_csv(RESULTS_DIR / f"metricas_{slug}_h{args.horizon}.csv"))
        category_metrics.append(
            pd.read_csv(RESULTS_DIR / f"metricas_por_categoria_{slug}_h{args.horizon}.csv")
        )
        predictions = pd.read_csv(RESULTS_DIR / f"previsoes_{slug}_h{args.horizon}.csv")
        matrix = pd.crosstab(predictions["categoria_real"], predictions["categoria_prevista"])
        matrix = matrix.reindex(index=RISK_LABELS, columns=RISK_LABELS, fill_value=0)
        matrix.index.name = "categoria_real"
        matrix = matrix.reset_index()
        matrix.insert(0, "modelo", display_name)
        matrix.insert(1, "horizonte_semanas", args.horizon)
        matrix = matrix.rename(columns={label: f"previsto_{label.lower()}" for label in RISK_LABELS})
        confusion.append(matrix)

    comparison = pd.concat(metrics, ignore_index=True).sort_values("rmse_casos")
    comparison.to_csv(
        RESULTS_DIR / f"comparacao_modelos_h{args.horizon}.csv", index=False, encoding="utf-8-sig"
    )
    pd.concat(category_metrics, ignore_index=True).to_csv(
        RESULTS_DIR / f"comparacao_categorias_h{args.horizon}.csv", index=False, encoding="utf-8-sig"
    )
    pd.concat(confusion, ignore_index=True).to_csv(
        RESULTS_DIR / f"matrizes_confusao_h{args.horizon}.csv", index=False, encoding="utf-8-sig"
    )
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
