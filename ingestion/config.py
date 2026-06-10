import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

CITIES = {
    "Nairobi": {"lat": -1.2921, "lon": 36.8219},
    "Mombasa": {"lat": -4.0435, "lon": 39.6682},
    "Eldoret": {"lat": 0.5143, "lon": 35.2698},
}

OPEN_METEO_URL = os.getenv(
    "OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast"
)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "2.0"))
FORECAST_DAYS = int(os.getenv("FORECAST_DAYS", "1"))
EXPECTED_HOURS_PER_CITY = FORECAST_DAYS * 24

DB_CONNECT_RETRIES = int(os.getenv("DB_CONNECT_RETRIES", "5"))
DB_CONNECT_DELAY = float(os.getenv("DB_CONNECT_DELAY", "2.0"))

DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "weather_db"),
    "user": os.getenv("POSTGRES_USER", "admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "password"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
}

# Kenya-relevant sanity bounds for hourly observations
TEMP_MIN_C = float(os.getenv("TEMP_MIN_C", "-5"))
TEMP_MAX_C = float(os.getenv("TEMP_MAX_C", "45"))
PRECIP_MAX_MM = float(os.getenv("PRECIP_MAX_MM", "200"))
WIND_MAX_KMH = float(os.getenv("WIND_MAX_KMH", "150"))
