import pytest
import requests

from ingestion.extract import build_session, extract_all, fetch_weather, _validate_response_schema


def test_validate_response_schema_success():
    data = {
        "hourly": {
            "time": ["2026-06-10T00:00", "2026-06-10T01:00"],
            "temperature_2m": [20.0, 21.0],
            "precipitation": [0.0, 0.5],
            "windspeed_10m": [5.0, 6.0],
        }
    }
    _validate_response_schema(data)


def test_validate_response_schema_missing_field():
    with pytest.raises(ValueError, match="temperature_2m"):
        _validate_response_schema(
            {
                "hourly": {
                    "time": ["2026-06-10T00:00"],
                    "precipitation": [0.0],
                    "windspeed_10m": [5.0],
                }
            }
        )


def test_fetch_weather_success(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "hourly": {
                    "time": ["2026-06-10T00:00"],
                    "temperature_2m": [20.0],
                    "precipitation": [0.0],
                    "windspeed_10m": [5.0],
                }
            }

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

        def mount(self, *args, **kwargs):
            return None

        def close(self):
            return None

    monkeypatch.setattr("ingestion.extract.build_session", lambda: FakeSession())

    records = fetch_weather("Nairobi", -1.29, 36.82)
    assert len(records) == 1
    assert records[0]["city"] == "Nairobi"
    assert records[0]["temperature"] == 20.0
    assert records[0]["ingested_at"] is not None


def test_fetch_weather_invalid_json(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            raise ValueError("bad json")

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            return None

    with pytest.raises(ValueError, match="Invalid JSON"):
        fetch_weather("Nairobi", -1.29, 36.82, session=FakeSession())


def test_fetch_weather_api_error(monkeypatch):
    class FakeSession:
        def get(self, *args, **kwargs):
            raise requests.RequestException("API error")

        def mount(self, *args, **kwargs):
            return None

        def close(self):
            return None

    monkeypatch.setattr("ingestion.extract.build_session", lambda: FakeSession())

    with pytest.raises(requests.RequestException):
        fetch_weather("Nairobi", -1.29, 36.82)


def test_extract_all_partial_failure(monkeypatch):
    class FakeSession:
        def close(self):
            return None

    def fake_fetch(city, lat, lon, session=None):
        if city == "Nairobi":
            raise requests.RequestException("down")
        return [
            {
                "city": city,
                "timestamp": "2026-06-10T00:00",
                "temperature": 20.0,
                "precipitation": 0.0,
                "windspeed": 5.0,
                "ingested_at": "2026-06-10T12:00:00+00:00",
            }
        ]

    monkeypatch.setattr("ingestion.extract.build_session", lambda: FakeSession())
    monkeypatch.setattr("ingestion.extract.fetch_weather", fake_fetch)

    with pytest.raises(RuntimeError, match="Nairobi"):
        extract_all()


def test_build_session_returns_session():
    session = build_session()
    assert session is not None
    session.close()
