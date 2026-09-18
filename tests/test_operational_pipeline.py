import unittest

import numpy as np
import pandas as pd

from src.operational_pipeline import (
    advance_epidemiological_week,
    build_operational_base,
    build_operational_features,
    evaluate_operational_predictions,
    feature_rows_for_origin,
    production_metrics,
)


def sources(weeks: int = 12, dengue_weeks: int | None = None):
    dengue_weeks = dengue_weeks if dengue_weeks is not None else weeks
    population = pd.DataFrame(
        {
            "ano_censo": 2022,
            "bairro_norm": [f"BAIRRO {index:02d}" for index in range(94)],
            "populacao": 10_000,
        }
    )
    climate = pd.DataFrame(
        {
            "epi_year": 2021,
            "epi_week": range(1, weeks + 1),
            "precipitacao_total": np.arange(weeks, dtype=float) + 10,
            "temp_max_media": np.arange(weeks, dtype=float) / 10 + 30,
        }
    )
    rows = []
    for week in range(1, dengue_weeks + 1):
        for neighborhood in population["bairro_norm"]:
            rows.append(
                {
                    "bairro_norm": neighborhood,
                    "epi_year": 2021,
                    "epi_week": week,
                    "casos_totais": 1 if neighborhood == "BAIRRO 00" else 0,
                }
            )
    return population, climate, pd.DataFrame(rows)


class OperationalPipelineTests(unittest.TestCase):
    def test_epidemiological_week_advances_across_year(self):
        self.assertEqual(advance_epidemiological_week(2020, 53, 1), (2021, 1))
        self.assertEqual(advance_epidemiological_week(2021, 52, 1), (2022, 1))

    def test_pipeline_waits_for_both_sources(self):
        population, climate, dengue = sources(weeks=12, dengue_weeks=11)
        base = build_operational_base(population, climate, dengue)
        self.assertEqual(base["epi_week"].max(), 11)
        self.assertEqual(len(base), 94 * 11)

    def test_incomplete_middle_week_is_rejected(self):
        population, climate, dengue = sources(weeks=12)
        dengue = dengue.loc[~dengue["epi_week"].eq(6)]
        with self.assertRaisesRegex(ValueError, "semanas incompletas"):
            build_operational_base(population, climate, dengue)

    def test_missing_middle_climate_week_is_rejected(self):
        population, climate, dengue = sources(weeks=12)
        climate = climate.loc[~climate["epi_week"].eq(6)]
        with self.assertRaisesRegex(ValueError, "semanas climáticas ausentes"):
            build_operational_base(population, climate, dengue)

    def test_latest_origin_has_all_neighborhoods_and_future_target(self):
        population, climate, dengue = sources(weeks=12)
        base = build_operational_base(population, climate, dengue)
        features = build_operational_features(base, horizon=4)
        rows = feature_rows_for_origin(features, 2021, 12)
        self.assertEqual(len(rows), 94)
        self.assertTrue(rows["target_epi_week"].eq(16).all())

    def test_evaluation_moves_from_provisional_to_consolidated(self):
        population, climate, dengue = sources(weeks=12)
        base = build_operational_base(population, climate, dengue)
        predictions = pd.DataFrame(
            {
                "modelo": ["XGBoost", "XGBoost"],
                "versao_modelo": ["test", "test"],
                "modo_resultado": ["producao", "producao"],
                "bairro_norm": ["BAIRRO 00", "BAIRRO 00"],
                "target_epi_year": [2021, 2021],
                "target_epi_week": [12, 7],
                "horizonte_semanas": [1, 1],
                "categoria_prevista": ["Baixo", "Baixo"],
            }
        )
        evaluated = evaluate_operational_predictions(predictions, base, lag_weeks=4)
        self.assertEqual(evaluated.iloc[0]["status_avaliacao"], "Provisório")
        self.assertEqual(evaluated.iloc[1]["status_avaliacao"], "Consolidado")

    def test_production_metrics_require_four_target_weeks(self):
        rows = []
        for week in range(1, 5):
            for neighborhood in range(2):
                rows.append(
                    {
                        "status_avaliacao": "Consolidado",
                        "horizonte_semanas": 1,
                        "target_epi_year": 2022,
                        "target_epi_week": week,
                        "categoria_observada_alvo": "Baixo",
                        "categoria_prevista": "Baixo",
                        "versao_modelo": "production-test",
                    }
                )
        metrics = production_metrics(pd.DataFrame(rows), minimum_target_weeks=4)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics.iloc[0]["semanas_avaliadas"], 4)
        self.assertEqual(metrics.iloc[0]["acuracia"], 1.0)


if __name__ == "__main__":
    unittest.main()
