import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ingestion.config import (
    CITIES,
    EXPECTED_HOURS_PER_CITY,
    PRECIP_MAX_MM,
    TEMP_MAX_C,
    TEMP_MIN_C,
    WIND_MAX_KMH,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    valid_records: list[dict[str, Any]] = field(default_factory=list)
    rejected_records: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return bool(self.valid_records) and not self.errors


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and value is not None


def validate_record(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    city = record.get("city")
    if city not in CITIES:
        issues.append(f"unknown city: {city}")

    if not record.get("timestamp"):
        issues.append("missing timestamp")

    temp = record.get("temperature")
    if temp is None:
        issues.append("missing temperature")
    elif not _is_number(temp) or not (TEMP_MIN_C <= temp <= TEMP_MAX_C):
        issues.append(f"temperature out of range: {temp}")

    precip = record.get("precipitation")
    if precip is None:
        issues.append("missing precipitation")
    elif not _is_number(precip) or precip < 0 or precip > PRECIP_MAX_MM:
        issues.append(f"precipitation out of range: {precip}")

    wind = record.get("windspeed")
    if wind is None:
        issues.append("missing windspeed")
    elif not _is_number(wind) or wind < 0 or wind > WIND_MAX_KMH:
        issues.append(f"windspeed out of range: {wind}")

    if not record.get("ingested_at"):
        issues.append("missing ingested_at")

    return issues


def validate_extraction_completeness(records: list[dict[str, Any]]) -> list[str]:
    counts = Counter(record["city"] for record in records)
    issues: list[str] = []

    for city in CITIES:
        count = counts.get(city, 0)
        if count != EXPECTED_HOURS_PER_CITY:
            issues.append(
                f"{city}: expected {EXPECTED_HOURS_PER_CITY} hourly records, got {count}"
            )

    return issues


def validate_records(records: list[dict[str, Any]]) -> ValidationResult:
    result = ValidationResult()

    if not records:
        result.errors.append("no records to validate")
        return result

    completeness_issues = validate_extraction_completeness(records)
    result.errors.extend(completeness_issues)

    for record in records:
        issues = validate_record(record)
        if issues:
            result.rejected_records.append(record)
            result.errors.append(
                f"{record.get('city')}@{record.get('timestamp')}: {', '.join(issues)}"
            )
        else:
            result.valid_records.append(record)

    if result.rejected_records:
        logger.warning(
            "Rejected %s of %s records during validation",
            len(result.rejected_records),
            len(records),
        )

    if not result.valid_records:
        result.errors.append("all records failed validation")

    logger.info(
        "Validation passed for %s records (%s rejected)",
        len(result.valid_records),
        len(result.rejected_records),
    )
    return result
