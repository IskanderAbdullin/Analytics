#!/usr/bin/env python3
"""Frozen 30s public-L2 clock *origin* sensitivity on genuine ABIDES tapes.

Four actual matching-engine public tapes are re-binned at 0/10/20-second
clock offsets. These twelve views are correlated and are NOT independent
market replications, actor attribution or a real-market accuracy estimate.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import statistics
from types import SimpleNamespace
from typing import Any

from abides_export import UPSTREAM_COMMIT
from l2_trade_context import public_projection
from lagged_l2_bin import summarize_lagged_book
from public_numeric import exact_nonnegative_integer as exact_int

SEEDS = (2101, 2102)
BACKGROUNDS = ("poisson", "fixed_cadence")
PHASES_SECONDS = (0, 10, 20)
BIN_SECONDS = 30
DEPTH = 5
START = "09:30:00"
END = "09:42:00"


def frozen_plan() -> dict[str, Any]:
    return {
        "schema_version": "abides-public-l2-clock-phase-v1",
        "simulator_revision": UPSTREAM_COMMIT,
        "seeds": list(SEEDS),
        "backgrounds": list(BACKGROUNDS),
        "phases_seconds": list(PHASES_SECONDS),
        "bin_width_seconds": BIN_SECONDS,
        "session": [START, END],
        "book_depth": DEPTH,
        "agents": "60 NoiseAgents, 20-second re-wake: Poisson or fixed cadence",
        "actual_simulations": 4,
        "analytic_views_of_same_public_tape": 12,
        "source_completion_attested": False,
        "public_features_only": True,
        "no_physical_owner_identification": True,
        "no_model_selection_or_best_phase": True,
        "no_real_market_calibration": True,
    }


def shift_public_clock(snapshots: Any, public: tuple, phase_seconds: int):
    if phase_seconds not in PHASES_SECONDS:
        raise ValueError("Only source-predeclared clock phases allowed")
    shift = phase_seconds * 1_000_000_000
    if any(exact_int(x, "L2 time ns") < shift for x in snapshots.times_ns) or any(
        x.time_ns < shift for x in public
    ):
        raise ValueError("Insufficient absolute source time to shift public clock")
    # Both series are shifted by the same constant, preserving all prices,
    # quantities, side labels, event differences and within-timestamp ties.
    shifted = SimpleNamespace(
        times_ns=[exact_int(t, "L2 time ns") - shift for t in snapshots.times_ns],
        bids=snapshots.bids,
        asks=snapshots.asks)
    shifted_prints = tuple(replace(p, time_ns=p.time_ns - shift) for p in public)
    return shifted, shifted_prints


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {
        (s, mode, phase)
        for s in SEEDS for mode in BACKGROUNDS for phase in PHASES_SECONDS
    }
    got = [(r["seed"], r["background"], r["phase_seconds"]) for r in rows]
    if len(got) != len(expected) or set(got) != expected:
        raise ValueError("Missing, duplicate or modified frozen phase matrix")
    groups: dict[tuple[int, str], list[dict]] = {}
    for row in rows:
        if (row["public_prints"] <= 0 or row["public_lots"] <= 0
            or row["l2_snapshots"] <= 0
            or row["eligible_lagged_bins"] < 0
            or row["eligible_lagged_bins"] > row["populated_trade_bins"]
            or row["eligible_lagged_bins"] + row["abstained_bins"] != row["populated_trade_bins"]
            or row["claimed_real_feed_completeness"]
            or row["private_identity_accessed"] or row["model_selected"]):
            raise ValueError("Public phase case violated source/research contract")
        rho = row["descriptive_rho"]
        if rho is not None and not (-1 <= rho <= 1):
            raise ValueError("Invalid rho")
        groups.setdefault((row["seed"], row["background"]), []).append(row)
    for key, group in groups.items():
        if (len(group) != len(PHASES_SECONDS)
            or len({x["public_sha256"] for x in group}) != 1
            or len({x["public_prints"] for x in group}) != 1
            or len({x["public_lots"] for x in group}) != 1
            or len({x["l2_snapshots"] for x in group}) != 1):
            raise ValueError("Clock phase study did not reuse identical public tape")
    cohorts = []
    for mode in BACKGROUNDS:
        for phase in PHASES_SECONDS:
            matches = [r for r in rows
                       if r["background"] == mode and r["phase_seconds"] == phase]
            present = [r["descriptive_rho"] for r in matches
                       if r["descriptive_rho"] is not None]
            cohorts.append({
                "background": mode, "phase_seconds": phase,
                "simulations": len(matches),
                "eligible_lagged_bins": sum(x["eligible_lagged_bins"] for x in matches),
                "defined_correlation_simulations": len(present),
                "median_descriptive_rho": statistics.median(present) if present else None,
                "real_market_false_alarm_rate": None,
            })
    sensitivity = []
    for seed in SEEDS:
        for mode in BACKGROUNDS:
            group = groups[(seed, mode)]
            present = [x["descriptive_rho"] for x in group
                       if x["descriptive_rho"] is not None]
            sensitivity.append({
                "seed": seed, "background": mode, "phases_analysed": len(group),
                "defined_correlations": len(present),
                "rho_range": (max(present)-min(present) if len(present)>=2 else None),
                "source_public_tape_is_identical_across_phases": True,
                "independent_evaluations_across_phases": False,
            })
    return {
        "schema_version": "abides-public-l2-clock-phase-v1",
        "frozen_plan": frozen_plan(),
        "cases": sorted(rows,key=lambda x:(x["seed"],x["background"],x["phase_seconds"])),
        "cohorts": cohorts,
        "per_simulation_sensitivity": sensitivity,
        "actual_matching_engine_simulations": len(groups),
        "non_independent_analytical_views": len(rows),
        "private_truth_used": False,
        "independent_provider_completeness_verified": False,
        "real_market_accuracy_calibrated": False,
        "physical_owner_count_known": False,
        "live_trading_enabled": False,
        "limitations": [
            "Origin offsets re-bin exactly the SAME anonymous simulated exchange tape.",
            "No best phase is selected; widths and phase offsets fixed before evaluation.",
            "Two seeds per background cannot estimate market specificity or p-values.",
            "Source-completeness watermark not independently verified.",
            "Controlled VWAP/POV parent agents absent but background algorithms present.",
            "No physical maker/taker owner or parent order can be inferred from rho.",
        ],
    }


def run_case(seed: int, mode: str) -> list[dict[str, Any]]:
    if seed not in SEEDS or mode not in BACKGROUNDS:
        raise ValueError("Frozen study forbids replacing seed/background")
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import NoiseAgentConfig
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile, run_simulation

    builder = (
        SimulationBuilder().apply_template("liquid_market").ticker("ABM")
        .start_time(START).end_time(END)
        .exchange(ExchangeConfig(book_capture="l2",book_log_depth=DEPTH))
        .enable_agent(NoiseAgentConfig(
            multi_wake=True,wake_up_freq="20s",poisson_arrival=(mode=="poisson"),
            noise_mkt_close_time=END),count=60).seed(seed)
    )
    result = run_simulation(builder.build(),profile=ResultProfile.QUANT)
    if any(str(a.agent_name).startswith(
        ("TWAP_EXECUTION_AGENT_","VWAP_EXECUTION_AGENT_","POV_EXECUTION_AGENT_")
    ) for a in result.agents):
        raise RuntimeError("Frozen background unexpectedly contained named execution agent")
    market = result.markets["ABM"]
    if market.l2_series is None or not market.trades:
        raise RuntimeError("Actual matching engine did not produce public L2 and prints")
    public = public_projection(market.trades)
    h = sha256()
    for p in public:
        h.update(f"{p.time_ns}|{p.price_cents}|{p.quantity}|{p.reported_aggressor_side}\n".encode())
    source_digest=h.hexdigest()
    rows = []
    for phase in PHASES_SECONDS:
        shifted_book, shifted_prints = shift_public_clock(market.l2_series,public,phase)
        rep = summarize_lagged_book(
            shifted_book,shifted_prints,bin_seconds=BIN_SECONDS,
            maximum_quote_age_seconds=BIN_SECONDS,maximum_depth=DEPTH)
        if (rep["archive_completion_watermark_supplied"]
            or rep["stream_coverage_independently_verified"]
            or rep["private_agent_identifiers_used"]
            or rep["individual_robot_detected"]):
            raise RuntimeError("Public-only unverified source contract breached")
        rows.append({
            "seed":seed, "background":mode, "phase_seconds":phase,
            "public_sha256":source_digest,
            "public_prints":rep["public_execution_prints"],
            "public_lots":rep["public_execution_lots"],
            "l2_snapshots":rep["source_l2_snapshot_count"],
            "eligible_lagged_bins":rep["eligible_lagged_bins"],
            "populated_trade_bins":rep["populated_execution_clock_bins"],
            "abstained_bins":sum(rep["abstained_clock_bins"].values()),
            "descriptive_rho":rep["descriptive_lagged_imbalance_to_next_buy_share_spearman"],
            "claimed_real_feed_completeness":False,
            "private_identity_accessed":False,
            "model_selected":False,
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Do not overwrite earlier study output")
    rows=[]
    for seed in SEEDS:
        for mode in BACKGROUNDS:
            rows.extend(run_case(seed,mode))
    summary=aggregate(rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(summary,f,indent=2,sort_keys=True)
        f.write("\n")
    for item in summary["cohorts"]:
        print("ABIDES_L2_PHASE_SENSITIVITY",json.dumps(item,sort_keys=True))
    print("ABIDES_L2_PHASE_DONE",json.dumps({
        "matching_engine_runs":summary["actual_matching_engine_simulations"],
        "correlated_views":summary["non_independent_analytical_views"],
        "calibrated":False
    }))


if __name__=="__main__":
    main()
