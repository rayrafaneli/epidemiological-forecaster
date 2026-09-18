"""Executa o experimento completo de criticidade em quatro categorias."""

import argparse
import subprocess
import sys

from src.config import FORECAST_HORIZON_WEEKS, PROJECT_ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, choices=range(1, 5))
    parser.add_argument("--all-horizons", action="store_true")
    args = parser.parse_args()
    scripts = [
        "prepare_criticality.py", "train_xgboost_criticality.py",
        "train_ann_criticality.py", "train_lstm_criticality.py",
        "compare_criticality.py",
    ]
    horizons = range(1, 5) if args.all_horizons else [args.horizon or FORECAST_HORIZON_WEEKS]
    for horizon in horizons:
        for script in scripts:
            print(f"Executando {script} para horizonte {horizon}...", flush=True)
            subprocess.run([sys.executable, str(PROJECT_ROOT / script), "--horizon", str(horizon)], cwd=PROJECT_ROOT, check=True)
    if args.all_horizons:
        subprocess.run([sys.executable, str(PROJECT_ROOT / "compare_all_horizons.py")], cwd=PROJECT_ROOT, check=True)


if __name__ == "__main__":
    main()
