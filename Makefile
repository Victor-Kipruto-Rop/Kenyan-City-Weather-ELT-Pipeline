.PHONY: help setup up down status logs wait-db ingest dbt-deps dbt-run dbt-test test test-integration test-all health pipeline reset clean

PYTHON ?= $(shell test -x .venv/bin/python && echo .venv/bin/python || echo python)

help:
	@echo "Kenyan Weather ELT Pipeline"
	@echo ""
	@echo "  make setup       Create venv and install dependencies"
	@echo "  make up          Start Postgres + Metabase"
	@echo "  make down        Stop containers"
	@echo "  make status      Show container health"
	@echo "  make logs        Tail service logs"
	@echo "  make wait-db     Wait until PostgreSQL is ready"
	@echo "  make ingest      Run extraction + validation + load"
	@echo "  make pipeline    Full run: wait-db + ingest + dbt + health"
	@echo "  make dbt-deps    Install dbt package dependencies"
	@echo "  make dbt-run     Run dbt models"
	@echo "  make dbt-test    Run dbt tests"
	@echo "  make test        Run Python unit tests (excludes integration)"
	@echo "  make test-integration  Run integration tests (requires DB)"
	@echo "  make test-all    Run all tests"
	@echo "  make health      Verify DB connectivity and latest run"
	@echo "  make reset       Recreate containers and volumes"
	@echo "  make clean       Stop containers and remove volumes"

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

status:
	docker compose ps

logs:
	docker compose logs -f

wait-db:
	$(PYTHON) scripts/wait_for_postgres.py

ingest:
	$(PYTHON) -m ingestion.load

dbt-deps:
	cd dbt_project && dbt deps

dbt-run: dbt-deps
	cd dbt_project && dbt run

dbt-test: dbt-deps
	cd dbt_project && dbt test

test:
	$(PYTHON) -m pytest tests/ -v --ignore=tests/test_pipeline_integration.py

test-integration:
	$(PYTHON) -m pytest tests/test_pipeline_integration.py -v

test-all:
	$(PYTHON) -m pytest tests/ -v

health:
	$(PYTHON) scripts/healthcheck.py

pipeline: wait-db ingest dbt-run dbt-test health

reset:
	docker compose down -v
	docker compose up -d

clean:
	docker compose down -v
