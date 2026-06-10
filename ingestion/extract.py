import logging
from datetime import datetime, timezone
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ingestion.config import (
    CITIES,
    FORECAST_DAYS,
    MAX_RETRIES,
    OPEN_METEO_URL,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
)

logger = logging.getLogger(__name__)

HOURLY_FIELDS = ("temperature_2m", "precipitation", "windspeed_10m")


def build_session() -> requests.Session:
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _validate_response_schema(data: dict[str, Any]) -> None:
    hourly = data.get("hourly")
    if not hourly:
        raise ValueError("API response missing 'hourly' block")

    times = hourly.get("time")
    if not times:
        raise ValueError("API response missing hourly timestamps")

    for field in HOURLY_FIELDS:
        values = hourly.get(field)
        if values is None:
            raise ValueError(f"API response missing hourly field: {field}")
        if len(values) != len(times):
            raise ValueError(
                f"Hourly field '{field}' length ({len(values)}) "
                f"does not match timestamps ({len(times)})"
            )


def fetch_weather(
    city: str,
    lat: float,
    lon: float,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY_FIELDS),
        "timezone": "Africa/Nairobi",
        "forecast_days": FORECAST_DAYS,
    }

    owns_session = session is None
    session = session or build_session()
    try:
        response = session.get(
            OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as exc:
            raise ValueError(f"Invalid JSON response for {city}") from exc

        _validate_response_schema(data)

        ingested_at = datetime.now(timezone.utc)
        records = []
        for i, hour in enumerate(data["hourly"]["time"]):
            records.append(
                {
                    "city": city,
                    "timestamp": hour,
                    "temperature": data["hourly"]["temperature_2m"][i],
                    "precipitation": data["hourly"]["precipitation"][i],
                    "windspeed": data["hourly"]["windspeed_10m"][i],
                    "ingested_at": ingested_at,
                }
            )

        logger.info("Fetched %s records for %s", len(records), city)
        return records

    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.error("Failed to fetch weather for %s: %s", city, exc)
        raise
    finally:
        if owns_session:
            session.close()


def extract_all() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    session = build_session()

    try:
        for city, coords in CITIES.items():
            try:
                city_records = fetch_weather(
                    city, coords["lat"], coords["lon"], session=session
                )
                records.extend(city_records)
            except Exception:
                logger.exception("Extraction failed for %s", city)
                failures.append(city)
    finally:
        session.close()

    if failures:
        raise RuntimeError(
            f"Weather extraction failed for cities: {', '.join(failures)}"
        )

    logger.info(
        "Extracted %s total records across %s cities", len(records), len(CITIES)
    )
    return records
