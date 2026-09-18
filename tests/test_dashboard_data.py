import unittest

import numpy as np

from src.dashboard_data import (
    DashboardRepository,
    RISK_LABELS_DISPLAY,
    build_dashboard_export,
    common_origins,
)


class DashboardDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_dashboard_export()
        cls.predictions = DashboardRepository(database_url=None).predictions()

    def test_enriched_contract_is_complete(self):
        required = {
            "semana_origem",
            "semana_alvo",
            "horizonte_semanas",
            "categoria_prevista",
            "confianca_modelo",
            "categoria_recente_observada",
            "previsao_correta",
        }
        self.assertTrue(required.issubset(self.predictions.columns))
        self.assertEqual(set(self.predictions["horizonte_semanas"].unique()), {1, 2, 3, 4})

    def test_probabilities_and_confidence_are_consistent(self):
        probabilities = self.predictions[["prob_baixo", "prob_medio", "prob_alto", "prob_critico"]].to_numpy()
        self.assertTrue(np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-6))
        self.assertTrue(np.allclose(probabilities.max(axis=1), self.predictions["confianca_modelo"]))
        labels = np.asarray(RISK_LABELS_DISPLAY)[probabilities.argmax(axis=1)]
        self.assertTrue((labels == self.predictions["categoria_prevista"].to_numpy()).all())

    def test_common_origins_have_all_four_horizons(self):
        validation = self.predictions.loc[
            self.predictions["modo_resultado"].eq("validacao_historica_2021")
        ]
        origins = common_origins(validation)
        self.assertEqual(origins[0], (2020, 53))
        self.assertEqual(origins[-1], (2021, 48))
        self.assertEqual(len(origins), 49)

    def test_one_row_per_origin_horizon_and_neighborhood(self):
        duplicated = self.predictions.duplicated(
            ["modo_resultado", "epi_year_origem", "epi_week_origem", "horizonte_semanas", "bairro_norm"]
        )
        self.assertFalse(duplicated.any())


if __name__ == "__main__":
    unittest.main()
