from pathlib import Path

from ipo_forecast.data.registry import load_source_registry


def test_repository_source_registry_is_well_formed():
    repository_root = Path(__file__).resolve().parents[1]
    registry = load_source_registry(repository_root / "data" / "source_registry.csv")
    assert not registry.empty
    assert registry["source_id"].is_unique
