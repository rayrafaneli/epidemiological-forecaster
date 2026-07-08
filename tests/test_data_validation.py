import pytest


def validate_weather_data(data):
    required_fields = [
        "cidade",
        "temperatura",
        "umidade",
        "data"
    ]

    for field in required_fields:
        assert field in data

    assert isinstance(data["cidade"], str)
    assert data["cidade"] != ""

    assert isinstance(data["temperatura"], (int, float))
    assert isinstance(data["umidade"], int)
    assert isinstance(data["data"], str)

    return True


def test_valid_weather_data(sample_weather_data):
    assert validate_weather_data(sample_weather_data)


def test_invalid_temperature(sample_weather_data):
    sample_weather_data["temperatura"] = "vinte"

    with pytest.raises(AssertionError):
        validate_weather_data(sample_weather_data)


def test_missing_required_field(sample_weather_data):
    del sample_weather_data["cidade"]

    with pytest.raises(AssertionError):
        validate_weather_data(sample_weather_data)
