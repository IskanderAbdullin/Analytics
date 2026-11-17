from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ipo_forecast.schemas import ConfidenceGrade, EvidenceType, FeatureObservation


def test_optional_timestamps_can_be_null_but_required_times_are_timezone_aware():
    observation = FeatureObservation(
        observation_id="obs-1",
        ipo_id="ipo-1",
        feature_name="revenue_growth_yoy",
        value=0.42,
        event_at=None,
        published_at=None,
        available_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        source_id="sec",
        evidence_type=EvidenceType.OBSERVED,
        confidence_grade=ConfidenceGrade.A,
    )
    assert observation.event_at is None


def test_naive_availability_timestamp_is_rejected():
    with pytest.raises(ValidationError, match="Timestamp must include a timezone"):
        FeatureObservation(
            observation_id="obs-2",
            ipo_id="ipo-1",
            feature_name="revenue_growth_yoy",
            value=0.42,
            available_at=datetime(2026, 1, 1),
            retrieved_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            source_id="sec",
            evidence_type=EvidenceType.OBSERVED,
            confidence_grade=ConfidenceGrade.A,
        )
