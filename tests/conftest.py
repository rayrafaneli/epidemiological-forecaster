import pytest

@pytest.fixture
def sample_weather_data():
    """
    Dados simulados que poderão ser utilizados pelos testes.
    """

    return {
        "cidade": "Campinas",
        "temperatura": 25.5,
        "umidade": 70,
        "data": "2025-07-06"
    }
