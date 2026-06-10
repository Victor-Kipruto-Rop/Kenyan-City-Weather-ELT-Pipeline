#!/usr/bin/env python3
"""Wait until PostgreSQL accepts connections."""

import logging
import sys

from ingestion.db import get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def wait_for_postgres() -> None:
    """Attempt a single connection; raise on failure.

    ``get_connection()`` already applies exponential-backoff retries
    configured via ``DB_CONNECT_RETRIES`` / ``DB_CONNECT_DELAY``, so
    this function simply delegates to it without wrapping in an
    additional retry loop.
    """
    try:
        conn = get_connection()
        conn.close()
        logger.info("PostgreSQL is ready.")
    except RuntimeError as exc:
        logger.error("PostgreSQL not reachable: %s", exc)
        raise


if __name__ == "__main__":
    try:
        wait_for_postgres()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)