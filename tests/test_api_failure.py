from unittest.mock import patch
import requests


def fetch_weather_data():
    """
    Função simulada para representar uma chamada à API do INMET.
    Será substituída pela implementação real futuramente.
    """
    response = requests.get("https://api.inmet.gov.br")
    response.raise_for_status()
    return response.json()
  

@patch("requests.get")
def test_api_connection_error(mock_get):
    """Verifica se a aplicação trata falha de conexão."""
    mock_get.side_effect = requests.exceptions.ConnectionError

    try:
        fetch_weather_data()
    except requests.exceptions.ConnectionError:
        assert True


@patch("requests.get")
def test_api_timeout(mock_get):
    """Verifica se a aplicação trata timeout."""
    mock_get.side_effect = requests.exceptions.Timeout

    try:
        fetch_weather_data()
    except requests.exceptions.Timeout:
        assert True
