import unittest

import numpy as np
import pandas as pd

from src.config import DATA_DIR, RISK_TO_ID
from src.criticality_pipeline import CRITICALITY_NUMERIC_FEATURES, category_from_incidence
from src.temporal_validation import progressive_masks


class CriticalityPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = pd.read_csv(DATA_DIR / "painel_semanal_2015_2021_h1.csv")
        cls.panel = pd.read_csv(DATA_DIR / "painel_criticidade_4s_h1.csv")

    def test_four_week_thresholds(self):
        labels = category_from_incidence(np.array([0, 99.99, 100, 299.99, 300, 499.99, 500]))
        self.assertEqual(labels.tolist(), ["Baixo", "Baixo", "Medio", "Medio", "Alto", "Alto", "Critico"])

    def test_target_is_future_four_week_sum(self):
        sample = self.panel.iloc[len(self.panel) // 2]
        neighborhood = self.base.loc[self.base["bairro_norm"].eq(sample["bairro_norm"])].sort_values("time_index")
        target_position = neighborhood.index[neighborhood["time_index"].eq(sample["target_time_index"])][0]
        location = neighborhood.index.get_loc(target_position)
        expected = neighborhood.iloc[location - 3 : location + 1]["casos_totais"].sum()
        self.assertEqual(float(sample["casos_acumulados_4s_alvo"]), float(expected))
        self.assertEqual(int(sample["target_time_index"]), int(sample["time_index"] + 1))

    def test_features_and_test_set_are_complete(self):
        self.assertFalse(self.panel[CRITICALITY_NUMERIC_FEATURES].isna().any().any())
        self.assertEqual(len(self.panel.loc[self.panel["target_epi_year"].eq(2021)]), 4888)
        mapped = self.panel["categoria_criticidade_alvo"].map(RISK_TO_ID)
        self.assertTrue((mapped == self.panel["categoria_criticidade_id"]).all())

    def test_progressive_validation_never_uses_future_years(self):
        training = self.panel.loc[self.panel["target_epi_year"].le(2020)].reset_index(drop=True)
        folds = list(progressive_masks(training))
        self.assertEqual([year for year, _, _ in folds], [2016, 2017, 2018, 2019, 2020])
        years = training["target_epi_year"].astype(int).to_numpy()
        for validation_year, train_mask, validation_mask in folds:
            self.assertTrue((years[train_mask] < validation_year).all())
            self.assertTrue((years[validation_mask] == validation_year).all())
            self.assertFalse((years[train_mask] >= validation_year).any())


if __name__ == "__main__":
    unittest.main()
