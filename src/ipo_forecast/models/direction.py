"""IPO positive-return classification baselines with honest probability outputs."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ipo_forecast.models.baseline import FORBIDDEN_FEATURE_NAMES


def _check_features(
    frame: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
) -> None:
    if not feature_columns:
        raise ValueError("At least one feature column must be specified")
    forbidden = {
        name
        for name in feature_columns
        if name in FORBIDDEN_FEATURE_NAMES
        or name == target_column
        or name.startswith(("target_", "actual_", "realized_", "outcome_"))
    }
    if forbidden:
        raise ValueError(f"Outcome/target features are not permitted: {sorted(forbidden)}")
    missing = set(feature_columns + [target_column]).difference(frame.columns)
    if missing:
        raise ValueError(f"Missing training columns: {sorted(missing)}")


def fit_direction_baseline(
    train: pd.DataFrame,
    feature_columns: list[str],
    *,
    target_column: str = "target_return",
    model_kind: str = "logistic",
    random_state: int = 42,
):
    """Fit a direction classifier to positive (>0) IPO returns."""
    _check_features(train, feature_columns, target_column)
    x = train[feature_columns].apply(pd.to_numeric, errors="coerce")
    target = pd.to_numeric(train[target_column], errors="coerce")
    if target.isna().any() or not np.isfinite(target.to_numpy(dtype=float)).all():
        raise ValueError("Training targets must be finite numbers")
    y = (target > 0).astype(int)
    if model_kind not in {"prior", "logistic", "random_forest"}:
        raise ValueError("Model must be prior, logistic or random_forest")
    if model_kind != "prior" and y.nunique() < 2:
        raise ValueError("A classifier needs examples of both return directions")

    if model_kind == "prior":
        pipeline = Pipeline([("classifier", DummyClassifier(strategy="prior"))])
    elif model_kind == "logistic":
        pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                ("scaler", StandardScaler()),
                ("classifier", LogisticRegression(max_iter=2000, random_state=random_state)),
            ]
        )
    else:
        pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=400,
                        min_samples_leaf=3,
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    pipeline.fit(x, y)
    return pipeline


def predict_positive_probability(
    model,
    frame: pd.DataFrame,
    feature_columns: list[str],
) -> np.ndarray:
    """Return the model's positive-class probability, including one-class prior."""
    missing = set(feature_columns).difference(frame.columns)
    if missing:
        raise ValueError(f"Missing prediction columns: {sorted(missing)}")
    x = frame[feature_columns].apply(pd.to_numeric, errors="coerce")
    probability = model.predict_proba(x)
    classes = model.classes_
    if len(classes) == 1:
        return np.full(len(frame), float(classes[0]))
    idx = list(classes).index(1)
    return probability[:, idx]
