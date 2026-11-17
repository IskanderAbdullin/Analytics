"""Dataset loading helpers."""

from pathlib import Path

import pandas as pd

from ipo_forecast.data.validate import validate_modeling_frame


def load_modeling_dataset(path: str | Path) -> pd.DataFrame:
    """Load and validate a CSV or Parquet modelling dataset."""
    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    suffix = dataset_path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(dataset_path)
    elif suffix in {".parquet", ".pq"}:
        frame = pd.read_parquet(dataset_path)
    else:
        raise ValueError("Supported dataset formats are CSV and Parquet")

    return validate_modeling_frame(frame)
