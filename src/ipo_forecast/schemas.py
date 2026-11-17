"""Validated domain schemas for IPO events and point-in-time observations."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceType(StrEnum):
    OBSERVED = "observed"
    ESTIMATED = "estimated"
    ANALYST_OPINION = "analyst_opinion"
    SYNTHETIC = "synthetic"


class ForecastOrigin(StrEnum):
    PRELIMINARY_FILING = "preliminary_filing"
    AFTER_PRICING_PRE_OPEN = "after_pricing_pre_open"
    POST_OPEN = "post_open"


class ConfidenceGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class AvailabilityPrecision(StrEnum):
    EXACT_TIMESTAMP = "exact_timestamp"
    DATE_ONLY = "date_only"
    CONSERVATIVE_NEXT_SESSION = "conservative_next_session"
    ESTIMATED = "estimated"


def _require_timezone(value: datetime | None) -> datetime | None:
    if value is None:
        return value
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    return value


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    access_method: str = Field(min_length=1)
    licence_notes: str | None = None
    retrieved_at: datetime
    terms_reviewed_at: date | None = None

    _check_retrieved_at = field_validator("retrieved_at")(_require_timezone)


class IPOEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ipo_id: str = Field(min_length=1)
    issuer_name: str = Field(min_length=1)
    ticker: str | None = None
    exchange: str = Field(min_length=1)
    country: str = Field(min_length=1)
    listing_date: date
    offer_price: float | None = Field(default=None, gt=0)
    currency: str | None = None
    shares_offered: int | None = Field(default=None, gt=0)
    evidence_type: EvidenceType
    confidence_grade: ConfidenceGrade
    source_ids: list[str] = Field(default_factory=list)


class FeatureObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    ipo_id: str = Field(min_length=1)
    feature_name: str = Field(min_length=1)
    value: float | int | bool | str | None
    unit: str | None = None
    event_at: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime
    availability_precision: AvailabilityPrecision
    retrieved_at: datetime
    source_id: str = Field(min_length=1)
    source_record_url: str | None = None
    evidence_type: EvidenceType
    confidence_grade: ConfidenceGrade
    notes: str | None = None

    _check_timestamps = field_validator(
        "event_at", "published_at", "available_at", "retrieved_at"
    )(_require_timezone)


class ForecastOriginRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forecast_id: str = Field(min_length=1)
    ipo_id: str = Field(min_length=1)
    as_of_timestamp: datetime
    forecast_origin: ForecastOrigin
    target_horizon: str = Field(min_length=1)
    listing_date: date
    reference_price: float | None = Field(default=None, gt=0)
    reference_price_type: str | None = None

    _check_as_of = field_validator("as_of_timestamp")(_require_timezone)


class ForecastRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    forecast_id: str
    model_version: str
    created_at: datetime
    predicted_return: float
    probability_positive: float | None = Field(default=None, ge=0, le=1)
    lower_prediction_interval: float | None = None
    upper_prediction_interval: float | None = None

    _check_created_at = field_validator("created_at")(_require_timezone)
