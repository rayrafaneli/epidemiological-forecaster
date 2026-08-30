import os
import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Variável DATABASE_URL não encontrada no arquivo .env")

engine = create_engine(DATABASE_URL)
app = FastAPI(title="SIPD API - Previsao de Dengue")

@app.get("/")
def read_root():
    return {"status": "SIPD API Online", "documentacao": "/docs"}

model = xgb.XGBRegressor()
try:
    model.load_model("model_xgb_recife.json")
except Exception as e:
    print(f"Erro ao carregar o modelo: {e}")

@app.get("/predict/recife")
def predict_recife(ano: int = 2025, semana: int = 1):
    try:
        query_pop = "SELECT LOWER(bairro_norm) as bairro_norm, populacao FROM ibge_populacao_bairro"
        df_pop = pd.read_sql(query_pop, engine)

        query_clima = f"SELECT * FROM inmet_semanal_recife WHERE epi_year = {ano} AND epi_week = {semana}"
        df_clima = pd.read_sql(query_clima, engine)

        if df_clima.empty:
            raise HTTPException(status_code=404, detail="Dados climaticos nao encontrados para esta semana.")

        df_input = df_pop.copy()
        df_input["epi_year"] = ano
        df_input["epi_week"] = semana
        
        for col in df_clima.columns:
            if col not in ["epi_year", "epi_week"]:
                val = df_clima[col].iloc[0]
                # Trata caso venha string com vírgula ou texto
                if isinstance(val, str):
                    val = val.replace(",", ".")
                df_input[col] = pd.to_numeric(val, errors="coerce")

        feature_columns = [
            "populacao", "epi_year", "epi_week", "precipitacao_total", "temp_max_media",
            "chuva_lag1", "chuva_lag2", "chuva_lag3", "chuva_lag4",
            "temp_max_lag1", "temp_max_lag2", "temp_max_lag3", "temp_max_lag4"
        ]

        # Garante que todas as features de entrada sejam estritamente numéricas para o XGBoost
        X_predict = df_input[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
        
        df_input["casos_previstos"] = model.predict(X_predict).round().astype(int)
        df_input["incidencia_100k"] = (df_input["casos_previstos"] / df_input["populacao"]) * 100000

        def classificar_risco(incidencia):
            if incidencia < 100: return "Baixo"
            if incidencia < 300: return "Medio"
            if incidencia < 500: return "Alto"
            return "Critico"

        df_input["nivel_alerta"] = df_input["incidencia_100k"].apply(classificar_risco)

        return df_input[["bairro_norm", "casos_previstos", "incidencia_100k", "nivel_alerta"]].to_dict(orient="records")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))