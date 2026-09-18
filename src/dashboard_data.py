"""Contrato de dados do dashboard operacional de criticidade.

O módulo combina previsões operacionais e resultados da validação temporal com
os metadados e campos derivados usados pela API e pelo Streamlit.
"""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from src.config import CRITICALITY_RESULTS_DIR, DATA_DIR, PROJECT_ROOT
from src.operational_store import (
    CLIMATE_TABLE,
    DENGUE_WEEKLY_TABLE,
    METRICS_TABLE,
    POPULATION_TABLE,
    PREDICTION_TABLE,
)


MODEL_VERSION = "criticidade_v2"
DATA_SOURCE = os.getenv("DATA_SOURCE", "auto").strip().lower()

RISK_LABELS_DISPLAY = ["Baixo", "Médio", "Alto", "Crítico"]
RISK_ORDER = {label: index for index, label in enumerate(RISK_LABELS_DISPLAY)}
RISK_DISPLAY = {
    "Baixo": "Baixo",
    "Medio": "Médio",
    "Médio": "Médio",
    "Alto": "Alto",
    "Critico": "Crítico",
    "Crítico": "Crítico",
}


def display_category(value: object) -> object:
    """Padroniza os rótulos internos sem acento para exibição em português."""
    if pd.isna(value):
        return pd.NA
    return RISK_DISPLAY.get(str(value), str(value))


def category_from_incidence(values: Iterable[float] | pd.Series) -> np.ndarray:
    incidence = np.asarray(values, dtype=float)
    return np.select(
        [incidence < 100, incidence < 300, incidence < 500],
        RISK_LABELS_DISPLAY[:3],
        default=RISK_LABELS_DISPLAY[3],
    )


def _generated_at(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")


def enrich_prediction_frame(frame: pd.DataFrame, horizon: int, generated_at: str) -> pd.DataFrame:
    """Transforma o output de avaliação em um contrato próprio para apresentação."""
    output = frame.copy()
    output = output.rename(
        columns={
            "epi_year": "epi_year_origem",
            "epi_week": "epi_week_origem",
            "casos_acumulados_4s_alvo": "casos_observados_alvo_4s",
            "incidencia_4s_alvo_100k": "incidencia_observada_alvo_4s_100k",
            "categoria_criticidade_alvo": "categoria_observada_alvo",
        }
    )
    integer_columns = [
        "epi_year_origem",
        "epi_week_origem",
        "target_epi_year",
        "target_epi_week",
        "populacao",
    ]
    for column in integer_columns:
        output[column] = pd.to_numeric(output[column], errors="raise").round().astype(int)

    output["horizonte_semanas"] = int(horizon)
    output["versao_modelo"] = MODEL_VERSION
    output["data_geracao"] = generated_at
    output["modo_resultado"] = "validacao_historica_2021"
    output["categoria_prevista"] = output["categoria_prevista"].map(display_category)
    output["categoria_observada_alvo"] = output["categoria_observada_alvo"].map(display_category)
    output["casos_observados_recentes_4s"] = np.rint(
        output["incidencia_recente_4s_100k"] * output["populacao"] / 100_000
    ).astype(int)
    output["categoria_recente_observada"] = category_from_incidence(
        output["incidencia_recente_4s_100k"]
    )
    probability_columns = ["prob_baixo", "prob_medio", "prob_alto", "prob_critico"]
    output["confianca_modelo"] = output[probability_columns].max(axis=1)
    output["previsao_correta"] = output["categoria_prevista"].eq(output["categoria_observada_alvo"])
    output["status_avaliacao"] = "Consolidado"
    output["data_avaliacao"] = generated_at
    output["semana_origem"] = (
        output["epi_year_origem"].astype(str)
        + "-"
        + output["epi_week_origem"].astype(str).str.zfill(2)
    )
    output["semana_alvo"] = (
        output["target_epi_year"].astype(str)
        + "-"
        + output["target_epi_week"].astype(str).str.zfill(2)
    )

    columns = [
        "modelo",
        "versao_modelo",
        "data_geracao",
        "modo_resultado",
        "epi_year_origem",
        "epi_week_origem",
        "semana_origem",
        "target_epi_year",
        "target_epi_week",
        "semana_alvo",
        "horizonte_semanas",
        "bairro_norm",
        "populacao",
        "casos_observados_recentes_4s",
        "incidencia_recente_4s_100k",
        "categoria_recente_observada",
        "categoria_prevista",
        "confianca_modelo",
        "prob_baixo",
        "prob_medio",
        "prob_alto",
        "prob_critico",
        "casos_observados_alvo_4s",
        "incidencia_observada_alvo_4s_100k",
        "categoria_observada_alvo",
        "previsao_correta",
        "status_avaliacao",
        "data_avaliacao",
    ]
    return output[columns].sort_values(
        ["epi_year_origem", "epi_week_origem", "horizonte_semanas", "bairro_norm"]
    ).reset_index(drop=True)


def build_dashboard_export(
    results_dir: Path = CRITICALITY_RESULTS_DIR,
    output_path: Path | None = None,
) -> Path:
    """Combina S+1 a S+4 e grava o dataset consumido pela aplicação."""
    frames: list[pd.DataFrame] = []
    for horizon in range(1, 5):
        source = results_dir / f"previsoes_xgboost_h{horizon}.csv"
        if not source.exists():
            raise FileNotFoundError(f"Previsões ausentes para S+{horizon}: {source}")
        frames.append(enrich_prediction_frame(pd.read_csv(source), horizon, _generated_at(source)))
    destination = output_path or (results_dir / "previsoes_xgboost_dashboard.csv")
    destination.parent.mkdir(parents=True, exist_ok=True)
    validation = pd.concat(frames, ignore_index=True)
    if destination.exists():
        existing = pd.read_csv(destination)
        if "modo_resultado" in existing:
            production = existing.loc[existing["modo_resultado"].eq("producao")].copy()
            if not production.empty:
                validation = pd.concat([validation, production], ignore_index=True, sort=False)
    validation.to_csv(destination, index=False, encoding="utf-8-sig")
    return destination


class DashboardRepository:
    """Acesso aos dados locais, com suporte opcional às tabelas do Supabase."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self._engine = None

    @property
    def engine(self):
        if not self.database_url:
            return None
        if self._engine is None:
            from sqlalchemy import create_engine

            self._engine = create_engine(self.database_url, pool_pre_ping=True)
        return self._engine

    def _read_table(self, table: str, fallback: Path) -> pd.DataFrame:
        if self.engine is not None:
            try:
                return pd.read_sql_table(table, self.engine)
            except Exception:
                if DATA_SOURCE == "database" or not fallback.exists():
                    raise
        if DATA_SOURCE == "database":
            raise RuntimeError(f"DATABASE_URL é obrigatória para ler a tabela {table} em produção.")
        return pd.read_csv(fallback)

    def predictions(self) -> pd.DataFrame:
        fallback = CRITICALITY_RESULTS_DIR / "previsoes_xgboost_dashboard.csv"
        if self.engine is not None:
            try:
                frame = pd.read_sql_table(PREDICTION_TABLE, self.engine)
                for column in ["categoria_prevista", "categoria_observada_alvo", "categoria_recente_observada"]:
                    if column in frame:
                        frame[column] = frame[column].map(display_category)
                return frame
            except Exception:
                if DATA_SOURCE == "database" or not fallback.exists():
                    raise
        if DATA_SOURCE == "database":
            raise RuntimeError("DATABASE_URL é obrigatória para carregar previsões em produção.")
        if not fallback.exists():
            build_dashboard_export(output_path=fallback)
        frame = pd.read_csv(fallback)
        for column in ["categoria_prevista", "categoria_observada_alvo", "categoria_recente_observada"]:
            if column in frame:
                frame[column] = frame[column].map(display_category)
        return frame

    def population(self) -> pd.DataFrame:
        return self._read_table(
            POPULATION_TABLE,
            DATA_DIR / "populacao_censo_2022_processada.csv",
        )

    def climate(self) -> pd.DataFrame:
        return self._read_table(
            CLIMATE_TABLE,
            DATA_DIR / "clima_2015_2021_processado.csv",
        )

    def observations(self) -> pd.DataFrame:
        """Retorna casos semanais já completos, incluindo semanas com zero casos."""
        fallback = DATA_DIR / "painel_semanal_2015_2021_h1.csv"
        if self.engine is None:
            columns = ["bairro_norm", "epi_year", "epi_week", "time_index", "casos_totais"]
            return pd.read_csv(fallback, usecols=columns)

        frame = pd.read_sql_table(DENGUE_WEEKLY_TABLE, self.engine)
        required = ["bairro_norm", "epi_year", "epi_week", "time_index", "casos_totais"]
        missing = set(required).difference(frame.columns)
        if missing:
            raise ValueError(f"Colunas ausentes em {DENGUE_WEEKLY_TABLE}: {sorted(missing)}")
        return frame[required]

    def metrics(self) -> pd.DataFrame:
        if self.engine is not None:
            try:
                metrics = pd.read_sql_table(METRICS_TABLE, self.engine)
                production = metrics.loc[metrics["fonte"].eq("producao")].copy()
                if not production.empty:
                    versions = (
                        production.groupby("versao_modelo")["horizonte_semanas"]
                        .nunique()
                        .loc[lambda values: values.eq(4)]
                    )
                    if not versions.empty:
                        eligible = production.loc[production["versao_modelo"].isin(versions.index)].copy()
                        eligible["atualizado_em"] = pd.to_datetime(eligible["atualizado_em"], errors="coerce")
                        latest_version = eligible.sort_values("atualizado_em").iloc[-1]["versao_modelo"]
                        return eligible.loc[eligible["versao_modelo"].eq(latest_version)].reset_index(drop=True)
                validation = metrics.loc[metrics["fonte"].eq("validacao_2021")].copy()
                if not validation.empty:
                    return validation.sort_values("horizonte_semanas").reset_index(drop=True)
            except Exception:
                if DATA_SOURCE == "database":
                    raise
        if DATA_SOURCE == "database":
            raise RuntimeError(f"Não foi possível carregar {METRICS_TABLE} do banco de produção.")
        path = CRITICALITY_RESULTS_DIR / "comparacao_todos_horizontes.csv"
        metrics = pd.read_csv(path)
        metrics = metrics.loc[metrics["modelo"].eq("XGBoost")].reset_index(drop=True)
        metrics["fonte"] = "validacao_2021"
        metrics["versao_modelo"] = MODEL_VERSION
        metrics["semanas_avaliadas"] = pd.NA
        metrics["periodo_inicio"] = "2021-01"
        metrics["periodo_fim"] = "2021-52"
        return metrics

    def feature_importance(self, horizon: int) -> pd.DataFrame:
        path = CRITICALITY_RESULTS_DIR / f"importancia_features_xgboost_h{horizon}.csv"
        return pd.read_csv(path)


def common_origins(predictions: pd.DataFrame) -> list[tuple[int, int]]:
    """Semanas de origem com previsões simultâneas em todos os horizontes."""
    origin_sets = []
    for horizon in range(1, 5):
        rows = predictions.loc[predictions["horizonte_semanas"].eq(horizon)]
        origin_sets.append(set(zip(rows["epi_year_origem"].astype(int), rows["epi_week_origem"].astype(int))))
    return sorted(set.intersection(*origin_sets))
