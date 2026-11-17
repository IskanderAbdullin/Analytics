import pandas as pd
import pytest

from ipo_forecast.data.validate import validate_modeling_frame


def test_modeling_frame_requires_unique_forecast_ids():
    frame = pd.DataFrame(
        [
            {
                "forecast_id": "f1",
                "ipo_id": "ipo-1",
                "listing_date": "2024-01-02",
                "as_of_timestamp": "2024-01-01T12:00:00Z",
                "forecast_origin": "after_pricing_pre_open",
                "target_horizon": "day1_close",
                "target_return": 0.12,
            },
            {
                "forecast_id": "f1",
                "ipo_id": "ipo-1",
                "listing_date": "2024-01-02",
                "as_of_timestamp": "2024-01-01T12:00:00Z",
                "forecast_origin": "after_pricing_pre_open",
                "target_horizon": "day1_close",
                "target_return": 0.12,
            },
        ]
    )
    with pytest.raises(ValueError, match="forecast_id must be unique"):
        validate_modeling_frame(frame)


def test_modeling_frame_normalises_timestamps_and_target():
    frame = pd.DataFrame(
        [
            {
                "forecast_id": "f1",
                "ipo_id": "ipo-1",
                "listing_date": "2024-01-02",
                "as_of_timestamp": "2024-01-01T12:00:00Z",
                "forecast_origin": "after_pricing_pre_open",
                "target_horizon": "day1_close",
                "target_return": "0.12",
            }
        ]
    )
    result = validate_modeling_frame(frame)
    assert result.loc[0, "target_return"] == pytest.approx(0.12)
    assert str(result.loc[0, "as_of_timestamp"].tz) == "UTC"
