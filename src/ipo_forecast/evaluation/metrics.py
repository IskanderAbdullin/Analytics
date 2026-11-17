"""Regression and binary probability metrics."""

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)


def regression_metrics(actual, predicted) -> dict[str, float | None]:
    y_true = np.asarray(actual, dtype=float)
    y_pred = np.asarray(predicted, dtype=float)
    if y_true.shape != y_pred.shape or y_true.size == 0:
        raise ValueError("actual and predicted must be non-empty arrays of equal shape")
    if not np.isfinite(y_true).all() or not np.isfinite(y_pred).all():
        raise ValueError("actual and predicted must contain only finite values")

    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "directional_accuracy": float(accuracy_score(y_true >= 0, y_pred >= 0)),
        "r2": float(r2_score(y_true, y_pred)) if y_true.size > 1 else None,
    }


def probability_metrics(actual_binary, probability_positive) -> dict[str, float | None]:
    y_true = np.asarray(actual_binary, dtype=int)
    probabilities = np.asarray(probability_positive, dtype=float)
    if y_true.shape != probabilities.shape or y_true.size == 0:
        raise ValueError("actual and probabilities must be non-empty arrays of equal shape")
    if not np.isin(y_true, [0, 1]).all():
        raise ValueError("actual_binary must contain only 0 and 1")
    if not np.isfinite(probabilities).all() or (
        (probabilities < 0) | (probabilities > 1)
    ).any():
        raise ValueError("Probabilities must be finite values between 0 and 1")

    return {
        "brier_score": float(brier_score_loss(y_true, probabilities)),
        "log_loss": float(log_loss(y_true, probabilities, labels=[0, 1])),
        "roc_auc": (
            float(roc_auc_score(y_true, probabilities))
            if np.unique(y_true).size == 2
            else None
        ),
    }
