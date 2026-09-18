"""Treina e testa uma Rede Neural Artificial (MLP) no protocolo comum."""

import argparse

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

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
from src.modeling import (
    ArtificialNeuralNetwork,
    fit_fixed_epochs,
    make_tabular_preprocessor,
    set_seed,
    train_with_early_stopping,
)


FEATURES = TABULAR_NUMERIC_FEATURES + ["bairro_norm"]
BATCH_SIZE = 512


def _loader(x: np.ndarray, y: np.ndarray, shuffle: bool) -> DataLoader:
    dataset = TensorDataset(torch.from_numpy(x.astype(np.float32)), torch.from_numpy(y.astype(np.float32)))
    generator = torch.Generator().manual_seed(RANDOM_SEED)
    return DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=shuffle, generator=generator)


def _forward(model, batch):
    x, target = batch
    return model(x), target


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
    x_fit = selector.fit_transform(fit[FEATURES])
    x_validation = selector.transform(validation[FEATURES])
    target_scaler = StandardScaler()
    y_fit = target_scaler.fit_transform(fit[["casos_alvo"]]).ravel()
    y_validation = target_scaler.transform(validation[["casos_alvo"]]).ravel()
    model = ArtificialNeuralNetwork(x_fit.shape[1])
    model, best_epoch, history = train_with_early_stopping(
        model,
        _loader(x_fit, y_fit, True),
        _loader(x_validation, y_validation, False),
        _forward,
    )

    set_seed(RANDOM_SEED)
    final_selector = make_tabular_preprocessor()
    x_train_full = final_selector.fit_transform(train_full[FEATURES])
    x_test = final_selector.transform(test[FEATURES])
    final_target_scaler = StandardScaler()
    y_train_full = final_target_scaler.fit_transform(train_full[["casos_alvo"]]).ravel()
    final_model = ArtificialNeuralNetwork(x_train_full.shape[1])
    final_model = fit_fixed_epochs(
        final_model, _loader(x_train_full, y_train_full, True), _forward, best_epoch
    )
    final_model.eval()
    with torch.no_grad():
        scaled_prediction = final_model(torch.from_numpy(x_test.astype(np.float32))).numpy()
    prediction = final_target_scaler.inverse_transform(scaled_prediction.reshape(-1, 1)).ravel()
    predictions, metrics, by_class = evaluate_predictions("RNA", test, prediction, args.horizon)
    metrics["epocas_ou_arvores_selecionadas"] = best_epoch
    save_evaluation(predictions, metrics, by_class, RESULTS_DIR, "rna", args.horizon)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"state_dict": final_model.state_dict(), "input_size": x_train_full.shape[1]},
        MODELS_DIR / f"rna_h{args.horizon}.pt",
    )
    joblib.dump(final_selector, MODELS_DIR / f"preprocessador_rna_h{args.horizon}.joblib")
    joblib.dump(final_target_scaler, MODELS_DIR / f"escalonador_alvo_rna_h{args.horizon}.joblib")
    pd.DataFrame(history).to_csv(
        RESULTS_DIR / f"historico_treino_rna_h{args.horizon}.csv", index=False, encoding="utf-8-sig"
    )
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
