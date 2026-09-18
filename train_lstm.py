"""Treina e testa uma LSTM com sequencias das quatro semanas observadas."""

import argparse

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from src.config import (
    FORECAST_HORIZON_WEEKS,
    LOOKBACK_WEEKS,
    MODELS_DIR,
    RANDOM_SEED,
    RESULTS_DIR,
    TEST_YEAR,
    VALIDATION_YEAR,
)
from src.data_pipeline import LSTM_SEQUENCE_FEATURES, LSTM_STATIC_NUMERIC_FEATURES, load_model_panel
from src.evaluation import evaluate_predictions, save_evaluation
from src.modeling import DengueLSTM, fit_fixed_epochs, set_seed, train_with_early_stopping


BATCH_SIZE = 512


def _build_sequences(panel: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sequences = []
    valid_indices = []
    ordered = panel.sort_values(["bairro_norm", "time_index"])
    row_position = {index: position for position, index in enumerate(ordered.index)}
    for _, group in ordered.groupby("bairro_norm", sort=False):
        values = group[LSTM_SEQUENCE_FEATURES].to_numpy(dtype=np.float32)
        times = group["time_index"].to_numpy(dtype=int)
        indices = group.index.to_numpy()
        for position in range(LOOKBACK_WEEKS - 1, len(group)):
            start = position - LOOKBACK_WEEKS + 1
            if np.all(np.diff(times[start : position + 1]) == 1):
                window = values[start : position + 1]
                if not np.isnan(window).any():
                    sequences.append(window)
                    valid_indices.append(indices[position])
    return np.stack(sequences), np.asarray(valid_indices), np.asarray([row_position[i] for i in valid_indices])


def _loader(sequence, static, target, shuffle):
    dataset = TensorDataset(
        torch.from_numpy(sequence.astype(np.float32)),
        torch.from_numpy(static.astype(np.float32)),
        torch.from_numpy(target.astype(np.float32)),
    )
    generator = torch.Generator().manual_seed(RANDOM_SEED)
    return DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=shuffle, generator=generator)


def _forward(model, batch):
    sequence, static, target = batch
    return model(sequence, static), target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=FORECAST_HORIZON_WEEKS, choices=range(1, 5))
    args = parser.parse_args()
    set_seed(RANDOM_SEED)
    panel = load_model_panel(args.horizon)
    sequences, indices, _ = _build_sequences(panel)
    panel = panel.loc[indices].copy().reset_index(drop=True)

    fit_mask = panel["target_epi_year"].lt(VALIDATION_YEAR)
    validation_mask = panel["target_epi_year"].eq(VALIDATION_YEAR)
    train_full_mask = panel["target_epi_year"].le(VALIDATION_YEAR)
    test_mask = panel["target_epi_year"].eq(TEST_YEAR)

    sequence_scaler = StandardScaler()
    sequence_scaler.fit(sequences[fit_mask.to_numpy()].reshape(-1, len(LSTM_SEQUENCE_FEATURES)))
    sequence_scaled = sequence_scaler.transform(
        sequences.reshape(-1, len(LSTM_SEQUENCE_FEATURES))
    ).reshape(sequences.shape)

    static_scaler = StandardScaler()
    static_fit = static_scaler.fit_transform(panel.loc[fit_mask, LSTM_STATIC_NUMERIC_FEATURES])
    static_all_numeric = static_scaler.transform(panel[LSTM_STATIC_NUMERIC_FEATURES])
    neighborhood_encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    neighborhood_encoder.fit(panel.loc[fit_mask, ["bairro_norm"]])
    neighborhood_all = neighborhood_encoder.transform(panel[["bairro_norm"]])
    static_all = np.hstack([static_all_numeric, neighborhood_all]).astype(np.float32)

    target_scaler = StandardScaler()
    target_scaler.fit(panel.loc[fit_mask, ["casos_alvo"]])
    target_all = target_scaler.transform(panel[["casos_alvo"]]).ravel().astype(np.float32)
    model = DengueLSTM(len(LSTM_SEQUENCE_FEATURES), static_all.shape[1])
    model, best_epoch, history = train_with_early_stopping(
        model,
        _loader(sequence_scaled[fit_mask], static_all[fit_mask], target_all[fit_mask], True),
        _loader(sequence_scaled[validation_mask], static_all[validation_mask], target_all[validation_mask], False),
        _forward,
    )

    set_seed(RANDOM_SEED)
    final_sequence_scaler = StandardScaler()
    final_sequence_scaler.fit(
        sequences[train_full_mask.to_numpy()].reshape(-1, len(LSTM_SEQUENCE_FEATURES))
    )
    final_sequences = final_sequence_scaler.transform(
        sequences.reshape(-1, len(LSTM_SEQUENCE_FEATURES))
    ).reshape(sequences.shape)
    final_static_scaler = StandardScaler()
    final_static_scaler.fit(panel.loc[train_full_mask, LSTM_STATIC_NUMERIC_FEATURES])
    final_encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    final_encoder.fit(panel.loc[train_full_mask, ["bairro_norm"]])
    final_static = np.hstack(
        [
            final_static_scaler.transform(panel[LSTM_STATIC_NUMERIC_FEATURES]),
            final_encoder.transform(panel[["bairro_norm"]]),
        ]
    ).astype(np.float32)
    final_target_scaler = StandardScaler()
    final_target_scaler.fit(panel.loc[train_full_mask, ["casos_alvo"]])
    final_target = final_target_scaler.transform(panel[["casos_alvo"]]).ravel().astype(np.float32)
    final_model = DengueLSTM(len(LSTM_SEQUENCE_FEATURES), final_static.shape[1])
    final_model = fit_fixed_epochs(
        final_model,
        _loader(
            final_sequences[train_full_mask],
            final_static[train_full_mask],
            final_target[train_full_mask],
            True,
        ),
        _forward,
        best_epoch,
    )
    final_model.eval()
    with torch.no_grad():
        scaled_prediction = final_model(
            torch.from_numpy(final_sequences[test_mask]), torch.from_numpy(final_static[test_mask])
        ).numpy()
    prediction = final_target_scaler.inverse_transform(scaled_prediction.reshape(-1, 1)).ravel()
    test = panel.loc[test_mask].copy()
    predictions, metrics, by_class = evaluate_predictions("LSTM", test, prediction, args.horizon)
    metrics["epocas_ou_arvores_selecionadas"] = best_epoch
    save_evaluation(predictions, metrics, by_class, RESULTS_DIR, "lstm", args.horizon)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": final_model.state_dict(),
            "sequence_features": len(LSTM_SEQUENCE_FEATURES),
            "static_features": final_static.shape[1],
        },
        MODELS_DIR / f"lstm_h{args.horizon}.pt",
    )
    joblib.dump(final_sequence_scaler, MODELS_DIR / f"escalonador_sequencia_lstm_h{args.horizon}.joblib")
    joblib.dump(final_static_scaler, MODELS_DIR / f"escalonador_estatico_lstm_h{args.horizon}.joblib")
    joblib.dump(final_encoder, MODELS_DIR / f"codificador_bairro_lstm_h{args.horizon}.joblib")
    joblib.dump(final_target_scaler, MODELS_DIR / f"escalonador_alvo_lstm_h{args.horizon}.joblib")
    pd.DataFrame(history).to_csv(
        RESULTS_DIR / f"historico_treino_lstm_h{args.horizon}.csv", index=False, encoding="utf-8-sig"
    )
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
