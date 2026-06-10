#!/usr/bin/env python3
"""Check pipeline infrastructure and latest ingestion run."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.config import CITIES
from ingestion.db import get_connection, table_exists

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def healthcheck() -> int:
    issues: list[str] = []

    # --- Database connectivity ---
    try:
        conn = get_connection()
    except RuntimeError as exc:
        logger.error("Database unreachable: %s", exc)
        return 1

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")

        logger.info("Database connected")

        # --- raw_weather table ---
        if not table_exists(conn, "raw_weather"):
            issues.append("raw_weather table does not exist (run make ingest)")
        else:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM raw_weather")
                total_rows = cur.fetchone()[0]
                logger.info("raw_weather: %s total rows", total_rows)

                cur.execute(
                    """
                    SELECT city, COUNT(*)
                    FROM raw_weather
                    GROUP BY city
                    ORDER BY city
                    """
                )
                city_counts = dict(cur.fetchall())

            for city in CITIES:
                count = city_counts.get(city, 0)
                if count == 0:
                    issues.append(f"no data for {city}")
                else:
                    logger.info("  %s: %s rows", city, count)

        # --- pipeline_runs table ---
        if not table_exists(conn, "pipeline_runs"):
            issues.append("pipeline_runs table does not exist (run make ingest)")
        else:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT status, records_loaded, finished_at
                    FROM pipeline_runs
                    ORDER BY started_at DESC
                    LIMIT 1
                    """
                )
                last_run = cur.fetchone()

            if last_run:
                status, loaded, finished_at = last_run
                logger.info(
                    "Last pipeline run: status=%s, loaded=%s, finished=%s",
                    status,
                    loaded,
                    finished_at,
                )
                if status != "success":
                    issues.append(f"last pipeline run status is {status}")
            else:
                issues.append("no pipeline runs recorded")

    finally:
        conn.close()

    if issues:
        for issue in issues:
            logger.warning("ISSUE: %s", issue)
        return 1

    logger.info("Health check passed")
    return 0


if __name__ == "__main__":
    sys.exit(healthcheck())