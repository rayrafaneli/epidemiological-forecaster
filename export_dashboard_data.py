"""Gera o arquivo consolidado consumido pela API e pelo dashboard."""

from src.dashboard_data import build_dashboard_export


def main() -> None:
    path = build_dashboard_export()
    print(f"Exportação do dashboard gerada em: {path}")


if __name__ == "__main__":
    main()
