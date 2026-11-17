import pandas as pd

from ipo_forecast.features.build import build_point_in_time_features


def test_future_observations_are_excluded_and_latest_available_is_selected():
    origins = pd.DataFrame(
        [
            {
                "forecast_id": "f1",
                "ipo_id": "ipo-1",
                "as_of_timestamp": "2026-11-17T10:00:00Z",
                "forecast_origin": "after_pricing_pre_open",
            }
        ]
    )
    observations = pd.DataFrame(
        [
            {
                "observation_id": "o1",
                "ipo_id": "ipo-1",
                "feature_name": "news_score",
                "value": 0.2,
                "available_at": "2026-11-17T08:00:00Z",
            },
            {
                "observation_id": "o2",
                "ipo_id": "ipo-1",
                "feature_name": "news_score",
                "value": 0.4,
                "available_at": "2026-11-17T09:30:00Z",
            },
            {
                "observation_id": "o3",
                "ipo_id": "ipo-1",
                "feature_name": "news_score",
                "value": 0.9,
                "available_at": "2026-11-17T10:30:00Z",
            },
        ]
    )

    result = build_point_in_time_features(origins, observations)

    assert len(result) == 1
    assert result.loc[0, "news_score"] == 0.4
