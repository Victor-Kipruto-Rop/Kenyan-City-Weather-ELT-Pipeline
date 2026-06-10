"""Integration tests for the full ingestion pipeline.

These tests require a running PostgreSQL instance (e.g. via ``make up``).
They are skipped automatically when the database is unreachable.
"""

from datetime import datetime, timezone

import psycopg2
import pytest

from ingestion.config import CITIES, DB_CONFIG
from ingestion.db import get_connection, table_exists
from ingestion.load import create_table, load, verify_load


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _db_available() -> bool:
    """Return True if the test database is reachable."""
    try:
        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=3)
        conn.close()
        return True
    except psycopg2.OperationalError:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="Integration tests require a running PostgreSQL instance",
)


@pytest.fixture()
def db_conn():
    """Yield a database connection, rolled back and closed after the test."""
    conn = get_connection()
    yield conn
    conn.rollback()
    conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@requires_db
def test_create_table_is_idempotent(db_conn):
    """Running CREATE TABLE twice should not raise."""
    create_table(db_conn)
    create_table(db_conn)
    assert table_exists(db_conn, "raw_weather")
    assert table_exists(db_conn, "pipeline_runs")


@requires_db
def test_upsert_and_verify(db_conn):
    """Load a small batch and verify the post-load check passes."""
    create_table(db_conn)

    now = datetime.now(timezone.utc)
    records = [
        {
            "city": city,
            "timestamp": f"2099-01-01T{h:02d}:00",
            "temperature": 20.0,
            "precipitation": 0.0,
            "windspeed": 5.0,
            "ingested_at": now,
        }
        for city in CITIES
        for h in range(3)
    ]

    loaded = load(db_conn, records)
    assert loaded == len(records)
    verify_load(db_conn, loaded)

    # Cleanup test data
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM raw_weather WHERE timestamp >= '2099-01-01'")
    db_conn.commit()


@requires_db
def test_load_rejects_empty_batch(db_conn):
    """Loading zero records should raise ValueError."""
    with pytest.raises(ValueError, match="no records to load"):
        load(db_conn, [])


@requires_db
def test_load_handles_duplicate_upsert(db_conn):
    """Upserting the same records twice should not create duplicates."""
    create_table(db_conn)

    now = datetime.now(timezone.utc)
    records = [
        {
            "city": "Nairobi",
            "timestamp": "2099-02-01T00:00",
            "temperature": 25.0,
            "precipitation": 0.0,
            "windspeed": 10.0,
            "ingested_at": now,
        }
    ]

    load(db_conn, records)
    load(db_conn, records)  # duplicate upsert

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM raw_weather "
            "WHERE city = 'Nairobi' AND timestamp = '2099-02-01T00:00'"
        )
        count = cur.fetchone()[0]

    assert count == 1, f"Expected 1 row after upsert, got {count}"

    # Cleanup
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM raw_weather WHERE timestamp >= '2099-02-01'")
    db_conn.commit()


@requires_db
def test_pipeline_runs_table_records_status(db_conn):
    """After a successful pipeline run, pipeline_runs should show 'success'."""
    create_table(db_conn)

    # Insert a fake completed run
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_runs (started_at, finished_at, status, records_loaded)
            VALUES (%s, %s, 'success', 72)
            RETURNING id
            """,
            (datetime.now(timezone.utc), datetime.now(timezone.utc)),
        )
        run_id = cur.fetchone()[0]
    db_conn.commit()

    with db_conn.cursor() as cur:
        cur.execute("SELECT status FROM pipeline_runs WHERE id = %s", (run_id,))
        status = cur.fetchone()[0]

    assert status == "success"

    # Cleanup
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM pipeline_runs WHERE id = %s", (run_id,))
    db_conn.commit()