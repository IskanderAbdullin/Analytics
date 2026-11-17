import pandas as pd
import pytest

from ipo_forecast.data.validate import select_forecast_task
from ipo_forecast.models.baseline import fit_regression_baseline


def test_select_forecast_task_never_mixes_origins_or_horizons():
    frame = pd.DataFrame(
        {
            "forecast_id": ["a", "b", "c"],
            "forecast_origin": [
                "after_pricing_pre_open",
                "after_pricing_pre_open",
                "post_open",
            ],
            "target_horizon": ["day1_close", "day5_close", "day1_close"],
        }
    )
    selected = select_forecast_task(
        frame,
        forecast_origin="after_pricing_pre_open",
        target_horizon="day1_close",
    )
    assert selected["forecast_id"].tolist() == ["a"]


def test_empty_forecast_task_raises():
    frame = pd.DataFrame(
        {
            "forecast_id": ["a"],
            "forecast_origin": ["post_open"],
            "target_horizon": ["day1_close"],
        }
    )
    with pytest.raises(ValueError, match="No rows for forecast_origin"):
        select_forecast_task(
            frame,
            forecast_origin="after_pricing_pre_open",
            target_horizon="day1_close",
        )


def test_baseline_rejects_target_leakage_features():
    frame = pd.DataFrame(
        {"deal_size": [100, 200, 300], "target_return": [0.1, 0.2, 0.3]}
    )
    with pytest.raises(ValueError, match="not permitted"):
        fit_regression_baseline(frame, ["deal_size", "target_return"])
