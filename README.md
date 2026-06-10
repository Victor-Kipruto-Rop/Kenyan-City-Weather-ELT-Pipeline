# Kenyan City Weather ELT Pipeline

Production-style ELT pipeline that ingests hourly weather for **Nairobi**, **Mombasa**, and **Eldoret** from the [Open-Meteo API](https://open-meteo.com/), loads into PostgreSQL with idempotent upserts, transforms via dbt, and exposes analytics through Metabase.

## Architecture

```
┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────┐
│ Open-Meteo   │───▶│ Extract     │───▶│ Validate     │───▶│ Load     │───▶│ dbt      │
│ Forecast API │    │ (retry)     │    │ (DQ checks)  │    │ (upsert) │    │ models   │
└──────────────┘    └─────────────┘    └──────────────┘    └──────────┘    └────┬─────┘
                                                                                  │
                                                                           ┌──────▼──────┐
                                                                           │  Metabase   │
                                                                           │  Dashboard  │
                                                                           └─────────────┘
```

## Project Structure

```
elt-pipeline/
├── ingestion/              # Python ELT package
│   ├── config.py             # Env-based configuration
│   ├── db.py                 # Connection retry + helpers
│   ├── extract.py            # API extraction with retries
│   ├── validate.py           # Pre-load data quality checks
│   └── load.py               # Batch upsert + audit logging
├── scripts/
│   ├── run_pipeline.sh       # End-to-end runner
│   ├── wait_for_postgres.py  # DB readiness probe
│   └── healthcheck.py        # Post-run health verification
├── dbt_project/              # SQL transformation layer
├── postgres/init.sql         # DB bootstrap (analytics schema + audit table)
├── tests/                    # Python unit tests (22 tests)
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Source | Open-Meteo API | Free, no-key hourly weather forecasts |
| Ingestion | Python 3.10+ | Extract, validate, load with retries |
| Warehouse | PostgreSQL 15 | Raw + analytics storage |
| Transform | dbt + dbt_utils | Medallion-style SQL models & tests |
| BI | Metabase | Dashboarding |
| Infra | Docker Compose | Reproducible local stack |

## Real-World Features

- **Retries & timeouts** on API calls (429/5xx backoff) and DB connections
- **Schema validation** of API responses before parsing (including JSON errors)
- **Completeness checks** — verifies all cities return expected hourly record counts
- **Pre-load DQ checks** (range validation, required fields, null rejection)
- **Idempotent upserts** via `ON CONFLICT` with batch inserts and rollback on failure
- **Post-load verification** — confirms rows landed in the database
- **Pipeline audit log** — `pipeline_runs` table tracks every run (status, counts, errors)
- **dbt source freshness** monitoring on `ingested_at`
- **dbt tests**: 26+ tests including city coverage and range checks
- **Health checks** on Postgres, Metabase containers, and pipeline state (`make health`)
- **CI workflow** — GitHub Actions runs unit tests on every push
- **Env-based config** via `.env` (no hardcoded secrets in code)

## Quickstart

### Prerequisites

- Docker & Docker Compose
- Python 3.10+

### 1. Configure

```bash
cd elt-pipeline
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start infrastructure

```bash
make up
make status    # wait until postgres is healthy
```

### 3. Run the pipeline

```bash
make pipeline
# or
bash scripts/run_pipeline.sh
```

### 4. Access services

| Service | URL | Credentials |
|---------|-----|-------------|
| Metabase | http://localhost:3000 | Set up on first visit |
| PostgreSQL | localhost:5432 | admin / password |

Connect Metabase to `analytics.weekly_trends` for dashboarding.

## Operations

```bash
make ingest       # Extract + validate + load only
make health       # Verify DB, city coverage, and last run status
make dbt-run      # Run transformations
make dbt-test     # Run dbt data tests
make test         # Run Python unit tests
make logs         # Tail container logs
make reset        # Recreate DB from scratch
```

## Scheduling (Production)

Run hourly via cron or a scheduler:

```bash
0 * * * * cd /path/to/elt-pipeline && /path/to/.venv/bin/python -m ingestion.load >> logs/ingest.log 2>&1
15 * * * * cd /path/to/elt-pipeline/dbt_project && dbt run && dbt test >> ../logs/dbt.log 2>&1
```

For production, consider Airflow (see `airflow-pipeline/` in this repo) for orchestration, alerting, and backfills.

## Data Model

| Layer | Model | Description |
|-------|-------|-------------|
| Raw | `public.raw_weather` | Hourly observations per city |
| Staging | `analytics.stg_weather` | Typed, cleaned observations |
| Intermediate | `analytics.int_daily_averages` | Daily aggregates per city |
| Marts | `analytics.weekly_trends` | Weekly KPIs for dashboards |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_DB` | `weather_db` | Database name |
| `MAX_RETRIES` | `3` | API retry attempts |
| `REQUEST_TIMEOUT` | `30` | API timeout (seconds) |
| `TEMP_MIN_C` / `TEMP_MAX_C` | `-5` / `45` | Temperature bounds |
| `FORECAST_DAYS` | `1` | Hours to fetch per run |

## Testing

```bash
make test         # Python unit tests (no infra required)
make dbt-test     # dbt tests (requires running Postgres + data)
```

## License

MIT
