"""Chronological splits that keep every IPO event in exactly one partition."""

import math

import pandas as pd


def chronological_event_split(
    frame: pd.DataFrame,
    *,
    group_column: str = "ipo_id",
    date_column: str = "listing_date",
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> dict[str, pd.DataFrame]:
    """Split by unique listing dates, preserving all rows for each IPO.

    All IPOs listing on the same date are assigned to the same partition.
    This is intentionally not a random split.
    """
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1")
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train_fraction + validation_fraction must be less than 1")
    if group_column not in frame or date_column not in frame:
        raise ValueError(f"Frame must contain {group_column!r} and {date_column!r}")
    if frame.empty:
        raise ValueError("Cannot split an empty dataset")

    events = frame[[group_column, date_column]].drop_duplicates()
    if events[group_column].isna().any() or events[date_column].isna().any():
        raise ValueError("IPO identifiers and listing dates must not be null")
    if events[group_column].duplicated().any():
        raise ValueError("Each IPO must map to exactly one listing date")

    events[date_column] = pd.to_datetime(events[date_column], errors="raise")
    unique_dates = sorted(events[date_column].unique())
    n_dates = len(unique_dates)
    if n_dates < 3:
        raise ValueError("At least three distinct listing dates are required")

    train_end = max(1, math.floor(n_dates * train_fraction))
    validation_end = max(
        train_end + 1, math.floor(n_dates * (train_fraction + validation_fraction))
    )
    validation_end = min(validation_end, n_dates - 1)

    train_dates = set(unique_dates[:train_end])
    validation_dates = set(unique_dates[train_end:validation_end])
    test_dates = set(unique_dates[validation_end:])

    date_by_ipo = events.set_index(group_column)[date_column]
    assignments = {
        "train": set(date_by_ipo[date_by_ipo.isin(train_dates)].index),
        "validation": set(date_by_ipo[date_by_ipo.isin(validation_dates)].index),
        "test": set(date_by_ipo[date_by_ipo.isin(test_dates)].index),
    }
    result = {
        name: frame.loc[frame[group_column].isin(ipo_ids)].copy()
        for name, ipo_ids in assignments.items()
    }
    if any(part.empty for part in result.values()):
        raise ValueError("Chronological split produced an empty partition; add more IPO dates")

    id_sets = [assignments[name] for name in ("train", "validation", "test")]
    if (id_sets[0] & id_sets[1]) or (id_sets[0] & id_sets[2]) or (id_sets[1] & id_sets[2]):
        raise RuntimeError("IPO event leakage detected between partitions")
    return result
