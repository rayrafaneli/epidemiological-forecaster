"""Consolida desempenho de todos os modelos nos horizontes de uma a quatro semanas."""

import json
import pandas as pd

from src.config import CRITICALITY_RESULTS_DIR


MODELS = [("xgboost", "XGBoost"), ("rna", "RNA"), ("lstm", "LSTM")]


def main() -> None:
    comparisons, categories, validations, hyperparameters = [], [], [], []
    for horizon in range(1, 5):
        comparisons.append(pd.read_csv(CRITICALITY_RESULTS_DIR / f"comparacao_modelos_criticidade_h{horizon}.csv"))
        categories.append(pd.read_csv(CRITICALITY_RESULTS_DIR / f"comparacao_por_categoria_h{horizon}.csv"))
        for slug, display_name in MODELS:
            validation = pd.read_csv(CRITICALITY_RESULTS_DIR / f"validacao_progressiva_{slug}_h{horizon}.csv")
            validation.insert(0, "modelo", display_name)
            validation.insert(1, "horizonte_semanas", horizon)
            validations.append(validation)
        params = json.loads((CRITICALITY_RESULTS_DIR / f"melhores_hiperparametros_xgboost_h{horizon}.json").read_text(encoding="utf-8"))
        hyperparameters.append({"horizonte_semanas": horizon, **params})

    comparison = pd.concat(comparisons, ignore_index=True)
    category = pd.concat(categories, ignore_index=True)
    validation = pd.concat(validations, ignore_index=True)
    model_only = comparison.loc[comparison["tipo"].eq("modelo")].copy()
    mean_summary = (
        model_only.groupby("modelo", as_index=False)[
            ["acuracia", "acuracia_balanceada", "f1_macro", "f2_macro", "pr_auc_macro",
             "erro_absoluto_nivel_medio", "kappa_quadratico", "subestimacao_grave_taxa"]
        ].mean()
        .sort_values(["f2_macro", "acuracia_balanceada"], ascending=False)
    )
    comparison.to_csv(CRITICALITY_RESULTS_DIR / "comparacao_todos_horizontes.csv", index=False, encoding="utf-8-sig")
    category.to_csv(CRITICALITY_RESULTS_DIR / "comparacao_categorias_todos_horizontes.csv", index=False, encoding="utf-8-sig")
    validation.to_csv(CRITICALITY_RESULTS_DIR / "validacao_progressiva_todos_modelos.csv", index=False, encoding="utf-8-sig")
    mean_summary.to_csv(CRITICALITY_RESULTS_DIR / "resumo_medio_horizontes.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(hyperparameters).to_csv(CRITICALITY_RESULTS_DIR / "hiperparametros_xgboost_horizontes.csv", index=False, encoding="utf-8-sig")
    print(model_only[["modelo", "horizonte_semanas", "acuracia_balanceada", "f1_macro", "f2_macro", "pr_auc_macro"]].to_string(index=False))
    print("\nMedia dos quatro horizontes:\n", mean_summary.to_string(index=False))


if __name__ == "__main__":
    main()
