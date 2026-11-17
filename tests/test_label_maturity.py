import pandas as pd
import pytest

from ipo_forecast.features.build import assemble_modeling_dataset
from ipo_forecast.validation.maturity import purge_unmatured_training_labels


def test_later_training_outcomes_are_excluded_before_validation_forecast():
    train = pd.DataFrame(
        [
            {
                "ipo_id": "ipo-1",
                "as_of_timestamp": "2025-01-01T14:00:00Z",
                "target_timestamp": "2025-04-01T21:00:00Z",
            },
            {
                "ipo_id": "ipo-2",
                "as_of_timestamp": "2025-03-01T14:00:00Z",
                "target_timestamp": "2026-08-01T21:00:00Z",
            },
        ]
    )
    validation = pd.DataFrame(
        [{"as_of_timestamp": "2026-07-01T14:00:00Z"}]
    )
    purged, report = purge_unmatured_training_labels(train, validation)
    assert purged["ipo_id"].tolist() == ["ipo-1"]
    assert report["purged_unmatured_rows"] == 1


def test_temporal_embargo_excludes_recent_training_labels():
    train = pd.DataFrame(
        [
            {
                "ipo_id": "ipo-old",
                "as_of_timestamp": "2026-01-01T14:00:00Z",
                "target_timestamp": "2026-06-01T21:00:00Z",
            },
            {
                "ipo_id": "ipo-recent",
                "as_of_timestamp": "2026-02-01T14:00:00Z",
                "target_timestamp": "2026-06-30T21:00:00Z",
            },
        ]
    )
    validation = pd.DataFrame(
        [{"as_of_timestamp": "2026-07-01T14:00:00Z"}]
    )
    purged, report = purge_unmatured_training_labels(
        train, validation, embargo_days=3
    )
    assert purged["ipo_id"].tolist() == ["ipo-old"]
    assert report["eligible_training_rows"] == 1


def test_missing_outcome_timestamp_fails_closed():
    with pytest.raises(ValueError, match="missing target_timestamp"):
        purge_unmatured_training_labels(
            pd.DataFrame([{"as_of_timestamp": "2025-01-01T00:00:00Z"}]),
            pd.DataFrame([{"as_of_timestamp": "2026-01-01T00:00:00Z"}]),
        )


def test_modeling_dataset_retains_target_timestamps():
    origins = pd.DataFrame(
        [
            {
                "forecast_id": "f1",
                "ipo_id": "ipo-1",
                "as_of_timestamp": "2026-01-01T00:00:00Z",
                "listing_date": "2026-01-05",
                "forecast_origin": "after_pricing_pre_open",
                "target_horizon": "day1_close",
            }
        ]
    )
    observations = pd.DataFrame(
        [
            {
                "observation_id": "obs1",
                "ipo_id": "ipo-1",
                "feature_name": "revenue_growth_yoy",
                "value": 0.5,
                "available_at": "2025-12-31T00:00:00Z",
            }
        ]
    )
    outcomes = pd.DataFrame(
        [
            {
                "forecast_id": "f1",
                "target_timestamp": "2026-01-05T21:00:00Z",
                "target_price": 50.0,
                "target_return": 0.25,
                "outcome_source_id": "tinvest_api",
            }
        ]
    )
    result = assemble_modeling_dataset(origins, observations, outcomes)
    assert result.loc[0, "target_timestamp"] == "2026-01-05T21:00:00Z"
    assert result.loc[0, "outcome_source_id"] == "tinvest_api"
