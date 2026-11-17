import numpy as np
import pandas as pd
import pytest

from ipo_forecast.models.direction import (
    fit_direction_baseline,
    predict_positive_probability,
)


def _sample_frame():
    return pd.DataFrame(
        {
            "deal_size_usd": [10, 20, 30, 40, 50, 60, 70, 80],
            "revenue_growth_yoy": [0.1, 0.2, -0.1, 0.4, -0.2, 0.5, 0.1, 0.3],
            "target_return": [-0.2, 0.1, -0.05, 0.15, -0.3, 0.35, 0.01, -0.02],
        }
    )


@pytest.mark.parametrize("model_kind", ["logistic", "random_forest", "prior"])
def test_direction_classifier_produces_valid_probabilities(model_kind):
    frame = _sample_frame()
    features = ["deal_size_usd", "revenue_growth_yoy"]
    model = fit_direction_baseline(frame, features, model_kind=model_kind)
    probabilities = predict_positive_probability(model, frame, features)
    assert probabilities.shape == (len(frame),)
    assert np.isfinite(probabilities).all()
    assert (probabilities >= 0).all()
    assert (probabilities <= 1).all()


def test_direction_classifier_fails_closed_for_target_leakage():
    frame = _sample_frame()
    with pytest.raises(ValueError, match="not permitted"):
        fit_direction_baseline(frame, ["target_return"])


def test_direction_classifier_fails_on_one_class_training_cohort():
    frame = _sample_frame()
    frame["target_return"] = 0.1
    with pytest.raises(ValueError, match="both return directions"):
        fit_direction_baseline(frame, ["deal_size_usd"], model_kind="logistic")


def test_direction_prior_handles_one_class_without_probabilities_inverting():
    frame = _sample_frame()
    frame["target_return"] = -0.1
    model = fit_direction_baseline(frame, ["deal_size_usd"], model_kind="prior")
    probability = predict_positive_probability(model, frame, ["deal_size_usd"])
    assert np.array_equal(probability, np.zeros(len(frame)))
