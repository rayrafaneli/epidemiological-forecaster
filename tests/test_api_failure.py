from unittest.mock import patch
import requests

def get_weather():
  """Simula uma chamada para a API do INMET."""
  response = requests.get("https://api.inmet.gov.br")
  
  if response.status_code != 200:
    return None

  return response.json()

@patch("requests.get")
def test_api_unavailable(mock_get):
  """Testa comportamento quando a API está fora do ar."""
  mock_get.side_effect = requests.exceptions.ConnectionError

  try:
    get_weather()
  except requests.exceptions.ConnectionError:
    assert True

@patch("requests.get")
def test_api_returns_500(mock_get):
  ".Testa retorno 500 da API."""
  mock_get.return_value.status_code = 500
  
  result = get_wheather()
  
  assert result is None
