#!/usr/bin/env python3
"""Frozen bin-width sensitivity of public-only previous-L2/next-trades rho.

Actual ABIDES matching runs ONCE per seed/background; the same public tape
is summarized at three prespecified clock widths. No one agent is identified.
This is descriptive robustness, not cross-width replication, calibration or
market prediction. No prior seeds are used for threshold selection.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import statistics
from typing import Any

from abides_export import UPSTREAM_COMMIT
from l2_trade_context import public_projection
from lagged_l2_bin import summarize_lagged_book

SEEDS = (1901, 1902)
BACKGROUNDS = ("poisson", "fixed_cadence")
BIN_WIDTHS_SECONDS = (10, 30, 60)
RUN_START = "09:30:00"
RUN_END = "09:42:00"
DEPTH = 5


def frozen_plan() -> dict[str, Any]:
    return {
        "schema_version": "abides-public-l2-binwidth-robustness-v1",
        "simulator_revision": UPSTREAM_COMMIT,
        "development_seeds": list(SEEDS),
        "backgrounds": list(BACKGROUNDS),
        "widths_seconds": list(BIN_WIDTHS_SECONDS),
        "session": [RUN_START, RUN_END],
        "book_depth": DEPTH,
        "agents": "60 NoiseAgents, 20s inter-wake, mode-dependent Poisson vs fixed",
        "one_market_simulation_per_seed_background": True,
        "current_bin_outcome_is_ex_post": True,
        "source_archive_coverage_attested": False,
        "private_truth_used_for_feature": False,
        "named_execution_program_added": False,
        "detector_threshold_fitted": False,
        "real_market_significance_established": False,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {
        (seed, mode, width)
        for seed in SEEDS for mode in BACKGROUNDS for width in BIN_WIDTHS_SECONDS
    }
    got = [(r["seed"], r["background"], r["bin_seconds"]) for r in rows]
    if len(got) != len(expected) or set(got) != expected:
        raise ValueError("Incomplete/duplicated/modified frozen case matrix")
    grouped: dict[tuple[int, str], list[dict]] = {}
    for row in rows:
        if (row["public_executed_prints"] <= 0 or row["public_execution_lots"] <= 0
            or row["public_l2_snapshots"] <= 0
            or row["eligible_lagged_bins"] < 0
            or row["eligible_lagged_bins"] > row["populated_public_trade_bins"]
            or row["private_agent_identified"] or row["market_significance_calibrated"]
            or row["source_completion_verified"] or row["threshold_selected"]):
            raise ValueError("Untrustworthy public case")
        if row["eligible_lagged_bins"] + row["abstained_lagged_bins"] != row["populated_public_trade_bins"]:
            raise ValueError("Each populated trade bin must be accounted for")
        rho = row["lagged_spearman"]
        if rho is not None and not (-1.0 <= rho <= 1.0):
            raise ValueError("Invalid public rank correlation")
        grouped.setdefault((row["seed"], row["background"]), []).append(row)
    for key, group in grouped.items():
        if (len(group) != 3 or len({x["public_sha256"] for x in group}) != 1 or
            len({x["public_executed_prints"] for x in group}) != 1 or
            len({x["public_execution_lots"] for x in group}) != 1 or
            len({x["public_l2_snapshots"] for x in group}) != 1):
            raise ValueError("Not the same public tape re-analyzed at fixed widths")

    sensitivity = []
    for seed in SEEDS:
        for mode in BACKGROUNDS:
            group = grouped[(seed, mode)]
            defined = [r["lagged_spearman"] for r in group if r["lagged_spearman"] is not None]
            sensitivity.append({
                "seed": seed,
                "background": mode,
                "evaluated_widths": len(group),
                "widths_with_defined_rho": len(defined),
                "minimum_rho_across_widths": min(defined) if defined else None,
                "maximum_rho_across_widths": max(defined) if defined else None,
                "rho_span_across_widths":
                    max(defined) - min(defined) if len(defined) > 1 else None,
                "all_widths_use_same_public_tape": True,
                "independent_validation_across_widths": False,
            })
    cohorts = []
    for mode in BACKGROUNDS:
        for width in BIN_WIDTHS_SECONDS:
            matches = [
                r for r in rows if r["background"] == mode and r["bin_seconds"] == width
            ]
            vals = [r["lagged_spearman"] for r in matches
                    if r["lagged_spearman"] is not None]
            cohorts.append({
                "background": mode, "bin_seconds": width, "simulations": len(matches),
                "eligible_lagged_bins": sum(r["eligible_lagged_bins"] for r in matches),
                "defined_rho_simulations": len(vals),
                "median_descriptive_rho": statistics.median(vals) if vals else None,
                "market_false_discovery_rate": None,
                "physical_owner_count_known": False
            })
    return {
        "schema_version": "abides-public-l2-binwidth-robustness-v1",
        "frozen_plan": frozen_plan(),
        "cases": sorted(rows, key=lambda r: (r["seed"], r["background"], r["bin_seconds"])),
        "per_simulation_sensitivity": sensitivity,
        "cohorts": cohorts,
        "actual_matching_engine_simulations": len(grouped),
        "independent_simulations_across_widths": False,
        "private_truth_exported": False,
        "model_threshold_selected": False,
        "real_market_calibration_known": False,
        "individual_bot_identified": False,
        "trading_enabled": False,
        "limitations": [
            "Three widths re-use the SAME generated public tape; not independent samples.",
            "No externally verified completeness watermark in simulated archives.",
            "N=2 seeds per background: no inferential stability or FDR estimate.",
            "Changing bin width changes the effective historical public statistic.",
            "No named TWAP/VWAP/POV execution agent was injected; other simulated agents "
            "still follow algorithms. No private parent-order attribution.",
            "All seeds become spent after this exploratory experiment."
        ]
    }


def run_case(seed: int, background: str) -> list[dict[str, Any]]:
    if seed not in SEEDS or background not in BACKGROUNDS:
        raise ValueError("Cannot change frozen design")
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import NoiseAgentConfig
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile, run_simulation

    builder = (
        SimulationBuilder().apply_template("liquid_market").ticker("ABM")
        .start_time(RUN_START).end_time(RUN_END)
        .exchange(ExchangeConfig(book_capture="l2", book_log_depth=DEPTH))
        .enable_agent(NoiseAgentConfig(
            multi_wake=True, wake_up_freq="20s",
            poisson_arrival=(background == "poisson"),
            noise_mkt_close_time=RUN_END), count=60)
        .seed(seed)
    )
    simulation = run_simulation(builder.build(), profile=ResultProfile.QUANT)
    if any(str(a.agent_name).startswith(
        ("TWAP_EXECUTION_AGENT_", "VWAP_EXECUTION_AGENT_", "POV_EXECUTION_AGENT_")
    ) for a in simulation.agents):
        raise RuntimeError("Named execution program unexpectedly present")
    market = simulation.markets["ABM"]
    if market.l2_series is None or not market.trades:
        raise RuntimeError("Genuine ABIDES public book/fill output unavailable")
    public = public_projection(market.trades)
    h = sha256()
    for p in public:
        h.update(
            f"{p.time_ns}|{p.price_cents}|{p.quantity}|{p.reported_aggressor_side}\n".encode()
        )
    public_digest = h.hexdigest()
    rows = []
    for width in BIN_WIDTHS_SECONDS:
        report = summarize_lagged_book(
            market.l2_series, public,
            bin_seconds=width,
            maximum_quote_age_seconds=width,
            maximum_depth=DEPTH
        )
        if (
            report["source_l2_snapshot_count"] <= 0
            or report["public_execution_prints"] != len(public)
            or report["archive_completion_watermark_supplied"]
            or report["completion_watermark_independently_verified"]
            or report["private_agent_identifiers_used"]
            or report["individual_robot_detected"]
        ):
            raise ValueError("Public feature violated unverified source bounds")
        rows.append({
            "seed": seed, "background": background, "bin_seconds": width,
            "public_sha256": public_digest,
            "public_executed_prints": len(public),
            "public_execution_lots": report["public_execution_lots"],
            "public_l2_snapshots": report["source_l2_snapshot_count"],
            "populated_public_trade_bins": report["populated_execution_clock_bins"],
            "eligible_lagged_bins": report["eligible_lagged_bins"],
            "abstained_lagged_bins": sum(report["abstained_clock_bins"].values()),
            "lagged_spearman":
                report["descriptive_lagged_imbalance_to_next_buy_share_spearman"],
            "private_agent_identified": False,
            "market_significance_calibrated": False,
            "source_completion_verified": False,
            "threshold_selected": False,
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Cannot overwrite research results")
    rows = []
    for seed in SEEDS:
        for mode in BACKGROUNDS:
            rows.extend(run_case(seed, mode))
    result = aggregate(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2, sort_keys=True)
        out.write("\n")
    for row in result["cohorts"]:
        print("ABIDES_L2_BIN_WIDTH_SENSITIVITY", json.dumps(row, sort_keys=True))
    print("ABIDES_L2_BIN_WIDTH_DONE", json.dumps({
        "matching_runs": result["actual_matching_engine_simulations"],
        "analytical_cases": len(result["cases"]),
        "independent_width_samples": False
    }))


if __name__ == "__main__":
    main()
