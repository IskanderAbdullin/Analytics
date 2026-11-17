import pytest

from ipo_forecast.evaluation.metrics import probability_metrics, regression_metrics


def test_regression_metrics():
    result = regression_metrics([0.1, -0.1, 0.2], [0.0, -0.2, 0.1])
    assert result["mae"] == pytest.approx(0.1)
    assert result["directional_accuracy"] == pytest.approx(1.0)


def test_probability_metrics():
    result = probability_metrics([0, 1, 1, 0], [0.1, 0.8, 0.7, 0.2])
    assert result["brier_score"] < 0.1
    assert result["roc_auc"] == pytest.approx(1.0)
