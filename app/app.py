import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit.components.v1 as components
from contextlib import contextmanager
import os
import unicodedata

import requests

# Requer Streamlit 1.40 ou superior para st.container(height=...).

st.set_page_config(
    page_title="Sistema Inteligente de Predição de Dengue",
    page_icon="🦟",
    layout="wide",
    initial_sidebar_state="expanded",
)

### CSS
st.markdown(
    """
    <style>
        :root {
            --bg: #f5f8fc;
            --panel: #ffffff;
            --border: #dfe9f5;
            --text: #092b4c;
            --muted: #65768a;
            --blue: #1683ff;
            --blue-2: #0b68d8;
            --cyan: #13bfcf;
            --green: #20c665;
            --yellow: #ffd448;
            --orange: #ff8618;
            --red: #f1283c;
            --purple: #8556e8;
            --sidebar: #06243d;
        }

        .stApp {
            background: var(--bg);
            font-family: "Inter", "Segoe UI", Arial, sans-serif;
        }

        .main .block-container {
            padding-top: 1.0rem;
            padding-left: 1.35rem;
            padding-right: 1.35rem;
            max-width: 100%;
        }

        header[data-testid="stHeader"] {
            height: 0;
            min-height: 0;
            background: transparent;
        }

        #MainMenu, footer,
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"],
        div[data-testid="stStatusWidget"] {
            display: none !important;
            visibility: hidden !important;
        }

        [data-testid="stSidebar"] {
            background: radial-gradient(circle at 70% 82%, rgba(20, 132, 255, 0.24), rgba(20, 132, 255, 0) 30%),
                        linear-gradient(180deg, #082f50 0%, #05243e 45%, #031a2d 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
            width: 198px !important;
            min-width: 198px !important;
            max-width: 198px !important;
        }

        [data-testid="stSidebar"] > div:first-child {
            width: 198px !important;
            min-width: 198px !important;
            max-width: 198px !important;
        }

        [data-testid="stSidebar"] * {
            color: #ffffff !important;
        }

        [data-testid="stSidebar"] .stRadio > label {
            display: none;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] > label {
            padding: 13px 14px;
            margin: 7px 0px;
            border-radius: 12px;
            transition: all .15s ease-in-out;
            color: #ffffff !important;
            font-weight: 700;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            background: rgba(255,255,255,0.10);
        }

        [data-testid="stSidebar"] div[role="radiogroup"] > label[data-baseweb="radio"] div:first-child {
            display: none;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
            background: linear-gradient(135deg, #1683ff, #0b68d8);
            box-shadow: 0 10px 26px rgba(22, 131, 255, 0.36);
        }

        h1, h2, h3, h4, h5, h6 {
            color: var(--text) !important;
            letter-spacing: -0.02em;
        }

        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            min-height: 58px;
            padding: 2px 4px 12px 4px;
            border-bottom: 1px solid rgba(206, 219, 234, 0.85);
            margin-bottom: 16px;
        }

        .topbar-title {
            font-size: 24px;
            line-height: 1.15;
            font-weight: 900;
            color: var(--text);
            white-space: nowrap;
        }

        .topbar-controls {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
            justify-content: flex-end;
        }

        .fake-select {
            min-width: 120px;
            height: 42px;
            background: #fff;
            border: 1px solid #dbe6f2;
            border-radius: 10px;
            padding: 6px 12px;
            box-shadow: 0 2px 8px rgba(20, 45, 75, 0.04);
            color: var(--text);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            font-weight: 700;
            font-size: 12px;
        }

        .fake-select.large {
            min-width: 210px;
        }

        .fake-select span {
            display: block;
            font-size: 11px;
            color: #315170;
            font-weight: 800;
            margin-bottom: 1px;
        }

        .bell {
            position: relative;
            font-size: 23px;
            color: #15395d;
            padding: 4px 8px;
        }

        .bell-badge {
            position: absolute;
            right: 2px;
            top: 0px;
            width: 17px;
            height: 17px;
            background: #0d76ee;
            color: white;
            border-radius: 50%;
            font-size: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
        }

        .page-title-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 4px 0 16px 0;
        }

        .page-title {
            font-size: 25px;
            font-weight: 900;
            color: var(--text);
        }

        .breadcrumb {
            font-size: 13px;
            color: #4f6380;
            margin-left: 18px;
            font-weight: 700;
        }

        .btn-outline {
            display: inline-flex;
            gap: 8px;
            align-items: center;
            padding: 10px 16px;
            border-radius: 10px;
            border: 1px solid #cfdceb;
            color: #147af3;
            background: #fff;
            font-weight: 800;
            box-shadow: 0 3px 10px rgba(20, 45, 75, 0.05);
        }

        .card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            box-shadow: 0 8px 22px rgba(17, 42, 70, 0.07);
        }

        .kpi-card {
            height: 122px;
            padding: 18px 18px;
            display: flex;
            align-items: center;
            gap: 16px;
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            box-shadow: 0 8px 22px rgba(17, 42, 70, 0.07);
            overflow: hidden;
            position: relative;
        }

        .kpi-card::after {
            content: "";
            position: absolute;
            left: 14px;
            right: 14px;
            bottom: 0px;
            height: 3px;
            border-radius: 20px 20px 0 0;
            background: var(--accent, #1683ff);
            opacity: .8;
        }

        .kpi-icon {
            width: 58px;
            height: 58px;
            min-width: 58px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--accent, #1683ff);
            color: white;
            font-size: 28px;
            box-shadow: 0 8px 20px rgba(22, 131, 255, 0.22);
        }

        .kpi-title {
            color: var(--text);
            font-weight: 900;
            font-size: 14px;
            margin-bottom: 4px;
        }

        .kpi-value {
            color: #081e35;
            font-size: 29px;
            font-weight: 950;
            line-height: 1.05;
            margin-bottom: 5px;
        }

        .kpi-sub {
            color: var(--muted);
            font-size: 12px;
            font-weight: 650;
        }

        .trend-up { color: var(--red); font-weight: 900; }
        .trend-down { color: #14aa64; font-weight: 900; }
        .trend-good { color: #14aa64; font-weight: 900; }
        .trend-orange { color: var(--orange); font-weight: 900; }

        .panel-title {
            font-size: 16px;
            font-weight: 950;
            color: var(--text);
            margin: 0 0 14px 0;
        }

        .panel-card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            box-shadow: 0 8px 22px rgba(17, 42, 70, 0.07);
            padding: 16px;
            min-height: 100px;
        }

        /*
           Cards de conteúdo. A altura não é mais controlada com seletores CSS
           baseados em :has(). Cada st.container recebe height diretamente no
           Python, o que garante a mesma altura para todos os cards da linha.
        */
        .sipd-section-marker {
            display: none !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            box-sizing: border-box !important;
            background: #ffffff !important;
            border: 1px solid var(--border) !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 22px rgba(17, 42, 70, 0.07) !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"],
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stElementContainer"],
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stMarkdownContainer"] {
            background-color: #ffffff !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"] {
            gap: 0.45rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] .stPlotlyChart {
            margin-top: -0.30rem;
            margin-bottom: -0.15rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] iframe {
            border-radius: 12px;
        }

        /* Barra de rolagem discreta, exibida somente se algum conteúdo exceder o card. */
        div[data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] ::-webkit-scrollbar-thumb {
            background: #c9d8e8;
            border-radius: 999px;
        }

        .rank-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            color: var(--text);
            background: #ffffff;
            border: 0 !important;
        }

        .rank-table th {
            padding: 10px 9px;
            border-left: 0 !important;
            border-right: 0 !important;
            text-align: left;
            background: #f7faff;
            color: #0d3155;
            border-bottom: 1px solid #dfe8f2;
            font-weight: 950;
        }

        .rank-table td {
            padding: 9px 9px;
            border-left: 0 !important;
            border-right: 0 !important;
            border-bottom: 1px solid #e8eef6;
            font-weight: 700;
            vertical-align: middle;
        }

        .rank-table tr:hover td {
            background: #f7fbff;
        }

        .rank-num {
            display: inline-flex;
            width: 20px;
            height: 20px;
            border-radius: 5px;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 11px;
            font-weight: 950;
        }

        .badge {
            display: inline-flex;
            min-width: 58px;
            height: 24px;
            padding: 0 10px;
            align-items: center;
            justify-content: center;
            border-radius: 7px;
            font-weight: 950;
            font-size: 12px;
        }

        .badge.baixo { background: var(--green); color: white; }
        .badge.medio { background: var(--yellow); color: #4a3800; }
        .badge.alto { background: var(--orange); color: white; }
        .badge.critico { background: var(--red); color: white; }

        .legend-box {
            background: rgba(255, 255, 255, .96);
            border: 1px solid #dfe9f5;
            border-radius: 12px;
            padding: 12px 14px;
            display: inline-block;
            font-size: 12px;
            color: var(--text);
            margin-top: -2px;
            box-shadow: 0 6px 16px rgba(17, 42, 70, 0.06);
        }

        .legend-row { display: flex; align-items: center; gap: 8px; margin: 5px 0; font-weight: 700; }
        .dot { width: 13px; height: 13px; border-radius: 50%; display: inline-block; }

        .updates-row {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            padding: 13px 0;
            border-bottom: 1px solid #e6edf6;
            color: var(--text);
        }

        .updates-row:last-child { border-bottom: none; }
        .updates-icon {
            width: 36px;
            height: 36px;
            border-radius: 12px;
            background: #eef6ff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 19px;
            flex: 0 0 auto;
        }

        .muted { color: var(--muted); font-size: 12px; font-weight: 650; }

        .info-list-row {
            display: grid;
            grid-template-columns: 30px 1fr 1fr;
            align-items: center;
            gap: 8px;
            padding: 10px 0;
            border-bottom: 1px solid #edf2f7;
            color: var(--text);
            font-size: 13px;
            font-weight: 750;
        }

        .info-list-row span:nth-child(2) { color: #53687f; }
        .risk-bar {
            height: 13px;
            width: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #27c76a 0 25%, #a9d545 25% 50%, #ff8a1d 50% 75%, #f1283c 75% 100%);
            position: relative;
            margin: 22px 0 6px 0;
            overflow: visible;
        }
        .risk-marker {
            position: absolute;
            top: 18px;
            left: 37%;
            width: 0; height: 0;
            border-left: 8px solid transparent;
            border-right: 8px solid transparent;
            border-bottom: 10px solid #0b1f34;
        }
        .risk-labels {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            font-size: 12px;
            color: #435b74;
            text-align: center;
            font-weight: 750;
            margin-top: 16px;
        }

        .chips { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
        .chip {
            border: 1px solid #bfd4ec;
            background: #f8fbff;
            color: #0b68d8;
            border-radius: 999px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 850;
        }

        .mini-card {
            background: #fff;
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 14px;
        }

        .callout-yellow {
            background: #fff9e5;
            border: 1px solid #f4ce3a;
            border-radius: 12px;
            padding: 14px;
            color: #4d3c04;
            font-weight: 700;
        }

        .footer-note {
            color: #6e8093;
            font-size: 11px;
            margin-top: 10px;
            font-weight: 650;
        }

        @media (max-width: 1200px) {
            .topbar { align-items: flex-start; flex-direction: column; }
            .topbar-title { white-space: normal; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

### DADOS E INTEGRAÇÃO COM A API
RISK_COLORS = {
    "Baixo": "#20c665",
    "Médio": "#ffd448",
    "Alto": "#ff8618",
    "Crítico": "#f1283c",
}

RISK_ORDER = ["Baixo", "Médio", "Alto", "Crítico"]

FALLBACK_API_PAYLOAD = [
    {
        "bairro_id": "2611606001",
        "bairro_nome": "Boa Viagem",
        "semana_epidemiologica": "2025-01",
        "populacao_total": 122922,
        "dados_climaticos": {"chuva_lag4_mm": 45.2, "temp_max_lag4_c": 31.5},
        "previsao_modelo": {
            "casos_previstos": 14,
            "casos_reais_historico": 12,
            "taxa_incidencia_100k": 11.3,
            "nivel_alerta": "Medio",
        },
    },
    {
        "bairro_id": "2611606002",
        "bairro_nome": "Afogados",
        "semana_epidemiologica": "2025-01",
        "populacao_total": 35400,
        "dados_climaticos": {"chuva_lag4_mm": 48.1, "temp_max_lag4_c": 31.2},
        "previsao_modelo": {
            "casos_previstos": 42,
            "casos_reais_historico": 38,
            "taxa_incidencia_100k": 118.6,
            "nivel_alerta": "Critico",
        },
    },
]

# O contrato atual não fornece localização. Este catálogo mantém o mapa funcional
# até que a API passe a retornar lat, lon, cidade e UF.
LOCATION_FALLBACK = {
    "2611606001": {"UF": "PE", "Cidade": "Recife", "lat": -8.1260, "lon": -34.9000},
    "2611606002": {"UF": "PE", "Cidade": "Recife", "lat": -8.0785, "lon": -34.9086},
}


def normalize_alert(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char)).strip().lower()
    return {
        "baixo": "Baixo",
        "medio": "Médio",
        "alto": "Alto",
        "critico": "Crítico",
    }.get(text, "Baixo")


def normalize_api_payload(payload):
    if isinstance(payload, dict):
        payload = payload.get("data", payload.get("resultados", payload.get("bairros", [])))
    if not isinstance(payload, list):
        raise ValueError("A resposta da API deve ser uma lista de bairros.")

    rows = []
    for item in payload:
        climate = item.get("dados_climaticos") or {}
        forecast = item.get("previsao_modelo") or {}
        bairro_id = str(item.get("bairro_id", "")).strip()
        location = LOCATION_FALLBACK.get(bairro_id, {})
        rows.append(
            {
                "bairro_id": bairro_id,
                "Bairro": item.get("bairro_nome") or "Bairro não informado",
                "UF": item.get("uf") or location.get("UF", "N/D"),
                "Cidade": item.get("cidade") or location.get("Cidade", "N/D"),
                "Semana": item.get("semana_epidemiologica") or "N/D",
                "População": item.get("populacao_total") or 0,
                "Chuva lag4": climate.get("chuva_lag4_mm") or 0,
                "Temp. max lag4": climate.get("temp_max_lag4_c") or 0,
                "Casos previstos": forecast.get("casos_previstos") or 0,
                "Casos históricos": forecast.get("casos_reais_historico") or 0,
                "Incidência por 100 mil": forecast.get("taxa_incidencia_100k") or 0,
                "Nível de alerta": normalize_alert(forecast.get("nivel_alerta")),
                "lat": item.get("lat", location.get("lat")),
                "lon": item.get("lon", location.get("lon")),
            }
        )

    if not rows:
        raise ValueError("A API retornou uma lista vazia.")

    df = pd.DataFrame(rows)
    numeric_columns = [
        "População", "Chuva lag4", "Temp. max lag4", "Casos previstos",
        "Casos históricos", "Incidência por 100 mil", "lat", "lon",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df.sort_values(
        ["Casos previstos", "Incidência por 100 mil"], ascending=False
    ).reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_api_payload(api_url):
    response = requests.get(
        api_url,
        timeout=15,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def load_bairros(api_url, force_refresh=False):
    if force_refresh:
        fetch_api_payload.clear()

    if not api_url:
        return normalize_api_payload(FALLBACK_API_PAYLOAD), "demonstração", None

    try:
        payload = fetch_api_payload(api_url)
        return normalize_api_payload(payload), "API", None
    except (requests.RequestException, ValueError, TypeError) as exc:
        if "bairros_snapshot" in st.session_state:
            return st.session_state.bairros_snapshot.copy(), "último dado válido", str(exc)
        return normalize_api_payload(FALLBACK_API_PAYLOAD), "demonstração", str(exc)

serie_casos = pd.DataFrame(
    {
        "Semana": ["SE 46", "SE 47", "SE 48", "SE 49", "SE 50", "SE 51", "SE 52", "SE 01"],
        "Casos previstos": [820, 910, 1020, 1110, 1230, 1150, 1210, 1382],
    }
)

serie_clima = pd.DataFrame(
    {
        "Semana": ["SE 46", "SE 47", "SE 48", "SE 49", "SE 50", "SE 51", "SE 52", "SE 01"],
        "Chuva (mm)": [45, 62, 80, 55, 70, 65, 50, 40],
        "Temperatura (°C)": [28.1, 28.6, 29.8, 30.1, 30.5, 29.7, 28.9, 28.2],
    }
)

serie_bairro = pd.DataFrame(
    {
        "Semana": ["SE 50", "SE 51", "SE 52", "SE 01", "SE 02", "SE 03", "SE 04", "SE 05"],
        "Casos previstos": [10, 11, 13, 14, 16, 18, 20, 22],
        "Casos históricos": [8, 9, 11, 12, 10, 9, 11, 13],
    }
)

hospitais = pd.DataFrame(
    [
        ["Hospital das Clínicas", "SP", 93.2, 107.4, 1842, "Crítico", -23.5570, -46.6680],
        ["Hospital Municipal Souza Aguiar", "RJ", 91.1, 104.6, 1726, "Crítico", -22.9068, -43.1729],
        ["Santa Casa de Belo Horizonte", "MG", 88.7, 101.2, 1512, "Alto", -19.9191, -43.9386],
        ["Hospital Geral de Fortaleza", "CE", 86.5, 98.3, 1298, "Alto", -3.7450, -38.5230],
        ["Hospital da Restauração", "PE", 82.4, 94.1, 1074, "Alto", -8.0500, -34.9000],
        ["Hospital São Lucas da PUCRS", "RS", 78.6, 90.5, 934, "Médio", -30.0600, -51.1750],
        ["Hospital Universitário da UFPR", "PR", 76.1, 87.3, 812, "Médio", -25.4284, -49.2733],
        ["Hospital de Base de Brasília", "DF", 74.2, 84.7, 732, "Médio", -15.7939, -47.8828],
    ],
    columns=["Hospital / Região", "UF", "Ocupação atual", "Ocupação prevista", "Pacientes estimados", "Nível de risco", "lat", "lon"],
)

ocupacao_semanal = pd.DataFrame(
    {
        "Semana": ["SE 46", "SE 47", "SE 48", "SE 49", "SE 50", "SE 51", "SE 52"],
        "Ocupação atual": [71, 74, 76, 78, 81, 83, 85],
        "Ocupação prevista": [76, 80, 84, 87, 90, 92, 94],
    }
)

demanda_regiao = pd.DataFrame(
    {
        "Região": ["Sudeste", "Nordeste", "Sul", "Centro-Oeste", "Norte"],
        "Pacientes estimados": [9842, 5124, 2648, 812, 306],
    }
)

### FUNÇÕES VISUAIS
def br_int(value):
    return f"{int(value):,}".replace(",", ".")


def br_float(value, decimals=1):
    return f"{float(value):.{decimals}f}".replace(".", ",")


def risk_class(value):
    return value.lower().replace("í", "i").replace("é", "e")


def badge(value):
    return f'<span class="badge {risk_class(value)}">{value}</span>'


def rank_num(i, level):
    color = RISK_COLORS.get(level, "#9aacc0")
    return f'<span class="rank-num" style="background:{color}">{i}</span>'


def sidebar_logo():
    st.sidebar.markdown(
        """
        <div style="text-align:center; padding: 12px 0 26px 0;">
            <div style="width:92px;height:92px;border-radius:30px;margin:0 auto 8px auto;
                        border:3px solid #1683ff; display:flex; align-items:center; justify-content:center;
                        background:rgba(22,131,255,.10); box-shadow:0 12px 32px rgba(22,131,255,.20);">
                <span style="font-size:44px;">🦟</span>
            </div>
            <div style="font-size:34px; font-weight:950; letter-spacing:.5px;">SIPD</div>
            <div style="font-size:14px; font-weight:650; line-height:1.35; opacity:.95;">
                Sistema Inteligente de<br>Predição de Dengue
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _select_filter(label, options, key, all_label="Todas"):
    values = [all_label] + sorted({str(value) for value in options if pd.notna(value)})
    if st.session_state.get(key) not in values:
        st.session_state[key] = all_label
    return st.selectbox(label, values, key=key)


def topbar(data, kind="alerta"):
    """Renderiza filtros reais e devolve somente as linhas selecionadas."""
    filtered = data.copy()
    st.markdown(
        '<div class="topbar-title" style="margin-bottom:8px;">'
        'Sistema Inteligente de Predição de Dengue</div>',
        unsafe_allow_html=True,
    )

    if kind == "risco":
        current_hospital_week = (
            bairros["Semana"].dropna().astype(str).max()
            if not bairros.empty
            else "N/D"
        )
        filtered["Semana"] = current_hospital_week
        region_by_uf = {
            "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte",
            "RO": "Norte", "RR": "Norte", "TO": "Norte",
            "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste",
            "MA": "Nordeste", "PB": "Nordeste", "PE": "Nordeste",
            "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
            "DF": "Centro-Oeste", "GO": "Centro-Oeste",
            "MT": "Centro-Oeste", "MS": "Centro-Oeste",
            "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
            "PR": "Sul", "RS": "Sul", "SC": "Sul",
        }
        filtered["Região"] = filtered["UF"].map(region_by_uf).fillna("N/D")
        c_week, c_region, c_uf, c_level = st.columns([1.35, 0.75, 0.65, 0.9])
        with c_week:
            week = _select_filter(
                "Semana epidemiológica",
                filtered["Semana"],
                "hospital_filter_week",
            )
        if week != "Todas":
            filtered = filtered[filtered["Semana"].astype(str) == week]
        with c_region:
            region = _select_filter(
                "Região", filtered["Região"], "hospital_filter_region"
            )
        if region != "Todas":
            filtered = filtered[filtered["Região"] == region]
        with c_uf:
            uf = _select_filter("UF", filtered["UF"], "hospital_filter_uf")
        if uf != "Todas":
            filtered = filtered[filtered["UF"] == uf]
        with c_level:
            level = _select_filter(
                "Nível de risco",
                filtered["Nível de risco"],
                "hospital_filter_level",
                all_label="Todos",
            )
        if level != "Todos":
            filtered = filtered[filtered["Nível de risco"] == level]
    else:
        c_week, c_uf, c_city, c_level = st.columns([1.35, 0.65, 0.8, 0.9])
        with c_week:
            week = _select_filter(
                "Semana epidemiológica", filtered["Semana"], f"{kind}_filter_week"
            )
        if week != "Todas":
            filtered = filtered[filtered["Semana"].astype(str) == week]
        with c_uf:
            uf = _select_filter("UF", filtered["UF"], f"{kind}_filter_uf")
        if uf != "Todas":
            filtered = filtered[filtered["UF"] == uf]
        with c_city:
            city = _select_filter(
                "Cidade", filtered["Cidade"], f"{kind}_filter_city"
            )
        if city != "Todas":
            filtered = filtered[filtered["Cidade"] == city]
        with c_level:
            level = _select_filter(
                "Nível de alerta",
                filtered["Nível de alerta"],
                f"{kind}_filter_level",
                all_label="Todos",
            )
        if level != "Todos":
            filtered = filtered[filtered["Nível de alerta"] == level]

    st.caption(f"{len(filtered)} registro(s) na seleção atual")
    return filtered.reset_index(drop=True)


def page_title(title, breadcrumb=None, action=None):
    crumb_html = f'<span class="breadcrumb">{breadcrumb}</span>' if breadcrumb else ""
    action_html = f'<div class="btn-outline">{action}</div>' if action else ""
    st.markdown(
        f"""
        <div class="page-title-row">
            <div><span class="page-title">{title}</span>{crumb_html}</div>
            <div>{action_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi(title, value, sub, icon="📊", accent="#1683ff", trend=None, trend_class="trend-up"):
    trend_html = f'<span class="{trend_class}">{trend}</span>' if trend else ""
    html = f"""
        <div class="kpi-card" style="--accent:{accent};">
            <div class="kpi-icon">{icon}</div>
            <div>
                <div class="kpi-title">{title}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-sub">{trend_html} {sub}</div>
            </div>
        </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def section(title, info=True, height=None, key=None, css_class=""):
    """Cria um card Streamlit com altura previsível.

    Quando ``height`` não for informado, o parâmetro não é enviado ao
    ``st.container``. Isso evita o erro ``StreamlitInvalidHeightError`` em
    versões que não aceitam ``None`` explicitamente.
    """
    icon = " ⓘ" if info else ""
    marker_classes = "sipd-section-marker"
    if css_class:
        marker_classes += f" {css_class}"

    @contextmanager
    def _section_context():
        container_args = {"border": True}

        if height is not None:
            container_args["height"] = height

        if key is not None:
            container_args["key"] = key

        with st.container(**container_args):
            st.markdown(
                f'<span class="{marker_classes}"></span>'
                f'<div class="panel-title">{title}{icon}</div>',
                unsafe_allow_html=True,
            )
            yield

    return _section_context()


def legend_box():
    st.markdown(
        """
        <div class="legend-box">
            <b>Nível de criticidade</b>
            <div class="legend-row"><span class="dot" style="background:#20c665"></span>Baixo</div>
            <div class="legend-row"><span class="dot" style="background:#ffd448"></span>Médio</div>
            <div class="legend-row"><span class="dot" style="background:#ff8618"></span>Alto</div>
            <div class="legend-row"><span class="dot" style="background:#f1283c"></span>Crítico</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def apply_chart_layout(fig, height=335, showlegend=True):
    fig.update_layout(
        height=height,
        template="plotly_white",
        margin=dict(l=12, r=12, t=8, b=20),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="Inter, Segoe UI, Arial", color="#092b4c", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5) if showlegend else None,
    )
    fig.update_xaxes(showgrid=False, linecolor="#dfe9f5")
    fig.update_yaxes(gridcolor="#e8eef6", linecolor="#dfe9f5")
    return fig


def brazil_map(df, level_col, hover_name, size_col, title="", show_legend=True):
    """Mapa retangular focado no Brasil, com calor, marcadores e legenda sobreposta."""
    fig = go.Figure()

    risk_weight = {"Baixo": 1, "Médio": 2, "Alto": 3, "Crítico": 4}
    map_df = df.copy()
    max_size = max(float(map_df[size_col].max()), 1.0)
    map_df["heat_weight"] = (
        map_df[level_col].map(risk_weight).fillna(1)
        * map_df[size_col].astype(float)
    )

    fig.add_trace(
        go.Densitymapbox(
            lat=map_df["lat"],
            lon=map_df["lon"],
            z=map_df["heat_weight"],
            radius=48,
            opacity=0.50,
            colorscale=[
                [0.00, "rgba(32,198,101,0.06)"],
                [0.22, "#20c665"],
                [0.48, "#ffd448"],
                [0.72, "#ff8618"],
                [1.00, "#f1283c"],
            ],
            showscale=False,
            hoverinfo="skip",
        )
    )

    for level in RISK_ORDER:
        temp = map_df[map_df[level_col] == level]
        if temp.empty:
            continue

        sizes = (temp[size_col].astype(float) / max_size) * 25 + 11
        customdata = temp[[size_col, level_col]].to_numpy()

        fig.add_trace(
            go.Scattermapbox(
                lat=temp["lat"],
                lon=temp["lon"],
                mode="markers",
                marker=dict(
                    size=sizes,
                    color=RISK_COLORS[level],
                    opacity=0.88,
                ),
                name=level,
                text=temp[hover_name],
                customdata=customdata,
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Valor: %{customdata[0]}<br>"
                    "Nível: %{customdata[1]}"
                    "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=title,
        height=405,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        showlegend=False,
        mapbox=dict(
            style="carto-positron",
            center=dict(lat=-14.3, lon=-52.0),
            zoom=3.05,
        ),
        font=dict(family="Inter, Segoe UI, Arial", color="#092b4c", size=12),
        hoverlabel=dict(bgcolor="#092b4c", font_color="white"),
        uirevision="sipd-brazil-map",
    )

    if show_legend:
        # Caixa branca sobreposta no canto inferior esquerdo do mapa.
        fig.add_shape(
            type="rect",
            xref="paper",
            yref="paper",
            x0=0.018,
            x1=0.215,
            y0=0.035,
            y1=0.350,
            fillcolor="rgba(255,255,255,0.96)",
            line=dict(color="#dfe9f5", width=1),
            layer="above",
        )
        fig.add_annotation(
            xref="paper", yref="paper", x=0.040, y=0.318,
            text="<b>Nível de criticidade</b>",
            showarrow=False, xanchor="left", yanchor="middle",
            font=dict(size=12, color="#092b4c"),
        )

        legend_items = [
            ("Baixo", "#20c665", 0.257),
            ("Médio", "#ffd448", 0.198),
            ("Alto", "#ff8618", 0.139),
            ("Crítico", "#f1283c", 0.080),
        ]
        for label, color, y in legend_items:
            fig.add_shape(
                type="circle",
                xref="paper", yref="paper",
                x0=0.040, x1=0.057,
                y0=y - 0.012, y1=y + 0.012,
                fillcolor=color,
                line=dict(color=color, width=1),
                layer="above",
            )
            fig.add_annotation(
                xref="paper", yref="paper", x=0.067, y=y,
                text=f"<b>{label}</b>",
                showarrow=False, xanchor="left", yanchor="middle",
                font=dict(size=11, color="#092b4c"),
            )

    return fig


def small_location_map(row):
    """Mapa retangular de localização do bairro selecionado."""
    fig = go.Figure()

    fig.add_trace(
        go.Scattermapbox(
            lat=[row["lat"]],
            lon=[row["lon"]],
            mode="markers+text",
            marker=dict(
                size=24,
                color=RISK_COLORS[row["Nível de alerta"]],
                opacity=0.95,
            ),
            text=[row["Bairro"]],
            textposition="bottom center",
            hovertemplate=(
                f"<b>{row['Bairro']}</b><br>"
                f"{row['Cidade']} - {row['UF']}"
                "<extra></extra>"
            ),
            showlegend=False,
        )
    )

    fig.update_layout(
        height=295,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        mapbox=dict(
            style="carto-positron",
            center=dict(lat=float(row["lat"]), lon=float(row["lon"])),
            zoom=11,
        ),
        hoverlabel=dict(bgcolor="#092b4c", font_color="white"),
    )

    return fig


def ranking_table_dashboard(data=None):
    source = bairros if data is None else data
    ranking = source.sort_values(
        ["Incidência por 100 mil", "Casos previstos"], ascending=False
    ).head(8).copy().reset_index(drop=True)
    rows = []

    for idx, row in ranking.iterrows():
        level = row["Nível de alerta"]
        rows.append(
            "<tr>"
            f"<td>{rank_num(idx + 1, level)}</td>"
            f"<td>{row['Bairro']}</td>"
            f"<td>{row['UF']} / {row['Cidade']}</td>"
            f"<td>{row['Casos previstos']}</td>"
            f"<td>{br_float(row['Incidência por 100 mil'])}</td>"
            f"<td>{badge(level)}</td>"
            "</tr>"
        )

    return (
        '<div style="overflow-x:auto;">'
        '<table class="rank-table">'
        '<thead><tr>'
        '<th>#</th><th>Bairro</th><th>UF / Cidade</th>'
        '<th>Casos previstos</th><th>Incidência<br>por 100 mil</th><th>Nível de alerta</th>'
        '</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody>"
        '</table></div>'
        '<div class="footer-note">'
        'Incidência calculada com base na população estimada do bairro (IBGE, 2024).'
        '</div>'
    )


def ranking_table_hospitals(data=None):
    source = hospitais if data is None else data
    temp = source.copy().sort_values("Ocupação prevista", ascending=False).reset_index(drop=True)
    rows = []

    for idx, row in temp.iterrows():
        level = row["Nível de risco"]
        rows.append(
            "<tr>"
            f"<td>{rank_num(idx + 1, level)}</td>"
            f"<td>{row['Hospital / Região']}</td>"
            f"<td>{row['UF']}</td>"
            f"<td>{br_float(row['Ocupação atual'])}%</td>"
            f"<td>{br_float(row['Ocupação prevista'])}%</td>"
            f"<td>{br_int(row['Pacientes estimados'])}</td>"
            f"<td>{badge(level)}</td>"
            "</tr>"
        )

    return (
        '<div style="overflow-x:auto;">'
        '<table class="rank-table">'
        '<thead><tr>'
        '<th>#</th><th>Hospital / Região</th><th>UF</th>'
        '<th>Ocupação atual</th><th>Ocupação prevista</th>'
        '<th>Pacientes estimados</th><th>Nível de risco</th>'
        '</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody>"
        '</table></div>'
        '<div class="footer-note">'
        'Indicadores calculados com base na taxa de ocupação de leitos e demanda projetada. (IBGE, 2024)'
        '</div>'
    )


def pressure_diagram_html():
    """Retorna o diagrama de fatores de pressão em HTML isolado.

    O conteúdo é renderizado por ``components.html`` dentro de um iframe.
    Dessa forma, o Streamlit não interpreta as tags indentadas como Markdown
    ou bloco de código, e o desenho ocupa toda a largura disponível.
    """
    return r"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<style>
    * {
        box-sizing: border-box;
    }

    html, body {
        width: 100%;
        height: 100%;
        margin: 0;
        padding: 0;
        overflow: hidden;
        background: transparent;
        font-family: Inter, "Segoe UI", Arial, sans-serif;
        color: #163a5b;
    }

    .pressure-root {
        width: 100%;
        height: 304px;
        display: flex;
        flex-direction: column;
    }

    .pressure-layout {
        display: grid;
        grid-template-columns: minmax(135px, 1fr) 125px minmax(175px, 1.2fr) 82px;
        column-gap: 8px;
        align-items: start;
        flex: 1 1 auto;
        min-height: 0;
    }

    .column-heading {
        height: 25px;
        display: flex;
        align-items: flex-start;
        color: #31506e;
        font-size: 11px;
        font-weight: 800;
        white-space: nowrap;
    }

    .rows {
        display: grid;
        grid-template-rows: repeat(5, 43px);
        row-gap: 1px;
    }

    .source-item,
    .hospital-item {
        display: flex;
        align-items: flex-start;
        gap: 7px;
        min-width: 0;
        height: 43px;
    }

    .source-icon {
        width: 20px;
        height: 20px;
        min-width: 20px;
        margin-top: 1px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-size: 10px;
        line-height: 1;
        font-weight: 900;
    }

    .source-icon.critical {
        background: #f1283c;
    }

    .source-icon.high {
        background: #ff8618;
    }

    .hospital-icon {
        width: 20px;
        min-width: 20px;
        margin-top: 1px;
        color: #f1283c;
        font-size: 18px;
        line-height: 1;
        font-weight: 900;
        text-align: center;
    }

    .hospital-icon.high {
        color: #ff8618;
    }

    .item-copy {
        min-width: 0;
        line-height: 1.12;
    }

    .item-name {
        display: block;
        color: #193b5c;
        font-size: 10px;
        font-weight: 750;
        margin-bottom: 2px;
        overflow-wrap: anywhere;
    }

    .item-meta {
        display: block;
        color: #6f8296;
        font-size: 8.5px;
        font-weight: 700;
    }

    .item-meta.critical {
        color: #f1283c;
    }

    .item-meta.high {
        color: #ff8618;
    }

    .connection-column {
        height: 240px;
        padding-top: 24px;
    }

    .connection-svg {
        display: block;
        width: 100%;
        height: 215px;
        overflow: visible;
    }

    .impact-card {
        height: 240px;
        border: 1px solid #dfe9f5;
        border-radius: 10px;
        background: #ffffff;
        box-shadow: 0 3px 12px rgba(17, 42, 70, 0.05);
        padding: 8px 7px;
    }

    .impact-heading {
        height: 25px;
        color: #536c84;
        font-size: 8.5px;
        font-weight: 850;
        text-align: center;
        white-space: nowrap;
    }

    .impact-rows {
        display: grid;
        grid-template-rows: repeat(5, 41px);
        align-items: center;
    }

    .impact-value {
        text-align: center;
        font-size: 15px;
        font-weight: 900;
    }

    .impact-value.critical {
        color: #f1283c;
    }

    .impact-value.high {
        color: #ff8618;
    }

    .impact-value.medium {
        color: #e0a900;
    }

    .pressure-footer {
        flex: 0 0 auto;
        margin-top: 5px;
        color: #75879a;
        font-size: 8.5px;
        font-weight: 650;
        line-height: 1.2;
    }

    @media (max-width: 620px) {
        .pressure-layout {
            grid-template-columns: minmax(120px, 1fr) 92px minmax(150px, 1.05fr) 70px;
            column-gap: 5px;
        }

        .column-heading {
            font-size: 10px;
        }

        .item-name {
            font-size: 9px;
        }

        .connection-column {
            padding-top: 22px;
        }
    }
</style>
</head>
<body>
<div class="pressure-root">
    <div class="pressure-layout">
        <div>
            <div class="column-heading">Bairros com maior risco</div>
            <div class="rows">
                <div class="source-item">
                    <div class="source-icon critical">⌂</div>
                    <div class="item-copy">
                        <span class="item-name">Complexo do Alemão (RJ)</span>
                        <span class="item-meta critical">Risco: Crítico</span>
                    </div>
                </div>
                <div class="source-item">
                    <div class="source-icon critical">⌂</div>
                    <div class="item-copy">
                        <span class="item-name">Pavuna (RJ)</span>
                        <span class="item-meta critical">Risco: Crítico</span>
                    </div>
                </div>
                <div class="source-item">
                    <div class="source-icon high">⌂</div>
                    <div class="item-copy">
                        <span class="item-name">Cidade Tiradentes (SP)</span>
                        <span class="item-meta high">Risco: Alto</span>
                    </div>
                </div>
                <div class="source-item">
                    <div class="source-icon high">⌂</div>
                    <div class="item-copy">
                        <span class="item-name">Jardim Ângela (SP)</span>
                        <span class="item-meta high">Risco: Alto</span>
                    </div>
                </div>
                <div class="source-item">
                    <div class="source-icon high">⌂</div>
                    <div class="item-copy">
                        <span class="item-name">Coelho Neto (RJ)</span>
                        <span class="item-meta high">Risco: Alto</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="connection-column" aria-hidden="true">
            <svg class="connection-svg" viewBox="0 0 125 215" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
                <!-- Linhas dos bairros críticos -->
                <path d="M1 10 C38 10, 77 10, 123 10" fill="none" stroke="#f1283c" stroke-width="1.8"/>
                <path d="M1 10 C38 10, 77 52, 123 52" fill="none" stroke="#f1283c" stroke-width="1.8"/>
                <path d="M1 52 C38 52, 77 10, 123 10" fill="none" stroke="#f1283c" stroke-width="1.8"/>
                <path d="M1 52 C38 52, 77 52, 123 52" fill="none" stroke="#f1283c" stroke-width="1.8"/>

                <!-- Linhas dos bairros em nível alto -->
                <path d="M1 94 C38 94, 77 94, 123 94" fill="none" stroke="#ff8618" stroke-width="1.8"/>
                <path d="M1 94 C38 94, 77 136, 123 136" fill="none" stroke="#ff8618" stroke-width="1.8"/>
                <path d="M1 136 C38 136, 77 94, 123 94" fill="none" stroke="#ff8618" stroke-width="1.8"/>
                <path d="M1 136 C38 136, 77 136, 123 136" fill="none" stroke="#ff8618" stroke-width="1.8"/>
                <path d="M1 178 C38 178, 77 52, 123 52" fill="none" stroke="#e0a900" stroke-width="1.8"/>
                <path d="M1 178 C38 178, 77 178, 123 178" fill="none" stroke="#e0a900" stroke-width="1.8"/>

                <circle cx="123" cy="10" r="2.6" fill="#ffffff" stroke="#f1283c" stroke-width="1.8"/>
                <circle cx="123" cy="52" r="2.6" fill="#ffffff" stroke="#f1283c" stroke-width="1.8"/>
                <circle cx="123" cy="94" r="2.6" fill="#ffffff" stroke="#ff8618" stroke-width="1.8"/>
                <circle cx="123" cy="136" r="2.6" fill="#ffffff" stroke="#ff8618" stroke-width="1.8"/>
                <circle cx="123" cy="178" r="2.6" fill="#ffffff" stroke="#e0a900" stroke-width="1.8"/>
            </svg>
        </div>

        <div>
            <div class="column-heading">Hospitais de referência</div>
            <div class="rows">
                <div class="hospital-item">
                    <div class="hospital-icon">▥</div>
                    <div class="item-copy">
                        <span class="item-name">Hospital Municipal Souza Aguiar</span>
                        <span class="item-meta critical">Impacto: Muito alto</span>
                    </div>
                </div>
                <div class="hospital-item">
                    <div class="hospital-icon">▥</div>
                    <div class="item-copy">
                        <span class="item-name">Hospital Federal de Bonsucesso</span>
                        <span class="item-meta critical">Impacto: Muito alto</span>
                    </div>
                </div>
                <div class="hospital-item">
                    <div class="hospital-icon high">▥</div>
                    <div class="item-copy">
                        <span class="item-name">Hospital das Clínicas</span>
                        <span class="item-meta high">Impacto: Alto</span>
                    </div>
                </div>
                <div class="hospital-item">
                    <div class="hospital-icon high">▥</div>
                    <div class="item-copy">
                        <span class="item-name">Hospital Geral de Itaquera</span>
                        <span class="item-meta high">Impacto: Alto</span>
                    </div>
                </div>
                <div class="hospital-item">
                    <div class="hospital-icon high">▥</div>
                    <div class="item-copy">
                        <span class="item-name">UPA Coelho Neto</span>
                        <span class="item-meta">Impacto: Médio</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="impact-card">
            <div class="impact-heading">Impacto estimado</div>
            <div class="impact-rows">
                <div class="impact-value critical">+38%</div>
                <div class="impact-value critical">+34%</div>
                <div class="impact-value high">+29%</div>
                <div class="impact-value high">+24%</div>
                <div class="impact-value medium">+18%</div>
            </div>
        </div>
    </div>

    <div class="pressure-footer">
        Correlação baseada em incidência prevista de dengue e fluxo histórico de atendimentos. (SIPD, 2024)
    </div>
</div>
</body>
</html>
"""


def details_table_bairro(row):
    return (
        '<div style="overflow-x:auto;">'
        '<table class="rank-table">'
        '<thead><tr>'
        '<th>bairro_id</th><th>Nome do bairro</th><th>Semana<br>epidemiológica</th>'
        '<th>População total</th><th>Chuva acumulada<br>(lag4)</th>'
        '<th>Temperatura máx.<br>(lag4)</th><th>Casos previstos<br>(SE atual)</th>'
        '<th>Casos históricos<br>(SE atual)</th><th>Incidência por<br>100 mil</th>'
        '<th>Nível de alerta</th>'
        '</tr></thead><tbody><tr>'
        f"<td>{row['bairro_id']}</td>"
        f"<td>{row['Bairro']}</td>"
        f"<td>{row['Semana']}</td>"
        f"<td>{br_int(row['População'])}</td>"
        f"<td>{br_float(row['Chuva lag4'])} mm</td>"
        f"<td>{br_float(row['Temp. max lag4'])} °C</td>"
        f"<td>{row['Casos previstos']}</td>"
        f"<td>{row['Casos históricos']}</td>"
        f"<td>{br_float(row['Incidência por 100 mil'])}</td>"
        f"<td>{badge(row['Nível de alerta'])}</td>"
        '</tr></tbody></table></div>'
    )

sidebar_logo()

default_api_url = os.getenv("SIPD_API_URL", "")
if "api_url" not in st.session_state:
    st.session_state.api_url = default_api_url

with st.sidebar.expander("Fonte de dados", expanded=False):
    api_url_input = st.text_input(
        "URL da API",
        value=st.session_state.api_url,
        placeholder="http://localhost:8000/previsoes",
        help="Deixe vazio para usar os dados de demonstração.",
    )
    force_refresh = st.button("Atualizar dados", use_container_width=True)

if api_url_input != st.session_state.api_url:
    st.session_state.api_url = api_url_input.strip()
    force_refresh = True

bairros, data_source, api_error = load_bairros(
    st.session_state.api_url,
    force_refresh=force_refresh,
)
st.session_state.bairros_snapshot = bairros.copy()

if api_error:
    st.sidebar.warning(
        "Não foi possível consultar a API. Exibindo "
        f"{data_source}. Detalhe: {api_error}"
    )
else:
    st.sidebar.success(f"Dados carregados: {data_source}")

available_ids = bairros["bairro_id"].astype(str).tolist()
if st.session_state.get("selected_bairro_id") not in available_ids:
    st.session_state.selected_bairro_id = available_ids[0]

serie_casos = (
    bairros.groupby("Semana", as_index=False)["Casos previstos"]
    .sum()
    .sort_values("Semana")
)
serie_casos["Semana"] = serie_casos["Semana"].map(lambda value: f"SE {str(value).split('-')[-1]}")

serie_clima = (
    bairros.groupby("Semana", as_index=False)
    .agg({"Chuva lag4": "mean", "Temp. max lag4": "mean"})
    .sort_values("Semana")
    .rename(columns={"Chuva lag4": "Chuva (mm)", "Temp. max lag4": "Temperatura (°C)"})
)
serie_clima["Semana"] = serie_clima["Semana"].map(lambda value: f"SE {str(value).split('-')[-1]}")

menu = st.sidebar.radio(
    "Menu",
    ["▦  Dashboard", "▥  Bairros", "▣  Hospitais", "▤  Relatórios"],
    label_visibility="collapsed",
)
page = "Dashboard" if "Dashboard" in menu else "Bairros" if "Bairros" in menu else "Hospitais" if "Hospitais" in menu else "Relatórios"

st.sidebar.markdown("<br><br><br><br>", unsafe_allow_html=True)
st.sidebar.caption("Versão 1.0.0")
st.sidebar.caption("© 2026 SIPD")

### TELA 1
if page == "Dashboard":
    dashboard_bairros = topbar(bairros, "dashboard")

    total_bairros = len(dashboard_bairros)
    total_casos = int(dashboard_bairros["Casos previstos"].sum())
    total_criticos = int((dashboard_bairros["Nível de alerta"] == "Crítico").sum())
    incidencia_media = float(dashboard_bairros["Incidência por 100 mil"].mean())
    dashboard_serie_casos = (
        dashboard_bairros.groupby("Semana", as_index=False)["Casos previstos"].sum()
    )
    dashboard_serie_casos["Semana"] = dashboard_serie_casos["Semana"].map(
        lambda value: f"SE {str(value).split('-')[-1]}"
    )
    dashboard_serie_clima = (
        dashboard_bairros.groupby("Semana", as_index=False)
        .agg({"Chuva lag4": "mean", "Temp. max lag4": "mean"})
        .rename(columns={
            "Chuva lag4": "Chuva (mm)",
            "Temp. max lag4": "Temperatura (°C)",
        })
    )
    dashboard_serie_clima["Semana"] = dashboard_serie_clima["Semana"].map(
        lambda value: f"SE {str(value).split('-')[-1]}"
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        kpi("Bairros monitorados", br_int(total_bairros), f"Fonte: {data_source}", "🏢", "#1683ff")
    with k2:
        kpi("Casos previstos", br_int(total_casos), "na seleção atual", "📈", "#0b72ee")
    with k3:
        kpi("Alerta crítico", br_int(total_criticos), "bairros", "⚠️", "#f1283c")
    with k4:
        kpi("Taxa média de incidência", br_float(incidencia_media), "por 100 mil hab.", "〽️", "#12bfc9")
    with k5:
        kpi("Risco de superlotação", "68%", "vs semana anterior", "👥", "#8556e8", "↑ 6,4%", "trend-orange")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    col_map, col_rank = st.columns([1.25, 1.0], gap="large")

    with col_map:
        with section("Mapa de calor — Risco de dengue no Brasil", height=500, key="dashboard_map", css_class="map-section"):
            fig_map = brazil_map(dashboard_bairros, "Nível de alerta", "Bairro", "Casos previstos")
            st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})

    with col_rank:
        with section("Bairros com maior risco", height=500, key="dashboard_ranking", css_class="rank-section"):
            st.markdown(ranking_table_dashboard(dashboard_bairros), unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    col_line, col_clima, col_update = st.columns([1.05, 1.20, 0.80], gap="large")

    with col_line:
        with section("Evolução semanal dos casos previstos", height=370, key="dashboard_weekly", css_class="chart-section"):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dashboard_serie_casos["Semana"], y=dashboard_serie_casos["Casos previstos"], mode="lines+markers+text", text=dashboard_serie_casos["Casos previstos"], textposition="top center", line=dict(color="#1683ff", width=3), marker=dict(size=8)))
            fig = apply_chart_layout(fig, height=290, showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_clima:
        with section("Influência climática", height=370, key="dashboard_climate", css_class="chart-section"):
            fig = go.Figure()
            fig.add_trace(go.Bar(x=dashboard_serie_clima["Semana"], y=dashboard_serie_clima["Chuva (mm)"], name="Chuva (mm)", marker_color="#1683ff", text=dashboard_serie_clima["Chuva (mm)"], textposition="outside"))
            fig.add_trace(go.Scatter(x=dashboard_serie_clima["Semana"], y=dashboard_serie_clima["Temperatura (°C)"], name="Temperatura (°C)", mode="lines+markers+text", yaxis="y2", line=dict(color="#f1283c", width=2), text=[f"{br_float(v)}°C" for v in dashboard_serie_clima["Temperatura (°C)"]], textposition="top center"))
            fig.update_layout(
                yaxis=dict(title="mm", range=[0, 105]),
                yaxis2=dict(title="°C", overlaying="y", side="right", range=[20, 36]),
            )
            fig = apply_chart_layout(fig, height=290, showlegend=True)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_update:
        with section("Últimas atualizações do modelo", height=370, key="dashboard_updates", css_class="updates-section"):
            current_week = bairros["Semana"].dropna().astype(str).max()
            st.markdown(
                f"""
                <div class="updates-row"><div class="updates-icon" style="background:#e9fbef;color:#20c665;">✓</div><div><b>Modelo atualizado há 2 horas</b><br><span class="muted">05/01/2025 08:35</span></div></div>
                <div class="updates-row"><div class="updates-icon" style="background:#eaf3ff;color:#1683ff;">◎</div><div><b>Precisão estimada: 89%</b><br><span class="muted">Baseado nas últimas 4 semanas</span></div></div>
                <div class="updates-row"><div class="updates-icon" style="background:#f1ecff;color:#8556e8;">▦</div><div><b>Dados processados até: SE {current_week}</b><br><span class="muted">Fonte atual: {data_source}</span></div></div>
                <div style="color:#0b72ee;font-weight:900;margin-top:14px;">Ver histórico de atualizações ›</div>
                """,
                unsafe_allow_html=True,
            )

### TELA 2
elif page == "Bairros":
    detail_bairros = topbar(bairros, "bairro")
    filtered_ids = detail_bairros["bairro_id"].astype(str).tolist()
    if st.session_state.get("selected_bairro_id") not in filtered_ids:
        st.session_state.selected_bairro_id = filtered_ids[0]
    bairro_options = detail_bairros.set_index("bairro_id")["Bairro"].to_dict()
    selected_bairro_id = st.selectbox(
        "Selecione o bairro",
        options=list(bairro_options.keys()),
        format_func=lambda value: bairro_options[value],
        key="selected_bairro_id",
    )
    row = detail_bairros[
        detail_bairros["bairro_id"].astype(str) == str(selected_bairro_id)
    ].iloc[0]
    page_title(
        "Detalhe do Bairro",
        f"Dashboard  ›  Bairros  ›  {row['Bairro']}",
        "⬇ Exportar relatório",
    )
    serie_bairro = pd.DataFrame(
        {
            "Semana": [f"SE {str(row['Semana']).split('-')[-1]}"],
            "Casos previstos": [row["Casos previstos"]],
            "Casos históricos": [row["Casos históricos"]],
        }
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        kpi("População total", br_int(row["População"]), "habitantes", "👥", "#1683ff")
    with k2:
        kpi("Casos previstos", str(int(row["Casos previstos"])), f"para a SE {row['Semana']}", "📈", "#72aefb")
    with k3:
        kpi("Casos históricos", str(int(row["Casos históricos"])), f"na SE {row['Semana']}", "📋", "#8ee6df")
    with k4:
        kpi("Incidência por 100 mil", br_float(row["Incidência por 100 mil"]), "por 100 mil hab.", "〽️", "#d6bbff")
    with k5:
        kpi(
            "Nível de alerta",
            row["Nível de alerta"],
            "Classificação do modelo",
            "⚠️",
            RISK_COLORS[row["Nível de alerta"]],
        )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    left, center, right = st.columns([1.20, 1.10, 0.62], gap="large")

    with left:
        with section("Informações do bairro", height=440, key="bairro_info", css_class="bairro-main-section bairro-info-section"):
            st.markdown(
                f"""
                <div style="display:flex; gap:14px; align-items:center; margin-bottom:8px;">
                    <div class="kpi-icon" style="--accent:#1683ff; width:50px;height:50px;min-width:50px;font-size:23px;">🏢</div>
                    <div><div style="font-size:24px;font-weight:950;color:#092b4c;">{row['Bairro']}</div><div class="muted">bairro_id: {row['bairro_id']}</div></div>
                </div>
                <div class="info-list-row"><span>📍</span><span>Cidade</span><b>{row['Cidade']} - {row['UF']}</b></div>
                <div class="info-list-row"><span>🧭</span><span>Região de Saúde</span><b>I - Recife</b></div>
                <div class="info-list-row"><span>🗓️</span><span>Semana epidemiológica</span><b>{row['Semana']}</b></div>
                <div class="info-list-row"><span>👥</span><span>População total</span><b>{br_int(row['População'])} habitantes</b></div>
                <div class="info-list-row"><span>⌁</span><span>Densidade populacional</span><b>6.842 hab/km²</b></div>
                <div class="info-list-row"><span>▱</span><span>Área</span><b>18,0 km²</b></div>
                <div style="height:14px"></div>
                <b style="color:#092b4c;">Nível de criticidade</b>
                <div class="risk-bar"><div class="risk-marker"></div></div>
                <div class="risk-labels"><span>Baixo</span><span>Médio</span><span>Alto</span><span>Crítico</span></div>
                """,
                unsafe_allow_html=True,
            )

    with center:
        with section("Casos previstos x casos históricos", height=440, key="bairro_cases", css_class="bairro-main-section"):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=serie_bairro["Semana"], y=serie_bairro["Casos previstos"], name="Casos previstos", mode="lines+markers+text", text=serie_bairro["Casos previstos"], textposition="top center", line=dict(color="#1683ff", width=3)))
            fig.add_trace(go.Scatter(x=serie_bairro["Semana"], y=serie_bairro["Casos históricos"], name="Casos históricos", mode="lines+markers+text", text=serie_bairro["Casos históricos"], textposition="bottom center", line=dict(color="#16b6bd", width=3)))
            current_week = serie_bairro["Semana"].iloc[-1]
            fig.add_vrect(x0=current_week, x1=current_week, fillcolor="#dcecff", opacity=0.30, line_width=0)
            fig = apply_chart_layout(fig, height=315, showlegend=True)
            fig.update_yaxes(range=[0, 50], title="Casos")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with right:
        with section("Variáveis climáticas (lag4)", height=440, key="bairro_climate", css_class="bairro-main-section bairro-climate-section"):
            st.markdown(
                f"""
                <div style="display:flex; gap:14px; align-items:center; padding:18px 0 24px 0;">
                    <div class="updates-icon" style="background:#eaf3ff;color:#1683ff;font-size:22px;">🌧️</div>
                    <div><b>Chuva acumulada</b><div style="font-size:27px;font-weight:950;color:#092b4c;">{br_float(row['Chuva lag4'])} mm</div><span class="muted">Acumulado em 4 semanas</span></div>
                </div>
                <hr style="border:0;border-top:1px solid #e6edf6;">
                <div style="display:flex; gap:14px; align-items:center; padding:24px 0 12px 0;">
                    <div class="updates-icon" style="background:#ffe8e8;color:#f1283c;font-size:22px;">🌡️</div>
                    <div><b>Temperatura máxima</b><div style="font-size:27px;font-weight:950;color:#092b4c;">{br_float(row['Temp. max lag4'])} °C</div><span class="muted">Média das máximas em 4 semanas</span></div>
                </div>
                <div class="footer-note">Dados até a SE {row['Semana']}</div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    loc, tend, actions = st.columns([1.20, 1.00, 1.00], gap="large")
    with loc:
        with section("Localização", height=380, key="bairro_location", css_class="bairro-secondary-section"):
            if pd.notna(row["lat"]) and pd.notna(row["lon"]):
                fig = small_location_map(row)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("Localização indisponível. Inclua `lat` e `lon` na resposta da API.")

    with tend:
        with section("Tendência para as próximas semanas", height=380, key="bairro_trend", css_class="bairro-secondary-section"):
            st.markdown(
                """
                <div class="mini-card">
                    <b>📈 Previsão de casos</b><br><br>
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);text-align:center;gap:8px;">
                        <div><span class="muted">SE 02<br>(05/01)</span><br><b style="font-size:20px;">16</b></div>
                        <div><span class="muted">SE 03<br>(12/01)</span><br><b style="font-size:20px;">18</b></div>
                        <div><span class="muted">SE 04<br>(19/01)</span><br><b style="font-size:20px;">20</b></div>
                        <div><span class="muted">SE 05<br>(26/01)</span><br><b style="font-size:20px;">22</b></div>
                    </div>
                </div>
                <div style="height:10px"></div>
                <div class="callout-yellow">⚠️ <b>Interpretação</b><br><span class="muted">Risco moderado, manter vigilância. Tendência de aumento gradual nas próximas semanas.</span></div>
                """,
                unsafe_allow_html=True,
            )

    with actions:
        with section("Ações recomendadas", height=380, key="bairro_actions", css_class="bairro-secondary-section bairro-actions-section"):
            st.markdown(
                """
                <ul style="color:#092b4c;font-weight:720;line-height:1.72;margin-top:0;">
                    <li>Intensificar o monitoramento de casos e sintomas.</li>
                    <li>Realizar inspeções domiciliares e eliminação de criadouros.</li>
                    <li>Reforçar campanhas de mobilização da população.</li>
                    <li>Manter atenção especial nas próximas 3 semanas.</li>
                </ul>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    with section("Detalhes do bairro", info=False):
        st.markdown(details_table_bairro(row), unsafe_allow_html=True)

### TELA 3
elif page == "Hospitais":
    filtered_hospitais = topbar(hospitais, "risco")
    page_title("Risco de Superlotação Hospitalar")

    hospital_count = len(filtered_hospitais)
    critical_count = int((filtered_hospitais["Nível de risco"] == "Crítico").sum())
    occupancy_mean = float(filtered_hospitais["Ocupação prevista"].mean())
    patient_count = int(filtered_hospitais["Pacientes estimados"].sum())

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        kpi("Hospitais monitorados", br_int(hospital_count), "na seleção atual", "🏥", "#1683ff")
    with k2:
        kpi("Regiões em risco", "214", "vs semana anterior", "📍", "#8556e8", "↑ 8,1%", "trend-up")
    with k3:
        kpi("Risco crítico", br_int(critical_count), "hospitais", "⚠️", "#f1283c")
    with k4:
        kpi("Ocupação média prevista", f"{br_float(occupancy_mean)}%", "na seleção atual", "📈", "#12bfc9")
    with k5:
        kpi("Pacientes estimados", br_int(patient_count), "na seleção atual", "👥", "#ff8618")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    col_map, col_rank = st.columns([1.15, 1.18], gap="large")

    with col_map:
        with section("Mapa de pressão assistencial no Brasil", height=500, key="hospital_map", css_class="map-section"):
            fig = brazil_map(filtered_hospitais.rename(columns={"Nível de risco": "Nível de alerta", "Hospital / Região": "Bairro", "Pacientes estimados": "Casos previstos"}), "Nível de alerta", "Bairro", "Casos previstos")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_rank:
        with section("Hospitais/Regiões com maior risco de superlotação", height=500, key="hospital_ranking", css_class="rank-section"):
            st.markdown(
                ranking_table_hospitals(filtered_hospitais),
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    col_proj, col_demanda, col_pressao = st.columns([1.0, 0.75, 1.3], gap="large")

    with col_proj:
        with section("Projeção de ocupação por semana", height=410, key="hospital_projection", css_class="hospital-chart-section"):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ocupacao_semanal["Semana"], y=ocupacao_semanal["Ocupação atual"], mode="lines+markers+text", name="Ocupação atual", text=[f"{v}%" for v in ocupacao_semanal["Ocupação atual"]], textposition="bottom center", line=dict(color="#1683ff", width=3)))
            fig.add_trace(go.Scatter(x=ocupacao_semanal["Semana"], y=ocupacao_semanal["Ocupação prevista"], mode="lines+markers+text", name="Ocupação prevista", text=[f"{v}%" for v in ocupacao_semanal["Ocupação prevista"]], textposition="top center", line=dict(color="#f1283c", width=2, dash="dash")))
            fig = apply_chart_layout(fig, height=305, showlegend=True)
            fig.update_yaxes(range=[0, 125], title="% ocupação", ticksuffix="%")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_demanda:
        with section("Demanda esperada por região", height=410, key="hospital_demand", css_class="hospital-chart-section"):
            fig = px.bar(demanda_regiao, x="Pacientes estimados", y="Região", orientation="h", text="Pacientes estimados", color="Região", color_discrete_sequence=["#f1283c", "#ff8618", "#ffd448", "#20c665", "#12bfc9"])
            fig.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig = apply_chart_layout(fig, height=305, showlegend=False)
            fig.update_layout(yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_pressao:
        with section(
            "Fatores de pressão",
            height=410,
            key="hospital_pressure",
            css_class="hospital-chart-section pressure-section",
        ):
            components.html(
                pressure_diagram_html(),
                height=315,
                scrolling=False,
            )

### TELA 4
else:
    reports_bairros = topbar(bairros, "relatorio")
    page_title("Relatórios")
    with section("Tela prevista para desenvolvimento futuro", info=False):
        st.markdown(
            "Nesta área, futuramente poderão ser exibidos relatórios exportáveis por semana "
            "epidemiológica, cidade, UF, bairro, nível de alerta e hospitais em risco. "
            f"A seleção atual contém {len(reports_bairros)} bairro(s)."
        )
