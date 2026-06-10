"""Shared fixtures for elt-pipeline tests."""

from datetime import datetime, timezone

import pytest


@pytest.fixture()
def fake_record():
    """Return a factory for valid weather records."""

    def _make(**overrides):
        base = {
            "city": "Nairobi",
            "timestamp": "2026-06-10T12:00",
            "temperature": 22.5,
            "precipitation": 0.0,
            "windspeed": 8.0,
            "ingested_at": datetime.now(timezone.utc),
        }
        base.update(overrides)
        return base

    return _make


@pytest.fixture()
def full_city_batch():
    """Return a complete batch of 24 hourly records for all 3 cities."""
    records = []
    for city in ("Nairobi", "Mombasa", "Eldoret"):
        for h in range(24):
            records.append(
                {
                    "city": city,
                    "timestamp": f"2026-06-10T{h:02d}:00",
                    "temperature": 20.0 + h * 0.5,
                    "precipitation": max(0.0, h - 12) * 0.1,
                    "windspeed": 5.0 + h * 0.3,
                    "ingested_at": datetime.now(timezone.utc),
                }
            )
    return records


@pytest.fixture()
def fake_api_response():
    """Return a valid Open-Meteo API response dict."""

    def _make(n_hours: int = 24):
        return {
            "hourly": {
                "time": [f"2026-06-10T{h:02d}:00" for h in range(n_hours)],
                "temperature_2m": [20.0 + h * 0.5 for h in range(n_hours)],
                "precipitation": [max(0.0, h - 12) * 0.1 for h in range(n_hours)],
                "windspeed_10m": [5.0 + h * 0.3 for h in range(n_hours)],
            }
        }

    return _make