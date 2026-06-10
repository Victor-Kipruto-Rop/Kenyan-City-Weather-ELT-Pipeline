#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

PYTHON="${PYTHON:-python}"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
step() {
  echo ""
  echo "========================================"
  echo "  $1"
  echo "========================================"
}

# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------
step "Waiting for Postgres"
"$PYTHON" scripts/wait_for_postgres.py

step "Extracting & loading weather data"
"$PYTHON" -m ingestion.load

step "Running dbt dependencies"
cd dbt_project && dbt deps && cd ..

step "Running dbt models"
cd dbt_project && dbt run && cd ..

step "Running dbt tests"
cd dbt_project && dbt test && cd ..

step "Running health check"
"$PYTHON" scripts/healthcheck.py

echo ""
echo "Pipeline completed successfully."