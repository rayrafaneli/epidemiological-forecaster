"""Gera o painel aprimorado para classificacao em quatro niveis."""

import argparse

from src.config import FORECAST_HORIZON_WEEKS
from src.criticality_pipeline import prepare_criticality_panel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=FORECAST_HORIZON_WEEKS, choices=range(1, 5))
    args = parser.parse_args()
    for name, path in prepare_criticality_panel(args.horizon).items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
