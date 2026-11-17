import pandas as pd

from ipo_forecast.models.baseline import fit_regression_baseline, predict_returns


def test_ridge_baseline_fits_and_predicts():
    frame = pd.DataFrame(
        {
            "deal_size_usd": [100, 120, 140, 160, 180, 200],
            "revenue_growth": [0.1, 0.2, 0.15, 0.3, 0.25, 0.35],
            "target_return": [0.02, 0.04, 0.01, 0.08, 0.06, 0.10],
        }
    )
    model = fit_regression_baseline(
        frame, ["deal_size_usd", "revenue_growth"], model_kind="ridge"
    )
    predictions = predict_returns(model, frame, ["deal_size_usd", "revenue_growth"])
    assert len(predictions) == len(frame)
    assert all(pd.notna(value) for value in predictions)
