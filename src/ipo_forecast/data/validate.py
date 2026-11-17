"""Validation and task selection for the assembled modelling table."""

import numpy as np
import pandas as pd

REQUIRED_MODEL_COLUMNS = {
    "forecast_id",
    "ipo_id",
    "listing_date",
    "as_of_timestamp",
    "forecast_origin",
    "target_horizon",
    "target_return",
}


def validate_modeling_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate required metadata and target fields; return a defensive copy."""
    if frame.empty:
        raise ValueError("The modelling dataset is empty")

    missing = REQUIRED_MODEL_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required modelling columns: {sorted(missing)}")

    result = frame.copy()
    if result["forecast_id"].isna().any() or result["ipo_id"].isna().any():
        raise ValueError("forecast_id and ipo_id must not contain null values")
    if result["forecast_id"].duplicated().any():
        raise ValueError("forecast_id must be unique in the modelling dataset")

    parsed_dates = pd.to_datetime(result["listing_date"], errors="coerce")
    if parsed_dates.isna().any():
        raise ValueError("listing_date contains invalid or missing dates")
    result["listing_date"] = parsed_dates.dt.date

    parsed_timestamps = pd.to_datetime(
        result["as_of_timestamp"], errors="coerce", utc=True
    )
    if parsed_timestamps.isna().any():
        raise ValueError("as_of_timestamp contains invalid or missing timestamps")
    result["as_of_timestamp"] = parsed_timestamps

    if result[["forecast_origin", "target_horizon"]].isna().any().any():
        raise ValueError("forecast_origin and target_horizon must not be null")

    target = pd.to_numeric(result["target_return"], errors="coerce")
    if target.isna().any() or not np.isfinite(target.to_numpy(dtype=float)).all():
        raise ValueError("target_return must contain finite numeric values")
    result["target_return"] = target.astype(float)

    return result


def select_forecast_task(
    frame: pd.DataFrame,
    *,
    forecast_origin: str,
    target_horizon: str,
) -> pd.DataFrame:
    """Select exactly one forecast origin and target horizon."""
    selected = frame.loc[
        (frame["forecast_origin"] == forecast_origin)
        & (frame["target_horizon"] == target_horizon)
    ].copy()
    if selected.empty:
        raise ValueError(
            f"No rows for forecast_origin={forecast_origin!r}, "
            f"target_horizon={target_horizon!r}"
        )
    return selected
