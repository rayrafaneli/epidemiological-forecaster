import unittest

import numpy as np
import pandas as pd

from src.config import DATA_DIR
from src.data_pipeline import TABULAR_NUMERIC_FEATURES


class ProcessedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.population = pd.read_csv(DATA_DIR / "populacao_censo_2022_processada.csv")
        cls.climate = pd.read_csv(DATA_DIR / "clima_2015_2021_processado.csv")
        cls.dengue = pd.read_csv(DATA_DIR / "dengue_2015_2021_processada.csv")
        cls.panel = pd.read_csv(DATA_DIR / "painel_semanal_2015_2021_h1.csv")

    def test_population_is_unique_2022(self):
        self.assertEqual(len(self.population), 94)
        self.assertEqual(self.population["ano_censo"].unique().tolist(), [2022])
        self.assertFalse(self.population["bairro_norm"].duplicated().any())

    def test_climate_is_complete_and_training_only_medians_are_recorded(self):
        self.assertEqual(len(self.climate), 365)
        self.assertFalse(self.climate[["precipitacao_total", "temp_max_media"]].isna().any().any())
        self.assertEqual(int(self.climate["precipitacao_imputada"].sum()), 11)
        self.assertEqual(int(self.climate["temperatura_imputada"].sum()), 11)
        training = self.climate.loc[self.climate["epi_year"].between(2015, 2020)]
        precipitation_median = training.groupby("epi_week")["precipitacao_original"].median()
        temperature_median = training.groupby("epi_week")["temperatura_original"].median()
        imputed = self.climate.loc[self.climate["precipitacao_imputada"]]
        np.testing.assert_allclose(
            imputed["precipitacao_total"], imputed["epi_week"].map(precipitation_median)
        )
        np.testing.assert_allclose(
            imputed["temp_max_media"], imputed["epi_week"].map(temperature_median)
        )

    def test_dengue_filters_and_deduplication(self):
        self.assertFalse(self.dengue["tp_classificacao_final"].eq(5).any())
        keys = [
            "co_unidade_notificacao",
            "nu_notificacao",
            "dt_diagnostico_sintoma",
            "ds_semana_sintoma",
            "bairro_norm",
            "tp_classificacao_final",
        ]
        self.assertFalse(self.dengue.duplicated(keys).any())

    def test_panel_has_no_model_feature_leakage_or_missing_test(self):
        modelable = self.panel.dropna(subset=TABULAR_NUMERIC_FEATURES + ["casos_alvo"])
        self.assertFalse(modelable[TABULAR_NUMERIC_FEATURES].isna().any().any())
        self.assertEqual(len(modelable.loc[modelable["target_epi_year"].eq(2021)]), 4888)
        self.assertTrue((modelable["target_time_index"] > modelable["time_index"]).all())


if __name__ == "__main__":
    unittest.main()
