"""
tests/test_inmet_transformer.py
===============================================================================
POR QUE TESTAR SÓ A CAMADA TRANSFORM (E NÃO EXTRACT/LOAD) NESTE EXEMPLO?
-----------------------
Extract depende de rede (download dos ZIPs do INMET) e Load depende de um
banco Postgres rodando. Isso os torna testes de INTEGRAÇÃO, mais lentos e
"flaky" (instáveis). A camada Transform, por outro lado, é só lógica pura de
Python sobre um DataFrame - não depende de nada externo. Por isso ela é o
melhor ponto para um TESTE UNITÁRIO: rápido, determinístico, sem
necessidade de internet ou banco configurado.

ATENÇÃO - HISTÓRICO DESTE ARQUIVO:
A versão anterior destes testes usava colunas como "CD_ESTACAO"/"DT_MEDICAO"
/"TEM_MAX", que eram o formato da API apitempo/estacao/diaria (endpoint que
o INMET descontinuou - ver src/extract/inmet_extractor.py). Como o
transform_inmet_daily atual espera dado HORÁRIO no formato produzido pelo
InmetExtractor.get_hourly_history() (colunas "codigo_estacao", "data",
"hora", "temperatura_ar", "precipitacao", ...), aqueles testes iriam falhar
silenciosamente sempre no primeiro `if`: como a coluna "data" não existia,
transform_inmet_daily devolvia um DataFrame vazio antes mesmo das asserções
rodarem. Este arquivo foi atualizado para usar o formato correto e atual.

COMO RODAR
-----------------------
    pytest tests/ -v
(É preciso instalar o pytest: pip install pytest)
===============================================================================
"""

import pandas as pd
from src.transform.inmet_transformer import transform_inmet_daily


def test_valor_fora_da_faixa_fisica_vira_nulo():
    """Uma temperatura fisicamente implausível (ex: erro de sensor) deve
    virar NaN depois da agregação diária, não ser mantida como está."""
    df_bruto = pd.DataFrame([
        {"codigo_estacao": "A307", "data": "2024-01-01", "hora": "0000 UTC", "temperatura_ar": 999},
        {"codigo_estacao": "A307", "data": "2024-01-01", "hora": "0100 UTC", "temperatura_ar": 28},
    ])
    df_limpo = transform_inmet_daily(df_bruto)
    assert pd.isna(df_limpo.loc[0, "temp_max_c"])


def test_leitura_sem_data_e_descartada():
    """Uma leitura horária sem data não tem como ser usada e deve ser descartada."""
    df_bruto = pd.DataFrame([
        {"codigo_estacao": "A307", "data": None, "hora": "0000 UTC", "temperatura_ar": 30},
        {"codigo_estacao": "A307", "data": "2024-01-02", "hora": "0000 UTC", "temperatura_ar": 30},
    ])
    df_limpo = transform_inmet_daily(df_bruto)
    assert len(df_limpo) == 1


def test_horas_do_mesmo_dia_sao_agregadas_em_uma_linha():
    """Múltiplas leituras horárias da mesma estação/dia devem virar UMA
    única linha diária, com temp_max/min/media e precipitação somada."""
    df_bruto = pd.DataFrame([
        {"codigo_estacao": "A307", "data": "2024-01-01", "hora": "0000 UTC",
         "temperatura_ar": 24, "precipitacao": 0},
        {"codigo_estacao": "A307", "data": "2024-01-01", "hora": "1200 UTC",
         "temperatura_ar": 30, "precipitacao": 2},
    ])
    df_limpo = transform_inmet_daily(df_bruto)
    assert len(df_limpo) == 1
    assert df_limpo.loc[0, "temp_max_c"] == 30
    assert df_limpo.loc[0, "temp_min_c"] == 24
    assert df_limpo.loc[0, "precipitacao_total_mm"] == 2


def test_estacoes_diferentes_nao_sao_misturadas():
    """Duas estações no mesmo dia devem gerar duas linhas, não uma média conjunta."""
    df_bruto = pd.DataFrame([
        {"codigo_estacao": "A301", "data": "2024-01-01", "hora": "1200 UTC", "temperatura_ar": 20},
        {"codigo_estacao": "A307", "data": "2024-01-01", "hora": "1200 UTC", "temperatura_ar": 30},
    ])
    df_limpo = transform_inmet_daily(df_bruto)
    assert len(df_limpo) == 2
