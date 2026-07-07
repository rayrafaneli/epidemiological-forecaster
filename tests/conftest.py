import pytest

@pytest.fixture
def sample_data():
  return {
    "cidade": "Campinas" ,
    "temperatura": 24.5,
    "umidade": 70,
    "data": "2026-07-05"
  }
