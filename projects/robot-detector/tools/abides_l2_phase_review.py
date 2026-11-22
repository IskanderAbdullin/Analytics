#!/usr/bin/env python3
"""Offline review of an existing ABIDES public-L2 phase output; no market runs."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from abides_l2_binphase_sensitivity import aggregate, frozen_plan
from abides_l2_phase_fragility import evaluate_phase_fragility

MAX_INPUT_BYTES = 256_000
INPUT_SCHEMA = "abides-public-l2-clock-phase-v1"
REVIEW_SCHEMA = "abides-public-l2-paired-review-v1"


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"Duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"Nonstandard non-finite JSON number: {token}")


def parse_input(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("Frozen research JSON exceeds the bounded input size")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                          parse_constant=_reject_nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid UTF-8 research JSON") from exc
    if type(data) is not dict:
        raise ValueError("Expected one research JSON object")
    return data


def reanalyse_saved_result(data: dict[str, Any]) -> dict[str, Any]:
    """Recompute paired contrasts and verify internal summaries only.

    Self-reported source hashes cannot authenticate the simulator or feed.
    """
    if (type(data) is not dict or data.get("schema_version") != INPUT_SCHEMA
            or data.get("frozen_plan") != frozen_plan()):
        raise ValueError("Frozen clock-origin protocol does not match")
    for key, value in (
        ("actual_matching_engine_simulations", 4),
        ("non_independent_analytical_views", 12),
        ("private_truth_used", False),
        ("independent_provider_completeness_verified", False),
        ("real_market_accuracy_calibrated", False),
        ("physical_owner_count_known", False),
        ("live_trading_enabled", False),
    ):
        if type(data.get(key)) is not type(value) or data[key] != value:
            raise ValueError(f"Incorrect research provenance: {key}")
    calculated = aggregate(data.get("cases"))
    if data.get("cases") != calculated["cases"]:
        raise ValueError("Cases were not sorted in the original frozen order")
    if data.get("cohorts") != calculated["cohorts"]:
        raise ValueError("Original cohort summaries disagree with raw cases")
    if ("full_public_tape_digest_available_all_phases" in data and
            (type(data["full_public_tape_digest_available_all_phases"]) is not bool or
             data["full_public_tape_digest_available_all_phases"] !=
             calculated["full_public_tape_digest_available_all_phases"])):
        raise ValueError("Full book/print digest evidence disagrees with cases")
    old = data.get("per_simulation_sensitivity")
    if type(old) is not list or len(old) != 4:
        raise ValueError("Missing original per-simulation sensitivity")
    for recorded, recalculated in zip(old, calculated["per_simulation_sensitivity"]):
        if (type(recorded) is not dict or not recorded
                or any(key not in recalculated or recalculated[key] != value
                       for key, value in recorded.items())):
            raise ValueError("Original simulation sensitivity disagrees with cases")
    return {
        "schema_version": REVIEW_SCHEMA,
        "source_schema_version": INPUT_SCHEMA,
        "original_simulations_reported": 4,
        "correlated_phase_views_reported": 12,
        "additional_simulations_run": 0,
        "per_simulation_sensitivity": calculated["per_simulation_sensitivity"],
        "paired_cohort_contrasts": calculated["paired_cohort_contrasts"],
        "phase_fragility": evaluate_phase_fragility(calculated),
        "source_file_authenticity_verified": False,
        "source_completeness_independently_verified": False,
        "physical_agent_identified": False,
        "market_false_alarm_rate_estimated": False,
        "live_trading_enabled": False,
        "limitations": [
            "Input is a self-reported aggregate: SHA strings cannot authenticate source events.",
            "The same four original simulations underlie all twelve correlated views.",
            "Paired simulation-level rho contrasts can have different eligible clock bins.",
            "N=2 seeds per background cannot support real-market inference or phase selection.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    result = reanalyse_saved_result(parse_input(raw))
    result["input_file_sha256"] = sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(result, out, sort_keys=True, indent=2, allow_nan=False)
        out.write("\n")
    print("ABIDES_L2_PAIRED_REVIEW", json.dumps({
        "additional_simulations_run": 0,
        "paired_cohort_rows": len(result["paired_cohort_contrasts"]),
        "source_file_authenticity_verified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
