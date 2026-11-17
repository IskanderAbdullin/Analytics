"""Transparent regression baselines for IPO return forecasting."""

import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def fit_regression_baseline(
    train: pd.DataFrame,
    feature_columns: list[str],
    *,
    target_column: str = "target_return",
    model_kind: str = "ridge",
    random_state: int = 42,
):
    """Fit a median, Ridge, or Random Forest baseline on numeric features."""
    if not feature_columns:
        raise ValueError("At least one feature column must be specified")
    missing = set(feature_columns + [target_column]).difference(train.columns)
    if missing:
        raise ValueError(f"Training frame is missing columns: {sorted(missing)}")

    x_train = train[feature_columns].apply(pd.to_numeric, errors="coerce")
    y_train = pd.to_numeric(train[target_column], errors="coerce")
    valid = y_train.notna()
    x_train = x_train.loc[valid]
    y_train = y_train.loc[valid]
    if x_train.empty:
        raise ValueError("No valid training rows remain")

    if model_kind == "median":
        pipeline = Pipeline([("model", DummyRegressor(strategy="median"))])
    elif model_kind == "ridge":
        pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=10.0)),
            ]
        )
    elif model_kind == "random_forest":
        pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=400,
                        min_samples_leaf=3,
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    else:
        raise ValueError("model_kind must be median, ridge, or random_forest")

    pipeline.fit(x_train, y_train)
    return pipeline


def predict_returns(model, frame: pd.DataFrame, feature_columns: list[str]):
    missing = set(feature_columns).difference(frame.columns)
    if missing:
        raise ValueError(f"Prediction frame is missing columns: {sorted(missing)}")
    x = frame[feature_columns].apply(pd.to_numeric, errors="coerce")
    return model.predict(x)
