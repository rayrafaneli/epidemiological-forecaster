"""Executa preparacao, os tres treinamentos e consolida a comparacao."""

import argparse
import subprocess
import sys
from pathlib import Path

from src.config import FORECAST_HORIZON_WEEKS, PROJECT_ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=FORECAST_HORIZON_WEEKS, choices=range(1, 5))
    args = parser.parse_args()
    scripts = [
        "prepare_data.py",
        "train_xgboost.py",
        "train_ann.py",
        "train_lstm.py",
        "compare_results.py",
    ]
    for script in scripts:
        print(f"\nExecutando {script} para horizonte {args.horizon}...")
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / script), "--horizon", str(args.horizon)],
            cwd=PROJECT_ROOT,
            check=True,
        )


if __name__ == "__main__":
    main()
