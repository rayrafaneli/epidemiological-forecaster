"""Validacao final dos modelos, previsoes e workbooks entregues."""

import json
import zipfile
from pathlib import Path

import joblib
import pandas as pd
import torch
import xgboost as xgb

from src.config import DATA_DIR, MODELS_DIR, PROJECT_ROOT, RESULTS_DIR


def main() -> None:
    checks = {}
    comparison = pd.read_csv(RESULTS_DIR / "comparacao_modelos_h1.csv")
    checks["tres_modelos_na_comparacao"] = sorted(comparison["modelo"].tolist()) == ["LSTM", "RNA", "XGBoost"]

    for slug in ["xgboost", "rna", "lstm"]:
        predictions = pd.read_csv(RESULTS_DIR / f"previsoes_{slug}_h1.csv")
        checks[f"previsoes_{slug}_4888"] = len(predictions) == 4888
        checks[f"previsoes_{slug}_sem_nan"] = not predictions["casos_previstos_continuo"].isna().any()

    xgb_model = xgb.XGBRegressor()
    xgb_model.load_model(MODELS_DIR / "xgboost_h1.json")
    checks["xgboost_reabre"] = xgb_model.get_booster().num_boosted_rounds() > 0
    checks["preprocessador_xgboost_reabre"] = joblib.load(
        MODELS_DIR / "preprocessador_xgboost_h1.joblib"
    ) is not None

    ann_checkpoint = torch.load(MODELS_DIR / "rna_h1.pt", map_location="cpu", weights_only=True)
    lstm_checkpoint = torch.load(MODELS_DIR / "lstm_h1.pt", map_location="cpu", weights_only=True)
    checks["rna_reabre"] = "state_dict" in ann_checkpoint and ann_checkpoint["input_size"] > 0
    checks["lstm_reabre"] = "state_dict" in lstm_checkpoint and lstm_checkpoint["sequence_features"] == 5

    workbooks = [
        "populacao_censo_2022_processada.xlsx",
        "dengue_2015_2021_processada.xlsx",
        "clima_2015_2021_processado.xlsx",
        "painel_semanal_2015_2021_h1.xlsx",
    ]
    for name in workbooks:
        path = DATA_DIR / name
        with zipfile.ZipFile(path) as archive:
            checks[f"xlsx_valido_{name}"] = archive.testzip() is None and "xl/workbook.xml" in archive.namelist()

    if not all(checks.values()):
        failures = [name for name, passed in checks.items() if not passed]
        raise AssertionError(f"Falhas de validacao: {failures}")
    output = PROJECT_ROOT / "docs" / "validacao_final.json"
    output.write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(checks)} verificacoes aprovadas. Relatorio: {output}")


if __name__ == "__main__":
    main()
