import logging
import time

import psycopg2

from ingestion.config import DB_CONFIG, DB_CONNECT_DELAY, DB_CONNECT_RETRIES

logger = logging.getLogger(__name__)


def get_connection():
    last_error = None
    for attempt in range(1, DB_CONNECT_RETRIES + 1):
        try:
            conn = psycopg2.connect(**DB_CONFIG, connect_timeout=10)
            conn.autocommit = False
            return conn
        except psycopg2.OperationalError as exc:
            last_error = exc
            logger.warning(
                "Database connection attempt %s/%s failed: %s",
                attempt,
                DB_CONNECT_RETRIES,
                exc,
            )
            if attempt < DB_CONNECT_RETRIES:
                time.sleep(DB_CONNECT_DELAY)

    raise RuntimeError(
        f"Could not connect to PostgreSQL after {DB_CONNECT_RETRIES} attempts"
    ) from last_error


def table_exists(conn, table_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = %s
            )
            """,
            (table_name,),
        )
        return bool(cur.fetchone()[0])
