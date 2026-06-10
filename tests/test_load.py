from unittest.mock import MagicMock, patch

import psycopg2
import pytest

from ingestion.db import get_connection
from ingestion.load import CREATE_TABLE_SQL, UPSERT_SQL, verify_load


def test_create_table_sql_is_idempotent():
    assert "CREATE TABLE IF NOT EXISTS raw_weather" in CREATE_TABLE_SQL
    assert "UNIQUE (city, timestamp)" in CREATE_TABLE_SQL
    assert "CREATE TABLE IF NOT EXISTS pipeline_runs" in CREATE_TABLE_SQL


def test_upsert_sql_handles_conflicts():
    assert "ON CONFLICT (city, timestamp) DO UPDATE" in UPSERT_SQL


def test_get_connection_retries_on_operational_error():
    conn = MagicMock()
    with patch(
        "ingestion.db.psycopg2.connect",
        side_effect=[psycopg2.OperationalError("refused"), conn],
    ) as mock_connect, patch("ingestion.db.time.sleep"):
        result = get_connection()
        assert result is conn
        assert mock_connect.call_count == 2


def test_get_connection_raises_after_exhausted_retries():
    with patch(
        "ingestion.db.psycopg2.connect",
        side_effect=psycopg2.OperationalError("refused"),
    ), patch("ingestion.db.time.sleep"), pytest.raises(RuntimeError, match="Could not connect"):
        get_connection()


def test_verify_load_passes_when_count_met():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (72,)
    conn.cursor.return_value.__enter__.return_value = cursor

    verify_load(conn, 72)
    cursor.execute.assert_called_once()


def test_verify_load_fails_when_count_low():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (10,)
    conn.cursor.return_value.__enter__.return_value = cursor

    with pytest.raises(RuntimeError, match="Post-load verification failed"):
        verify_load(conn, 72)
