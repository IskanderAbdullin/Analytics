"""Source registry validation."""

from pathlib import Path

import pandas as pd

REQUIRED_SOURCE_COLUMNS = {
    "source_id",
    "publisher",
    "source_name",
    "source_url",
    "source_type",
    "access_method",
}


def load_source_registry(path: str | Path) -> pd.DataFrame:
    registry = pd.read_csv(path)
    missing = REQUIRED_SOURCE_COLUMNS.difference(registry.columns)
    if missing:
        raise ValueError(f"Source registry is missing columns: {sorted(missing)}")
    if registry.empty:
        return registry
    if registry["source_id"].isna().any() or registry["source_id"].duplicated().any():
        raise ValueError("source_id must be present and unique")
    if registry[list(REQUIRED_SOURCE_COLUMNS)].isna().any().any():
        raise ValueError("Required source registry fields must not be null")
    return registry
