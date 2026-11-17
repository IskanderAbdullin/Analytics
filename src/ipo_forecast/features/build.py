"""Leakage-safe feature assembly from long-form observations."""

import pandas as pd

ORIGIN_COLUMNS = {"forecast_id", "ipo_id", "as_of_timestamp"}
OBSERVATION_COLUMNS = {"ipo_id", "feature_name", "value", "available_at"}


def build_point_in_time_features(
    forecast_origins: pd.DataFrame,
    observations: pd.DataFrame,
) -> pd.DataFrame:
    """Build a wide feature table using only observations available at each cut-off.

    For each forecast_id/feature_name pair, the latest observation with
    available_at <= as_of_timestamp is selected. Source provenance stays in
    the long-form observation table and should be retained with model outputs.
    """
    missing_origins = ORIGIN_COLUMNS.difference(forecast_origins.columns)
    missing_observations = OBSERVATION_COLUMNS.difference(observations.columns)
    if missing_origins:
        raise ValueError(f"Forecast origins missing columns: {sorted(missing_origins)}")
    if missing_observations:
        raise ValueError(f"Observations missing columns: {sorted(missing_observations)}")
    if forecast_origins["forecast_id"].isna().any():
        raise ValueError("forecast_id must not contain null values")
    if forecast_origins["forecast_id"].duplicated().any():
        raise ValueError("forecast_id must be unique in forecast_origins")
    if observations.empty:
        return forecast_origins.copy()

    origins = forecast_origins.copy()
    obs = observations.copy()
    origins["as_of_timestamp"] = pd.to_datetime(
        origins["as_of_timestamp"], errors="raise", utc=True
    )
    obs["available_at"] = pd.to_datetime(obs["available_at"], errors="raise", utc=True)

    if obs[["ipo_id", "feature_name", "available_at"]].isna().any().any():
        raise ValueError("Observation ipo_id, feature_name, and available_at are required")

    joined = origins[["forecast_id", "ipo_id", "as_of_timestamp"]].merge(
        obs, on="ipo_id", how="left", validate="one_to_many"
    )
    eligible = joined.loc[
        joined["available_at"].notna()
        & (joined["available_at"] <= joined["as_of_timestamp"])
    ].copy()

    if eligible.empty:
        return origins.copy()

    sort_columns = ["forecast_id", "feature_name", "available_at"]
    if "observation_id" in eligible.columns:
        sort_columns.append("observation_id")
    eligible = eligible.sort_values(sort_columns)
    latest = eligible.drop_duplicates(
        subset=["forecast_id", "feature_name"], keep="last"
    )

    wide = latest.pivot(index="forecast_id", columns="feature_name", values="value")
    wide.columns.name = None
    wide = wide.reset_index()
    return origins.merge(wide, on="forecast_id", how="left", validate="one_to_one")


def assemble_modeling_dataset(
    forecast_origins: pd.DataFrame,
    observations: pd.DataFrame,
    outcomes: pd.DataFrame,
) -> pd.DataFrame:
    """Join point-in-time features to realised labels by forecast_id."""
    if not {"forecast_id", "target_return"}.issubset(outcomes.columns):
        raise ValueError("Outcomes must contain forecast_id and target_return")
    if outcomes["forecast_id"].duplicated().any():
        raise ValueError("Outcomes must contain at most one row per forecast_id")

    features = build_point_in_time_features(forecast_origins, observations)
    return features.merge(
        outcomes[["forecast_id", "target_return"]],
        on="forecast_id",
        how="inner",
        validate="one_to_one",
    )
