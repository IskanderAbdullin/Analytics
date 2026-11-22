#!/usr/bin/env python3
"""Produce aggregate-only 64-replicate constructed timing-null comparison.

Research diagnostic only: no market samples, target labels, significance,
exchangeability proof, physical owner identities, or real-market FDR.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests_background"))
from test_public_abc_constructed_controls import (  # noqa: E402
    REPLICATES, SEED, constructed_controls, descriptive_panel,
)


def build_report() -> dict:
    panel = descriptive_panel()
    controls = constructed_controls()
    return {
        "schema_version": "rd-public-abc-constructed-v1",
        "source_kind": "constructed_source_free_negative_controls_only",
        "protocol": "docs/INTENSITY_CONDITIONED_NULL_PREREG_20261122.md",
        "randomization_seed": SEED,
        "randomization_replicates_per_model": REPLICATES,
        "independent_market_or_abides_source_runs": 0,
        "metric": "within_5s_cell_adjacent_unique_exchange_timestamp_gaps_le_10ms",
        "calibrated_p_values": False,
        "real_market_fdr_known": False,
        "physical_owners_identifiable": False,
        "scenarios": {
            name: {"public_print_count": len(controls[name]),
                   "unique_timestamp_count": len(set(controls[name])), **row}
            for name, row in panel.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Small aggregate-only JSON result")
    args = parser.parse_args()
    payload = json.dumps(build_report(), sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print("ABC_CONSTRUCTED_REPORT_CREATED", str(args.output))
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
