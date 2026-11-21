#!/usr/bin/env python3
"""Pre-registered synthetic replication of the public-only shift monitor.

Fixed ABIDES seeds and unchanged exploratory parameters. This is NOT a
real-exchange specificity or physical metaorder-identification experiment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from directional_shift_dev_survey import run

FROZEN_REPLICATION_SEEDS = (1101, 1102, 1103, 1104)
LOCKED_PARAMETERS = {
    "bin_seconds": 30,
    "reference_bins": 6,
    "minimum_absolute_buy_share_change": 0.25,
    "minimum_known_side_fraction": 0.9,
    "cooldown_bins": 2,
    "minimum_current_known_lots": 100,
    "minimum_reference_known_lots": 500,
}
ALLOWED_MODES = ("null", "vwap", "pov")


def preregister(seeds: list[int]) -> dict:
    if tuple(seeds) != FROZEN_REPLICATION_SEEDS:
        raise ValueError("Replication seeds and order must remain exactly pre-registered")
    return {
        "design": "synthetic-public-directional-shift-unmodified-v1",
        "seeds": seeds,
        "modes": list(ALLOWED_MODES),
        "parameters": dict(LOCKED_PARAMETERS),
        "private_truth_access": False,
        "market_false_alarm_calibrated": False,
        "physical_owner_count_known": False,
        "allowed_conclusion": "descriptive observed public-bin contrasts only",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli-dll", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite a previous synthetic replication")
    plan = preregister(list(FROZEN_REPLICATION_SEEDS))
    result = run(list(FROZEN_REPLICATION_SEEDS), args.cli_dll)
    result["cohort_type"] = "pre_registered_synthetic_replication"
    result["pre_registered_plan"] = plan
    assert result["development_seeds"] == list(FROZEN_REPLICATION_SEEDS)
    assert result["private_truth_used_for_detection"] is False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    for row in result["cohorts"]:
        print("ABIDES_DIRECTIONAL_SHIFT_FROZEN", json.dumps(row, sort_keys=True))
    print("ABIDES_DIRECTIONAL_SHIFT_FROZEN_DONE",
          json.dumps({"seeds": plan["seeds"], "cases": len(result["cases"]),
                      "physical_owner_count_known": False}))


if __name__ == "__main__":
    main()
