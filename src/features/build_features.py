import os
import re
import unicodedata

import pandas as pd
from sqlalchemy import create_engine
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def connect_to_database():
    if not DATABASE_URL:
        raise ValueError("Variável DATABASE_URL não encontrada no arquivo .env")
    return create_engine(DATABASE_URL)

def normalize_text(value: str) -> str:
    if pd.isna(value):
        return ""
    text_str = str(value).strip().lower()
    text_str = unicodedata.normalize("NFKD", text_str)
    text_str = "".join(ch for ch in text_str if not unicodedata.combining(ch))
    text_str = re.sub(r"\s+", " ", text_str)
    text_str = text_str.replace("(pe)", "").replace("- recife", "").replace("recife", "")
    return text_str.strip()

def load_dengue_from_db(engine) -> pd.DataFrame:
    query = """
        SELECT nm_bairro, dt_notific 
        FROM dengue 
        WHERE nm_bairro IS NOT NULL AND dt_notific IS NOT NULL
    """
    dengue = pd.read_sql(query, engine)
    dengue["dt_notific"] = pd.to_datetime(dengue["dt_notific"], errors="coerce")
    dengue = dengue.dropna(subset=["dt_notific"])

    epi_date = dengue["dt_notific"].dt.isocalendar()
    dengue["epi_year"] = epi_date["year"].astype(int)
    dengue["epi_week"] = epi_date["week"].astype(int)

    dengue["bairro_norm"] = dengue["nm_bairro"].apply(normalize_text)
    dengue = dengue[dengue["bairro_norm"] != ""]

    grouped = (
        dengue.groupby(["bairro_norm", "epi_year", "epi_week"], as_index=False)
        .size()
        .rename(columns={"size": "casos_totais"})
    )
    return grouped

def build_features() -> pd.DataFrame:
    engine = connect_to_database()

    df_dengue = load_dengue_from_db(engine)
    print(f"[DEBUG] Linhas em Dengue apos agrupar: {len(df_dengue)}")

    df_pop = pd.read_sql("SELECT LOWER(bairro_norm) as bairro_norm, populacao FROM ibge_populacao_bairro", engine)
    print(f"[DEBUG] Linhas em IBGE Populacao: {len(df_pop)}")

    df_clima = pd.read_sql("SELECT * FROM inmet_semanal_recife", engine)
    print(f"[DEBUG] Linhas em Clima INMET: {len(df_clima)}")

    merged = df_dengue.merge(df_pop, how="left", on="bairro_norm")
    print(f"[DEBUG] Linhas apos merge com IBGE (antes do dropna): {len(merged)}")

    merged = merged.dropna(subset=["populacao"])
    print(f"[DEBUG] Linhas apos apagar bairros sem match de populacao: {len(merged)}")

    final = merged.merge(df_clima, how="left", on=["epi_year", "epi_week"])
    
    final["taxa_incidencia_100k"] = (final["casos_totais"] / final["populacao"]) * 100_000
    final = final.sort_values(["bairro_norm", "epi_year", "epi_week"]).reset_index(drop=True)
    
    return final

def train_baseline_model(df_final: pd.DataFrame) -> xgb.XGBRegressor:
    feature_columns = [
        "populacao", "epi_year", "epi_week", "precipitacao_total", "temp_max_media",
        "chuva_lag1", "chuva_lag2", "chuva_lag3", "chuva_lag4",
        "temp_max_lag1", "temp_max_lag2", "temp_max_lag3", "temp_max_lag4"
    ]

    df_model = df_final.dropna(subset=["populacao", "casos_totais"]).reset_index(drop=True)

    train_mask = df_model["epi_year"] <= 2024
    test_mask = df_model["epi_year"] == 2025

    X_train = df_model.loc[train_mask, feature_columns]
    y_train = df_model.loc[train_mask, "casos_totais"]
    X_test = df_model.loc[test_mask, feature_columns]
    y_test = df_model.loc[test_mask, "casos_totais"]

    if X_train.empty or X_test.empty:
        raise ValueError("Dados insuficientes para treino ou teste. Verifique o range de anos e os joins climaticos.")

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

    print("Baseline XGBoost model trained via Supabase")
    print(f"Treino: {len(X_train)} linhas | Validacao 2025: {len(X_test)} linhas")
    print(f"MAE: {mae:.2f}")
    print(f"RMSE: {rmse:.2f}")

    feature_importances = pd.Series(model.feature_importances_, index=feature_columns)
    top_features = feature_importances.sort_values(ascending=False).head(5)
    print("Top 5 features mais importantes:")
    for feature, importance in top_features.items():
        print(f"- {feature}: {importance:.4f}")

    # Salva o arquivo fisico na raiz do projeto
    model_path = "model_xgb_recife.json"
    model.save_model(model_path)
    print(f"Modelo salvo com sucesso em: {model_path}")

    return model

def main():
    print("Extraindo dados do Supabase e construindo features...")
    df_final = build_features()
    print(f"DataFrame final construido com {len(df_final)} linhas.")
    train_baseline_model(df_final)

if __name__ == "__main__":
    main()