"""Componentes do pipeline operacional de previsao e avaliacao.

O treinamento do modelo permanece separado deste modulo. Aqui ficam apenas as
transformacoes necessarias para detectar semanas completas, construir atributos
sem vazamento temporal, formatar previsoes e avalia-las quando os dados reais
se tornam disponiveis.
"""

from __future__ import annotations

from datetime import datetime
import math
import os

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, fbeta_score, recall_score

from src.config import ID_TO_RISK, RISK_LABELS, RISK_TO_ID
from src.criticality_pipeline import (
    CRITICALITY_NUMERIC_FEATURES,
    build_criticality_panel,
    category_from_incidence,
)


PRODUCTION_MODE = "producao"
VALIDATION_MODE = "validacao_historica_2021"
EVALUATION_LAG_WEEKS = int(os.getenv("EVALUATION_LAG_WEEKS", "4"))
MIN_PRODUCTION_EVALUATION_WEEKS = int(os.getenv("MIN_PRODUCTION_EVALUATION_WEEKS", "4"))

RISK_DISPLAY = {
    "Baixo": "Baixo",
    "Medio": "Médio",
    "Médio": "Médio",
    "Alto": "Alto",
    "Critico": "Crítico",
    "Crítico": "Crítico",
}
RISK_ID_DISPLAY = {identifier: RISK_DISPLAY[label] for identifier, label in ID_TO_RISK.items()}
RISK_DISPLAY_TO_ID = {
    "Baixo": RISK_TO_ID["Baixo"],
    "Medio": RISK_TO_ID["Medio"],
    "Médio": RISK_TO_ID["Medio"],
    "Alto": RISK_TO_ID["Alto"],
    "Critico": RISK_TO_ID["Critico"],
    "Crítico": RISK_TO_ID["Critico"],
}


def display_category(value: object) -> str:
    return RISK_DISPLAY.get(str(value), str(value))


def epidemiological_week_start(year: int, week: int) -> pd.Timestamp:
    """Retorna o domingo inicial da semana epidemiologica informada."""
    if week < 1 or week > 53:
        raise ValueError(f"Semana epidemiologica invalida: {year}-{week:02d}")
    january_fourth = pd.Timestamp(int(year), 1, 4)
    week_one_start = january_fourth - pd.Timedelta(days=(january_fourth.dayofweek + 1) % 7)
    result = week_one_start + pd.Timedelta(weeks=int(week) - 1)
    next_january_fourth = pd.Timestamp(int(year) + 1, 1, 4)
    next_week_one = next_january_fourth - pd.Timedelta(days=(next_january_fourth.dayofweek + 1) % 7)
    if result >= next_week_one:
        raise ValueError(f"A semana {year}-{week:02d} nao existe no calendario epidemiologico.")
    return result


def epidemiological_year_week(date: pd.Timestamp) -> tuple[int, int]:
    """Converte uma data para a semana epidemiologica domingo-sabado."""
    normalized = pd.Timestamp(date).normalize()
    candidate_year = normalized.year
    start = epidemiological_week_start(candidate_year, 1)
    if normalized < start:
        candidate_year -= 1
        start = epidemiological_week_start(candidate_year, 1)
    next_start = epidemiological_week_start(candidate_year + 1, 1)
    if normalized >= next_start:
        return candidate_year + 1, 1
    return candidate_year, int((normalized - start).days // 7 + 1)


def advance_epidemiological_week(year: int, week: int, steps: int) -> tuple[int, int]:
    target_date = epidemiological_week_start(int(year), int(week)) + pd.Timedelta(weeks=int(steps))
    return epidemiological_year_week(target_date)


def _validate_population(population: pd.DataFrame) -> pd.DataFrame:
    required = {"bairro_norm", "populacao"}
    missing = required.difference(population.columns)
    if missing:
        raise ValueError(f"Colunas populacionais ausentes: {sorted(missing)}")
    output = population[[column for column in ["ano_censo", "bairro_norm", "populacao"] if column in population]].copy()
    output["bairro_norm"] = output["bairro_norm"].astype(str).str.strip().str.upper()
    output["populacao"] = pd.to_numeric(output["populacao"], errors="raise")
    output = output.drop_duplicates("bairro_norm")
    if len(output) != 94:
        raise ValueError(f"Esperados 94 bairros; encontrados {len(output)}.")
    return output.sort_values("bairro_norm").reset_index(drop=True)


def _complete_climate_weeks(
    climate: pd.DataFrame,
    dengue_weekly: pd.DataFrame,
    neighborhoods: int,
) -> pd.DataFrame:
    climate_required = {"epi_year", "epi_week", "precipitacao_total", "temp_max_media"}
    dengue_required = {"bairro_norm", "epi_year", "epi_week", "casos_totais"}
    if missing := climate_required.difference(climate.columns):
        raise ValueError(f"Colunas climaticas ausentes: {sorted(missing)}")
    if missing := dengue_required.difference(dengue_weekly.columns):
        raise ValueError(f"Colunas semanais de dengue ausentes: {sorted(missing)}")

    ordered = climate.copy()
    ordered["epi_year"] = pd.to_numeric(ordered["epi_year"], errors="raise").astype(int)
    ordered["epi_week"] = pd.to_numeric(ordered["epi_week"], errors="raise").astype(int)
    ordered = ordered.sort_values(["epi_year", "epi_week"]).drop_duplicates(["epi_year", "epi_week"], keep="last")
    ordered["_week_start"] = [
        epidemiological_week_start(year, week)
        for year, week in zip(ordered["epi_year"], ordered["epi_week"])
    ]
    missing_calendar_weeks = ordered["_week_start"].diff().dt.days.dropna().ne(7)
    if missing_calendar_weeks.any():
        first_gap_position = int(np.flatnonzero(missing_calendar_weeks.to_numpy())[0]) + 1
        row = ordered.iloc[first_gap_position]
        raise ValueError(
            "Existem semanas climáticas ausentes antes de "
            f"{int(row['epi_year'])}-{int(row['epi_week']):02d}."
        )
    ordered["clima_completo"] = ordered[["precipitacao_total", "temp_max_media"]].notna().all(axis=1)

    coverage = (
        dengue_weekly.groupby(["epi_year", "epi_week"])["bairro_norm"]
        .nunique()
        .rename("bairros_dengue")
        .reset_index()
    )
    ordered = ordered.merge(coverage, on=["epi_year", "epi_week"], how="left")
    ordered["semana_completa"] = ordered["clima_completo"] & ordered["bairros_dengue"].eq(neighborhoods)
    complete_positions = np.flatnonzero(ordered["semana_completa"].to_numpy())
    if not len(complete_positions):
        raise ValueError("Nenhuma semana possui simultaneamente clima e dengue completos.")
    latest_position = int(complete_positions[-1])
    gaps = ordered.iloc[: latest_position + 1].loc[lambda frame: ~frame["semana_completa"]]
    if not gaps.empty:
        labels = [f"{int(row.epi_year)}-{int(row.epi_week):02d}" for row in gaps.itertuples()]
        raise ValueError(
            "Existem semanas incompletas antes da semana mais recente: " + ", ".join(labels[:12])
        )
    return ordered.iloc[: latest_position + 1].drop(
        columns=["_week_start", "clima_completo", "bairros_dengue", "semana_completa"]
    )


def build_operational_base(
    population: pd.DataFrame,
    climate: pd.DataFrame,
    dengue_weekly: pd.DataFrame,
) -> pd.DataFrame:
    """Monta o painel semanal usando apenas semanas completas nas duas fontes."""
    population = _validate_population(population)
    dengue = dengue_weekly.copy()
    dengue["bairro_norm"] = dengue["bairro_norm"].astype(str).str.strip().str.upper()
    dengue["epi_year"] = pd.to_numeric(dengue["epi_year"], errors="raise").astype(int)
    dengue["epi_week"] = pd.to_numeric(dengue["epi_week"], errors="raise").astype(int)
    dengue["casos_totais"] = pd.to_numeric(dengue["casos_totais"], errors="raise").fillna(0).astype(int)
    dengue = dengue.groupby(["bairro_norm", "epi_year", "epi_week"], as_index=False)["casos_totais"].sum()

    complete_climate = _complete_climate_weeks(climate, dengue, len(population)).copy()
    complete_climate["time_index"] = np.arange(len(complete_climate), dtype=int)
    complete_climate["week_sin"] = np.sin(2 * math.pi * complete_climate["epi_week"] / 53.0)
    complete_climate["week_cos"] = np.cos(2 * math.pi * complete_climate["epi_week"] / 53.0)

    base = population[["bairro_norm", "populacao"]].merge(
        complete_climate, how="cross"
    ).merge(
        dengue,
        on=["bairro_norm", "epi_year", "epi_week"],
        how="left",
        validate="one_to_one",
    )
    if base["casos_totais"].isna().any():
        raise ValueError("A tabela dengue_semanal_bairro deve conter inclusive os zeros semanais.")
    return base.sort_values(["bairro_norm", "time_index"]).reset_index(drop=True)


def build_operational_features(base: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Cria atributos para treino ou inferencia, inclusive nas semanas sem alvo observado."""
    if horizon not in range(1, 5):
        raise ValueError("O horizonte deve estar entre 1 e 4 semanas.")
    panel = base.copy()
    targets = [
        advance_epidemiological_week(year, week, horizon)
        for year, week in zip(panel["epi_year"], panel["epi_week"])
    ]
    panel["target_epi_year"] = [target[0] for target in targets]
    panel["target_epi_week"] = [target[1] for target in targets]
    panel["target_time_index"] = panel["time_index"] + horizon
    return build_criticality_panel(panel, horizon)


def latest_origin(features: pd.DataFrame) -> tuple[int, int]:
    latest_index = int(features["time_index"].max())
    row = features.loc[features["time_index"].eq(latest_index)].iloc[0]
    return int(row["epi_year"]), int(row["epi_week"])


def feature_rows_for_origin(features: pd.DataFrame, year: int, week: int) -> pd.DataFrame:
    selected = features.loc[
        features["epi_year"].astype(int).eq(int(year))
        & features["epi_week"].astype(int).eq(int(week))
    ].copy()
    required = CRITICALITY_NUMERIC_FEATURES + ["bairro_norm"]
    selected = selected.dropna(subset=required)
    if len(selected) != 94:
        raise ValueError(
            f"A origem {year}-{week:02d} deveria produzir 94 bairros; produziu {len(selected)}."
        )
    return selected.sort_values("bairro_norm").reset_index(drop=True)


def format_predictions(
    feature_rows: pd.DataFrame,
    probabilities: np.ndarray,
    horizon: int,
    model_version: str,
    generated_at: str | None = None,
) -> pd.DataFrame:
    probabilities = np.asarray(probabilities, dtype=float)
    if probabilities.shape != (len(feature_rows), 4):
        raise ValueError(f"Probabilidades com formato inesperado: {probabilities.shape}")
    generated_at = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    predicted_ids = probabilities.argmax(axis=1)
    output = pd.DataFrame(
        {
            "modelo": "XGBoost",
            "versao_modelo": model_version,
            "data_geracao": generated_at,
            "modo_resultado": PRODUCTION_MODE,
            "epi_year_origem": feature_rows["epi_year"].astype(int),
            "epi_week_origem": feature_rows["epi_week"].astype(int),
            "target_epi_year": feature_rows["target_epi_year"].astype(int),
            "target_epi_week": feature_rows["target_epi_week"].astype(int),
            "horizonte_semanas": int(horizon),
            "bairro_norm": feature_rows["bairro_norm"].astype(str),
            "populacao": feature_rows["populacao"].round().astype(int),
            "casos_observados_recentes_4s": feature_rows["casos_soma4"].round().astype(int),
            "incidencia_recente_4s_100k": feature_rows["incidencia_recente_4s_100k"].astype(float),
            "categoria_recente_observada": [
                display_category(value)
                for value in category_from_incidence(feature_rows["incidencia_recente_4s_100k"])
            ],
            "categoria_prevista": [RISK_ID_DISPLAY[int(identifier)] for identifier in predicted_ids],
            "confianca_modelo": probabilities.max(axis=1),
            "prob_baixo": probabilities[:, 0],
            "prob_medio": probabilities[:, 1],
            "prob_alto": probabilities[:, 2],
            "prob_critico": probabilities[:, 3],
            "casos_observados_alvo_4s": pd.NA,
            "incidencia_observada_alvo_4s_100k": pd.NA,
            "categoria_observada_alvo": pd.NA,
            "previsao_correta": pd.NA,
            "status_avaliacao": "Pendente",
            "data_avaliacao": pd.NA,
        }
    )
    output["semana_origem"] = (
        output["epi_year_origem"].astype(str) + "-" + output["epi_week_origem"].astype(str).str.zfill(2)
    )
    output["semana_alvo"] = (
        output["target_epi_year"].astype(str) + "-" + output["target_epi_week"].astype(str).str.zfill(2)
    )
    return output


def evaluate_operational_predictions(
    predictions: pd.DataFrame,
    base: pd.DataFrame,
    lag_weeks: int = EVALUATION_LAG_WEEKS,
    evaluated_at: str | None = None,
) -> pd.DataFrame:
    """Anexa resultados observados, distinguindo provisório e consolidado."""
    if predictions.empty:
        return predictions.copy()
    evaluated_at = evaluated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    actual = base[["bairro_norm", "epi_year", "epi_week", "time_index", "populacao", "casos_totais"]].copy()
    actual["casos_observados_alvo_4s"] = (
        actual.groupby("bairro_norm")["casos_totais"]
        .rolling(4, min_periods=4)
        .sum()
        .reset_index(level=0, drop=True)
    )
    actual["incidencia_observada_alvo_4s_100k"] = (
        actual["casos_observados_alvo_4s"] / actual["populacao"] * 100_000
    )
    actual["categoria_observada_alvo"] = category_from_incidence(
        actual["incidencia_observada_alvo_4s_100k"]
    )
    actual.loc[actual["casos_observados_alvo_4s"].isna(), "categoria_observada_alvo"] = pd.NA
    actual["categoria_observada_alvo"] = actual["categoria_observada_alvo"].map(
        lambda value: display_category(value) if pd.notna(value) else pd.NA
    )
    actual = actual.rename(columns={"epi_year": "target_epi_year", "epi_week": "target_epi_week"})

    observed_columns = [
        "bairro_norm", "target_epi_year", "target_epi_week", "time_index",
        "casos_observados_alvo_4s", "incidencia_observada_alvo_4s_100k",
        "categoria_observada_alvo",
    ]
    base_columns = [column for column in predictions.columns if column not in {
        "casos_observados_alvo_4s", "incidencia_observada_alvo_4s_100k",
        "categoria_observada_alvo", "previsao_correta", "status_avaliacao", "data_avaliacao",
    }]
    output = predictions[base_columns].merge(
        actual[observed_columns],
        on=["bairro_norm", "target_epi_year", "target_epi_week"],
        how="left",
        validate="many_to_one",
    )
    latest_index = int(base["time_index"].max())
    has_result = output["categoria_observada_alvo"].notna()
    age = latest_index - output["time_index"]
    output["status_avaliacao"] = np.select(
        [has_result & age.ge(int(lag_weeks)), has_result],
        ["Consolidado", "Provisório"],
        default="Pendente",
    )
    output["previsao_correta"] = pd.array([pd.NA] * len(output), dtype="boolean")
    output.loc[has_result, "previsao_correta"] = (
        output.loc[has_result, "categoria_prevista"].eq(output.loc[has_result, "categoria_observada_alvo"])
    ).to_numpy()
    output["data_avaliacao"] = pd.NA
    output.loc[has_result, "data_avaliacao"] = evaluated_at
    return output.drop(columns="time_index")


def production_metrics(
    predictions: pd.DataFrame,
    minimum_target_weeks: int = MIN_PRODUCTION_EVALUATION_WEEKS,
) -> pd.DataFrame:
    """Calcula métricas somente com previsões consolidadas e amostra suficiente."""
    consolidated = predictions.loc[predictions["status_avaliacao"].eq("Consolidado")].copy()
    rows: list[dict] = []
    for horizon, frame in consolidated.groupby("horizonte_semanas"):
        target_weeks = (
            frame[["target_epi_year", "target_epi_week"]]
            .drop_duplicates()
            .sort_values(["target_epi_year", "target_epi_week"])
            .reset_index(drop=True)
        )
        if len(target_weeks) < int(minimum_target_weeks):
            continue
        actual = frame["categoria_observada_alvo"].map(RISK_DISPLAY_TO_ID).to_numpy(dtype=int)
        predicted = frame["categoria_prevista"].map(RISK_DISPLAY_TO_ID).to_numpy(dtype=int)
        rows.append(
            {
                "modelo": "XGBoost",
                "versao_modelo": str(frame["versao_modelo"].iloc[-1]),
                "fonte": "producao",
                "horizonte_semanas": int(horizon),
                "n_amostras_teste": int(len(frame)),
                "semanas_avaliadas": int(len(target_weeks)),
                "periodo_inicio": f"{int(target_weeks.iloc[0, 0])}-{int(target_weeks.iloc[0, 1]):02d}",
                "periodo_fim": f"{int(target_weeks.iloc[-1, 0])}-{int(target_weeks.iloc[-1, 1]):02d}",
                "acuracia": float(accuracy_score(actual, predicted)),
                "acuracia_balanceada": float(
                    recall_score(
                        actual,
                        predicted,
                        labels=np.unique(actual),
                        average="macro",
                        zero_division=0,
                    )
                ),
                "f1_macro": float(f1_score(actual, predicted, labels=[0, 1, 2, 3], average="macro", zero_division=0)),
                "f2_macro": float(fbeta_score(actual, predicted, beta=2, labels=[0, 1, 2, 3], average="macro", zero_division=0)),
                "atualizado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
        )
    return pd.DataFrame(rows)
