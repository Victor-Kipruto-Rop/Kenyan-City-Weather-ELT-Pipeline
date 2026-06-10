import logging
import sys
from datetime import datetime, timezone
from typing import Any

from psycopg2.extras import execute_values

from ingestion.db import get_connection
from ingestion.extract import extract_all
from ingestion.validate import validate_records

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS raw_weather (
    id BIGSERIAL PRIMARY KEY,
    city VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    temperature DOUBLE PRECISION,
    precipitation DOUBLE PRECISION,
    windspeed DOUBLE PRECISION,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT raw_weather_city_timestamp_key UNIQUE (city, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_raw_weather_city_timestamp
    ON raw_weather (city, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_raw_weather_ingested_at
    ON raw_weather (ingested_at DESC);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL,
    records_extracted INTEGER,
    records_loaded INTEGER,
    records_rejected INTEGER,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at
    ON pipeline_runs (started_at DESC);
"""

UPSERT_SQL = """
INSERT INTO raw_weather (
    city, timestamp, temperature, precipitation, windspeed, ingested_at
)
VALUES %s
ON CONFLICT (city, timestamp) DO UPDATE SET
    temperature = EXCLUDED.temperature,
    precipitation = EXCLUDED.precipitation,
    windspeed = EXCLUDED.windspeed,
    ingested_at = EXCLUDED.ingested_at;
"""


def create_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    logger.info("Ensured raw_weather and pipeline_runs tables exist")


def _start_run(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_runs (started_at, status)
            VALUES (%s, 'running')
            RETURNING id
            """,
            (datetime.now(timezone.utc),),
        )
        run_id = cur.fetchone()[0]
    conn.commit()
    return run_id


def _finish_run(
    conn,
    run_id: int,
    *,
    status: str,
    records_extracted: int = 0,
    records_loaded: int = 0,
    records_rejected: int = 0,
    error_message: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE pipeline_runs
            SET finished_at = %s,
                status = %s,
                records_extracted = %s,
                records_loaded = %s,
                records_rejected = %s,
                error_message = %s
            WHERE id = %s
            """,
            (
                datetime.now(timezone.utc),
                status,
                records_extracted,
                records_loaded,
                records_rejected,
                error_message,
                run_id,
            ),
        )
    conn.commit()


def load(conn, records: list[dict[str, Any]]) -> int:
    if not records:
        raise ValueError("no records to load")

    rows = [
        (
            r["city"],
            r["timestamp"],
            r["temperature"],
            r["precipitation"],
            r["windspeed"],
            r["ingested_at"],
        )
        for r in records
    ]

    try:
        with conn.cursor() as cur:
            execute_values(cur, UPSERT_SQL, rows, page_size=500)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    logger.info("Loaded %s records into raw_weather", len(rows))
    return len(rows)


def verify_load(conn, expected_count: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM raw_weather
            WHERE ingested_at >= NOW() - INTERVAL '5 minutes'
            """
        )
        recent_count = cur.fetchone()[0]

    if recent_count < expected_count:
        raise RuntimeError(
            f"Post-load verification failed: expected at least {expected_count} "
            f"recent rows, found {recent_count}"
        )

    logger.info("Post-load verification passed (%s recent rows)", recent_count)


def run_pipeline() -> int:
    conn = None
    run_id = None
    records_extracted = 0
    records_rejected = 0

    try:
        conn = get_connection()
        create_table(conn)
        run_id = _start_run(conn)

        records = extract_all()
        records_extracted = len(records)

        validation = validate_records(records)
        records_rejected = len(validation.rejected_records)

        if not validation.is_valid:
            for error in validation.errors[:10]:
                logger.error("Validation error: %s", error)
            raise ValueError("data quality checks failed")

        loaded = load(conn, validation.valid_records)
        verify_load(conn, loaded)

        _finish_run(
            conn,
            run_id,
            status="success",
            records_extracted=records_extracted,
            records_loaded=loaded,
            records_rejected=records_rejected,
        )
        return loaded

    except Exception as exc:
        if conn is not None and run_id is not None:
            conn.rollback()
            _finish_run(
                conn,
                run_id,
                status="failed",
                records_extracted=records_extracted,
                records_rejected=records_rejected,
                error_message=str(exc)[:1000],
            )
        raise
    finally:
        if conn is not None:
            conn.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    try:
        loaded = run_pipeline()
        logger.info("Pipeline completed successfully (%s rows)", loaded)
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        sys.exit(1)
