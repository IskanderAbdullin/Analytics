"""Prevent training on IPO outcomes that were not yet known at forecast time."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd


def purge_unmatured_training_labels(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    *,
    outcome_timestamp_column: str = "target_timestamp",
    forecast_timestamp_column: str = "as_of_timestamp",
    embargo_days: int = 0,
) -> tuple[pd.DataFrame, dict[str, int | str]]:
    """Remove training rows with outcomes unavailable by first validation forecast.

    This is a minimum safeguard against overlapping long-horizon labels. It does
    not replace a full walk-forward refit on later validation/test periods.
    """
    if embargo_days < 0:
        raise ValueError("embargo_days must not be negative")
    for frame, name in ((train, "train"), (validation, "validation")):
        if frame.empty:
            raise ValueError(f"{name} split is empty")
        if forecast_timestamp_column not in frame:
            raise ValueError(
                f"{name} is missing required {forecast_timestamp_column}"
            )
    if outcome_timestamp_column not in train:
        raise ValueError(
            "Cannot establish label maturity: training dataset is missing "
            f"{outcome_timestamp_column}. Provide observed target timestamps "
            "from the outcome source."
        )

    cutoff = pd.to_datetime(
        validation[forecast_timestamp_column], errors="coerce", utc=True
    )
    if cutoff.isna().any():
        raise ValueError("validation forecast timestamps are invalid")
    earliest_validation = cutoff.min()
    boundary = earliest_validation - timedelta(days=embargo_days)
    label_times = pd.to_datetime(
        train[outcome_timestamp_column], errors="coerce", utc=True
    )
    if label_times.isna().any():
        raise ValueError("training outcome timestamps are invalid or missing")

    keep = label_times < boundary
    purged = train.loc[keep].copy()
    if purged.empty:
        raise ValueError(
            "No training labels had matured by the first validation forecast "
            "timestamp. Reduce the horizon or add older IPOs."
        )
    report = {
        "input_training_rows": int(len(train)),
        "eligible_training_rows": int(len(purged)),
        "purged_unmatured_rows": int((~keep).sum()),
        "first_validation_forecast_at": earliest_validation.isoformat(),
        "training_label_cutoff": boundary.isoformat(),
    }
    return purged, report
