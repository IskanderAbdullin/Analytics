import pandas as pd

from ipo_forecast.validation.split import chronological_event_split


def test_split_is_chronological_and_keeps_ipo_rows_together():
    rows = []
    for day in range(1, 11):
        for origin in ("preliminary_filing", "after_pricing_pre_open"):
            rows.append(
                {
                    "ipo_id": f"ipo-{day}",
                    "listing_date": f"2020-01-{day:02d}",
                    "forecast_origin": origin,
                }
            )
    frame = pd.DataFrame(rows)

    splits = chronological_event_split(
        frame, train_fraction=0.6, validation_fraction=0.2
    )

    sets = [set(part["ipo_id"]) for part in splits.values()]
    assert not (sets[0] & sets[1])
    assert not (sets[0] & sets[2])
    assert not (sets[1] & sets[2])
    assert len(splits["train"]) == 12
    assert len(splits["validation"]) == 4
    assert len(splits["test"]) == 4

    max_train = pd.to_datetime(splits["train"]["listing_date"]).max()
    min_validation = pd.to_datetime(splits["validation"]["listing_date"]).min()
    max_validation = pd.to_datetime(splits["validation"]["listing_date"]).max()
    min_test = pd.to_datetime(splits["test"]["listing_date"]).min()
    assert max_train < min_validation <= max_validation < min_test
