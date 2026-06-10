from datetime import datetime, timezone

from ingestion.validate import (
    validate_extraction_completeness,
    validate_record,
    validate_records,
)


def _record(**overrides):
    base = {
        "city": "Nairobi",
        "timestamp": "2026-06-10T12:00",
        "temperature": 22.5,
        "precipitation": 0.0,
        "windspeed": 8.0,
        "ingested_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return base


def test_validate_record_success():
    assert validate_record(_record()) == []


def test_validate_record_rejects_unknown_city():
    issues = validate_record(_record(city="Kisumu"))
    assert any("unknown city" in issue for issue in issues)


def test_validate_record_rejects_out_of_range_temperature():
    issues = validate_record(_record(temperature=60.0))
    assert any("temperature out of range" in issue for issue in issues)


def test_validate_record_rejects_null_temperature():
    issues = validate_record(_record(temperature=None))
    assert any("missing temperature" in issue for issue in issues)


def test_validate_records_accepts_valid_batch():
    result = validate_records([_record(), _record(city="Mombasa")])
    assert not result.is_valid  # incomplete city coverage


def test_validate_records_rejects_empty_batch():
    result = validate_records([])
    assert not result.is_valid
    assert "no records to validate" in result.errors


def test_validate_extraction_completeness_success():
    records = [_record(city=city, timestamp=f"2026-06-10T{h:02d}:00") for city in ("Nairobi", "Mombasa", "Eldoret") for h in range(24)]
    assert validate_extraction_completeness(records) == []


def test_validate_extraction_completeness_detects_missing_city():
    records = [_record(city="Nairobi", timestamp=f"2026-06-10T{h:02d}:00") for h in range(24)]
    issues = validate_extraction_completeness(records)
    assert any("Mombasa" in issue for issue in issues)
    assert any("Eldoret" in issue for issue in issues)


def test_validate_records_full_pipeline_batch():
    records = [_record(city=city, timestamp=f"2026-06-10T{h:02d}:00") for city in ("Nairobi", "Mombasa", "Eldoret") for h in range(24)]
    result = validate_records(records)
    assert result.is_valid
    assert len(result.valid_records) == 72
    assert not result.rejected_records
