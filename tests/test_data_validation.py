import pytest

def validate_data(data):
  assert isinstance(data["cidade"],str)
  assert data["cidade"] != ""
  
  assert isinstance(data["temperatura"], (int, float))
                    
  assert isinstance(data["umidade"], int)
                    
  assert isinstance(data["data"], str)
  
  return True

def test_valid_data(sample_data):
  assert validate_data(sample_data)

def test_invalid_temperature(sample_data):
  sample_data["temperatura"] = "quente"
  
  with pytest.raises(AssertionError):
    validate_data(sample_data)

def test_empty_city(sample_data):
  sample_data["cidade"] = ""
  
  with pytest.raises(AssertionError):
    validate_data(sample_data)

def test_invalid_humidity(sample_data):
  sample_data["umidade"] = "alta"
  
  with pytest.raises(AssertionError):
    validate_data(sample_data)
