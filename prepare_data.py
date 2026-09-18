"""Gera as bases processadas e todas as auditorias."""

import argparse

from src.config import FORECAST_HORIZON_WEEKS
from src.data_pipeline import prepare_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=FORECAST_HORIZON_WEEKS, choices=range(1, 5))
    args = parser.parse_args()
    outputs = prepare_all(horizon=args.horizon)
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
