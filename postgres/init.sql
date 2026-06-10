-- Raw landing schema for ingestion jobs
CREATE SCHEMA IF NOT EXISTS public;

-- Analytics schema for dbt models
CREATE SCHEMA IF NOT EXISTS analytics;

GRANT ALL ON SCHEMA public TO admin;
GRANT ALL ON SCHEMA analytics TO admin;

-- Pipeline audit log (also ensured by ingestion on each run)
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
