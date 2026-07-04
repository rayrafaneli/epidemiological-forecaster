import re
import unicodedata
from pathlib import Path

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
import xgboost as xgb

RAW_DATA_DIR = Path("data/raw")
READY_DIR = Path("data/ready")
OUTPUT_PATH = READY_DIR / "dataset_recife_features.csv"


def normalize_text(value: str) -> str:
    """Normaliza nome de bairro pra conseguir fazer merge certinho."""
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    text = text.replace("(pe)", "")
    text = text.replace("- recife", "")
    text = text.replace("recife", "")
    text = text.strip()
    return text


def _read_csv_with_encodings(path: Path, **kwargs) -> pd.DataFrame:
    """Tenta ler CSV como UTF-8 e, se falhar, tenta latin1."""
    for encoding in ["utf-8", "latin1"]:
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except Exception:
            continue
    raise ValueError(f"Unable to read CSV with utf-8 or latin1: {path}")


def _find_header_skip(lines, marker: str):
    for idx, line in enumerate(lines):
        if marker in line:
            return idx
    return None


def load_dengue_data(raw_dir: Path) -> pd.DataFrame:
    """Carrega dados de dengue e agrupa por bairro e semana epidemiológica."""
    dengue_files = sorted(set(raw_dir.glob("*casos-de-dengue*.csv")) | set(raw_dir.glob("*resources_*casos-de-dengue*.csv")))
    if not dengue_files:
        raise FileNotFoundError("Nenhum arquivo de dengue encontrado em data/raw.")

    frames = []
    for path in dengue_files:
        df = _read_csv_with_encodings(path, sep=";", quotechar='"', engine="python")
        df.columns = [str(col).strip().lower() for col in df.columns]
        frames.append(df)

    dengue = pd.concat(frames, ignore_index=True)
    dengue = dengue.loc[:, ~dengue.columns.duplicated()].copy()

    date_columns = [c for c in dengue.columns if c in {"dt_notific", "dt_notificacao", "dt_notificacao", "dt_notificao"}]
    if date_columns:
        date_col = date_columns[0]
    else:
        date_col = next((c for c in dengue.columns if "dt" in c and "not" in c), None)

    bairro_columns = [c for c in dengue.columns if c in {"nm_bairro", "no_bairro_residencia", "nm_bairro_residencia"}]
    if bairro_columns:
        bairro_col = bairro_columns[0]
    else:
        raise KeyError("Não foi possível encontrar coluna de bairro nos arquivos de dengue.")

    dengue[date_col] = pd.to_datetime(dengue[date_col].astype(str).str.strip(), dayfirst=True, errors="coerce")
    dengue = dengue.dropna(subset=[date_col]).copy()
    if dengue.empty:
        raise ValueError("Falha ao converter datas de notificação de dengue.")

    epi_date = dengue[date_col].dt.isocalendar()
    dengue["epi_year"] = epi_date["year"]
    dengue["epi_week"] = epi_date["week"]

    dengue["bairro_norm"] = dengue[bairro_col].astype(str).apply(normalize_text)
    dengue = dengue[dengue["bairro_norm"] != ""].copy()

    grouped = (
        dengue.groupby(["bairro_norm", "epi_year", "epi_week"], as_index=False)
        .size()
        .rename(columns={"size": "casos_totais"})
    )
    grouped["bairro"] = grouped["bairro_norm"]
    return grouped


def load_climate_data(raw_dir: Path) -> pd.DataFrame:
    """Lê clima INMET, agrega por semana epi e cria lags de chuva/temperatura."""
    inmet_path = next(raw_dir.glob("*dados_INMET*.csv"), None)
    if inmet_path is None:
        raise FileNotFoundError("Arquivo INMET não encontrado em data/raw.")

    with inmet_path.open("r", encoding="utf-8", errors="ignore") as handle:
        lines = handle.readlines()

    header_skip = _find_header_skip(lines, "Data Medicao")
    if header_skip is None:
        raise ValueError("Cabeçalho de INMET não encontrado no arquivo.")

    climate = _read_csv_with_encodings(inmet_path, sep=";", skiprows=header_skip, engine="python")
    climate.columns = [str(col).strip() for col in climate.columns]

    date_col = next((c for c in climate.columns if "data" in c.lower()), None)
    precip_col = next((c for c in climate.columns if "precipitacao" in c.lower()), None)
    temp_max_col = next((c for c in climate.columns if "temperatura maxima" in c.lower()), None)

    if not {date_col, precip_col, temp_max_col}:
        raise KeyError("Colunas obrigatórias de clima não foram encontradas.")

    climate[date_col] = pd.to_datetime(climate[date_col].astype(str).str.strip(), dayfirst=True, errors="coerce")
    climate = climate.dropna(subset=[date_col]).copy()

    climate[precip_col] = pd.to_numeric(climate[precip_col].astype(str).str.replace(",", "."), errors="coerce")
    climate[temp_max_col] = pd.to_numeric(climate[temp_max_col].astype(str).str.replace(",", "."), errors="coerce")

    iso = climate[date_col].dt.isocalendar()
    climate["epi_year"] = iso["year"].astype(int)
    climate["epi_week"] = iso["week"].astype(int)

    weekly = (
        climate.groupby(["epi_year", "epi_week"], as_index=False)
        .agg(
            precipitacao_total=(precip_col, "sum"),
            temp_max_media=(temp_max_col, "mean"),
        )
    )
    weekly = weekly.sort_values(["epi_year", "epi_week"]).reset_index(drop=True)

    for lag in range(1, 5):
        weekly[f"chuva_lag{lag}"] = weekly["precipitacao_total"].shift(lag)
        weekly[f"temp_max_lag{lag}"] = weekly["temp_max_media"].shift(lag)

    return weekly


def load_population_data(raw_dir: Path) -> pd.DataFrame:
    """Carrega população IBGE e ajeita os nomes de bairro."""
    ibge_path = raw_dir / "sidra-ibge-recife-2022.csv"
    if not ibge_path.exists():
        raise FileNotFoundError("Arquivo de população IBGE não encontrado em data/raw.")

    with ibge_path.open("r", encoding="utf-8", errors="ignore") as handle:
        lines = handle.readlines()

    header_skip = None
    for idx, line in enumerate(lines):
        if "Brasil e Bairro" in line and ("Total" in line or "2022" in line):
            header_skip = idx
            break
    if header_skip is None:
        raise ValueError("Cabeçalho do IBGE não encontrado no arquivo.")

    population = _read_csv_with_encodings(ibge_path, sep=";", skiprows=header_skip, engine="python")
    population.columns = [str(col).strip() for col in population.columns]

    if "Total" in population.columns:
        population = population.rename(columns={"Cód.": "cod", "Brasil e Bairro": "bairro", "Total": "populacao"})
    elif "2022" in population.columns:
        population = population.rename(columns={"Cód.": "cod", "Brasil e Bairro": "bairro", "2022": "populacao"})
    else:
        raise KeyError("Coluna de população não encontrada no IBGE.")

    population = population.loc[population["bairro"].astype(str).str.lower() != "brasil"].copy()

    def simplify_bairro(name: str) -> str:
        if not isinstance(name, str):
            return ""
        match = re.match(r"^(.*?) - Recife", name, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return name.strip()

    population["bairro"] = population["bairro"].astype(str).apply(simplify_bairro)
    population["bairro_norm"] = population["bairro"].apply(normalize_text)
    population["populacao"] = pd.to_numeric(population["populacao"].astype(str).str.replace("\"", ""), errors="coerce")
    population = population.dropna(subset=["populacao", "bairro_norm"]).copy()
    population["populacao"] = population["populacao"].astype(int)

    return population[["bairro_norm", "populacao"]].drop_duplicates(subset=["bairro_norm"])


def build_features() -> pd.DataFrame:
    """Monta o DataFrame final juntando dengue, IBGE e clima."""
    dengue = load_dengue_data(RAW_DATA_DIR)
    population = load_population_data(RAW_DATA_DIR)
    climate = load_climate_data(RAW_DATA_DIR)

    merged = dengue.merge(population, how="left", left_on="bairro_norm", right_on="bairro_norm")
    merged = merged.dropna(subset=["populacao"]).copy()

    final = merged.merge(climate, how="left", on=["epi_year", "epi_week"])
    final["taxa_incidencia_100k"] = (final["casos_totais"] / final["populacao"]) * 100_000
    final = final.sort_values(["bairro_norm", "epi_year", "epi_week"]).reset_index(drop=True)
    return final


def train_baseline_model(df_final: pd.DataFrame) -> xgb.XGBRegressor:
    """Treina o XGBoost baseline e mostra as métricas na tela."""
    feature_columns = [
        "populacao",
        "epi_year",
        "epi_week",
        "precipitacao_total",
        "temp_max_media",
        "chuva_lag1",
        "chuva_lag2",
        "chuva_lag3",
        "chuva_lag4",
        "temp_max_lag1",
        "temp_max_lag2",
        "temp_max_lag3",
        "temp_max_lag4",
    ]

    df_model = df_final.copy()
    df_model = df_model.dropna(subset=["populacao", "casos_totais"]).reset_index(drop=True)

    train_mask = df_model["epi_year"] <= 2024
    test_mask = df_model["epi_year"] == 2025

    X_train = df_model.loc[train_mask, feature_columns]
    y_train = df_model.loc[train_mask, "casos_totais"]
    X_test = df_model.loc[test_mask, feature_columns]
    y_test = df_model.loc[test_mask, "casos_totais"]

    if X_train.empty:
        raise ValueError("Não há dados de treinamento antes de 2025.")
    if X_test.empty:
        raise ValueError("Não há dados de validação para 2025.")

    model = xgb.XGBRegressor(
        objective="reg:squarederror",
        random_state=42,
        n_estimators=100,
        learning_rate=0.1,
        verbosity=0,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred) ** 0.5

    print("Baseline XGBoost model trained")
    print(f"Treino: {len(X_train)} linhas | Validação 2025: {len(X_test)} linhas")
    print(f"MAE: {mae:.2f}")
    print(f"RMSE: {rmse:.2f}")

    feature_importances = pd.Series(model.feature_importances_, index=feature_columns)
    top_features = feature_importances.sort_values(ascending=False).head(5)
    print("Top 5 features mais importantes:")
    for feature, importance in top_features.items():
        print(f"- {feature}: {importance:.4f}")

    return model


def main() -> None:
    READY_DIR.mkdir(parents=True, exist_ok=True)
    print("Construindo features baselines para dengue em Recife...")
    df_final = build_features()
    print(f"DataFrame final construído com {len(df_final)} linhas.")
    df_final.to_csv(OUTPUT_PATH, index=False)
    print(f"Dataset salvo em: {OUTPUT_PATH}")
    train_baseline_model(df_final)


if __name__ == "__main__":
    main()
