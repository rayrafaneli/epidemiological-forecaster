"""Utilitarios compartilhados de modelagem e redes PyTorch."""

from __future__ import annotations

import random

import numpy as np
import torch
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from torch import nn

from src.data_pipeline import TABULAR_NUMERIC_FEATURES


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def make_tabular_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), TABULAR_NUMERIC_FEATURES),
            ("bairro", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["bairro_norm"]),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


class ArtificialNeuralNetwork(nn.Module):
    def __init__(self, input_size: int) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.10),
            nn.Linear(64, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x).squeeze(-1)


class DengueLSTM(nn.Module):
    def __init__(self, sequence_features: int, static_features: int) -> None:
        super().__init__()
        self.lstm = nn.LSTM(sequence_features, hidden_size=48, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(48 + static_features, 64),
            nn.ReLU(),
            nn.Dropout(0.10),
            nn.Linear(64, 1),
        )

    def forward(self, sequence: torch.Tensor, static: torch.Tensor) -> torch.Tensor:
        _, (hidden, _) = self.lstm(sequence)
        combined = torch.cat([hidden[-1], static], dim=1)
        return self.head(combined).squeeze(-1)


def train_with_early_stopping(
    model: nn.Module,
    train_batches,
    validation_batches,
    forward_fn,
    max_epochs: int = 80,
    patience: int = 10,
) -> tuple[nn.Module, int, list[dict[str, float]]]:
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    loss_fn = nn.MSELoss()
    best_loss = float("inf")
    best_epoch = 1
    best_state = None
    history: list[dict[str, float]] = []

    for epoch in range(1, max_epochs + 1):
        model.train()
        train_losses = []
        for batch in train_batches:
            optimizer.zero_grad()
            prediction, target = forward_fn(model, batch)
            loss = loss_fn(prediction, target)
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.detach()))

        model.eval()
        validation_losses = []
        with torch.no_grad():
            for batch in validation_batches:
                prediction, target = forward_fn(model, batch)
                validation_losses.append(float(loss_fn(prediction, target)))
        validation_loss = float(np.mean(validation_losses))
        history.append(
            {
                "epoca": epoch,
                "loss_treino": float(np.mean(train_losses)),
                "loss_validacao": validation_loss,
            }
        )
        if validation_loss < best_loss - 1e-6:
            best_loss = validation_loss
            best_epoch = epoch
            best_state = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
        elif epoch - best_epoch >= patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_epoch, history


def fit_fixed_epochs(model: nn.Module, batches, forward_fn, epochs: int) -> nn.Module:
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    loss_fn = nn.MSELoss()
    for _ in range(epochs):
        model.train()
        for batch in batches:
            optimizer.zero_grad()
            prediction, target = forward_fn(model, batch)
            loss = loss_fn(prediction, target)
            loss.backward()
            optimizer.step()
    return model
