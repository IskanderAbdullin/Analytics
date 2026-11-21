#!/usr/bin/env python3
"""Genuine ABIDES-NG *background-only* L2/flow null-family study.

All cohorts intentionally omit TWAP, VWAP and POV execution-program agents.
The heterogeneous cohort adds public-market momentum agents; this is NOT a
claim of a market without algorithms or one with identifiable human traders.
No private maker/taker IDs are read by the feature or retained in the output.
The protocol is frozen at source control time BEFORE evaluation.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import statistics
from typing import Any

from abides_export import UPSTREAM_COMMIT
from l2_trade_context import public_projection, audit_public_join
from lagged_l2_bin import summarize_lagged_book

SEEDS = (1801, 1802)
COHORTS = (
    "poisson_noise",
    "fixed_cadence_noise",
    "noise_plus_momentum",
)
DURATION = ("09:30:00", "09:42:00")
BIN_SECONDS = 30
MAX_PRIOR_QUOTE_AGE_SECONDS = 30
BOOK_DEPTH = 5


def frozen_plan() -> dict[str, Any]:
    return {
        "protocol": "abides-public-book-background-nulls-v1",
        "simulator_revision": UPSTREAM_COMMIT,
        "seeds": list(SEEDS),
        "cohorts": list(COHORTS),
        "session_clock": list(DURATION),
        "book_depth": BOOK_DEPTH,
        "bin_seconds": BIN_SECONDS,
        "maximum_previous_quote_age_seconds": MAX_PRIOR_QUOTE_AGE_SECONDS,
        "baseline": "60 noise agents, Poisson 20-second average wake-ups",
        "fixed_cadence": "60 noise agents, fixed 20-second re-wake intervals",
        "heterogeneous": "50 Poisson noise agents plus 10 momentum agents",
        "no_injected_twap_vwap_or_pov_execution_program": True,
        "no_inference_of_physical_owner": True,
        "no_real_market_calibration": True,
        "no_private_truth_used_by_feature": True,
        "no_strategy_selection_from_these_seeds": True,
    }


def summarize_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {(seed, name) for seed in SEEDS for name in COHORTS}
    observed = [(x["seed"], x["cohort"]) for x in cases]
    if len(observed) != len(expected) or set(observed) != expected:
        raise ValueError("Frozen seed/cohort matrix missing, duplicated or altered")
    for case in cases:
        if (case["public_executed_prints"] <= 0 or
            case["public_l2_snapshots"] <= 0 or
            case["public_executed_lots"] <= 0 or
            case["eligible_previous_book_bins"] < 0 or
            case["eligible_previous_book_bins"] > case["populated_trade_bins"] or
            case["same_timestamp_ambiguous_prints"] > case["public_executed_prints"] or
            case["private_agent_identifiers_accessed"] or
            case["named_execution_agent_injected"] or
            case["real_market_accuracy_calibrated"]):
            raise ValueError("Untrustworthy public-only background case")
        coefficient = case["lagged_spearman"]
        if coefficient is not None and not (-1.0 <= coefficient <= 1.0):
            raise ValueError("Impossible Spearman coefficient")
    aggregate = []
    for cohort in COHORTS:
        group = [c for c in cases if c["cohort"] == cohort]
        valid = [x["lagged_spearman"] for x in group
                 if x["lagged_spearman"] is not None]
        aggregate.append({
            "cohort": cohort,
            "simulations": len(group),
            "public_executed_prints": sum(x["public_executed_prints"] for x in group),
            "public_l2_snapshots": sum(x["public_l2_snapshots"] for x in group),
            "eligible_previous_book_bins": sum(
                x["eligible_previous_book_bins"] for x in group),
            "simulations_with_evaluable_spearman": len(valid),
            "median_descriptive_spearman": statistics.median(valid) if valid else None,
            "real_market_false_alarm_rate": None,
            "one_parent_order_identified": False,
        })
    return {
        "schema_version": "abides-public-book-background-nulls-v1",
        "frozen_plan": frozen_plan(),
        "cases": sorted(cases, key=lambda x: (x["seed"], COHORTS.index(x["cohort"]))),
        "cohorts": aggregate,
        "private_truth_read_or_published": False,
        "physical_owner_count_known": False,
        "real_market_statistical_significance_calibrated": False,
        "trading_enabled": False,
        "limitations": [
            "Genuine ABIDES matching-engine backgrounds, not real exchange tapes.",
            "No separately injected TWAP/VWAP/POV program does not mean that "
            "the whole market lacks algorithmic participants.",
            "Changes between cohorts alter market liquidity and event timing; "
            "they are not one-to-one causal counterfactuals.",
            "Two seeds per background are descriptive only and cannot estimate "
            "market false-alarm rates or select a detector threshold.",
            "Spearman measures public association rather than owner identity.",
            "The source provides no verified real broker book event sequence.",
        ],
    }


def simulate_case(seed: int, cohort: str) -> dict[str, Any]:
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import (
        NoiseAgentConfig, MomentumAgentConfig
    )
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile, run_simulation

    if seed not in SEEDS or cohort not in COHORTS:
        raise ValueError("Frozen simulation plan does not allow this case")

    builder = (
        SimulationBuilder().apply_template("liquid_market")
        .ticker("ABM").start_time(DURATION[0]).end_time(DURATION[1])
        .exchange(ExchangeConfig(book_capture="l2", book_log_depth=BOOK_DEPTH))
        .seed(seed)
    )
    if cohort == "poisson_noise":
        builder = builder.enable_agent(NoiseAgentConfig(
            multi_wake=True, wake_up_freq="20s", poisson_arrival=True,
            noise_mkt_close_time=DURATION[1]), count=60)
    elif cohort == "fixed_cadence_noise":
        builder = builder.enable_agent(NoiseAgentConfig(
            multi_wake=True, wake_up_freq="20s", poisson_arrival=False,
            noise_mkt_close_time=DURATION[1]), count=60)
    else:
        builder = builder.enable_agent(NoiseAgentConfig(
            multi_wake=True, wake_up_freq="20s", poisson_arrival=True,
            noise_mkt_close_time=DURATION[1]), count=50)
        builder = builder.enable_agent(MomentumAgentConfig(
            min_size=1, max_size=10, wake_up_freq="25s",
            poisson_arrival=True, short_window=5, long_window=15
        ), count=10)
    simulation = run_simulation(builder.build(), profile=ResultProfile.QUANT)
    if any(
        str(agent.agent_name).startswith((
            "TWAP_EXECUTION_AGENT_", "VWAP_EXECUTION_AGENT_",
            "POV_EXECUTION_AGENT_"))
        for agent in simulation.agents
    ):
        raise RuntimeError("Background contained a separately injected execution agent")
    market = simulation.markets["ABM"]
    if market.l2_series is None or market.trades is None:
        raise RuntimeError("Genuine L2 snapshots/public executions missing")
    public = public_projection(market.trades)
    if not public:
        raise RuntimeError("Exchange executed no public prints")
    lagged = summarize_lagged_book(
        market.l2_series, public, bin_seconds=BIN_SECONDS,
        maximum_quote_age_seconds=MAX_PRIOR_QUOTE_AGE_SECONDS,
        maximum_depth=BOOK_DEPTH)
    strict = audit_public_join(market.l2_series, public, max_depth=BOOK_DEPTH)
    if not lagged["previous_completed_bin_only"] or lagged["private_agent_identifiers_used"]:
        raise RuntimeError("Public history-only invariant failed")
    if sum(strict["categories"].values()) != len(public):
        raise RuntimeError("Strict public quote/fill accounting failed")
    if lagged["eligible_lagged_bins"] + sum(
        lagged["abstained_clock_bins"].values()
    ) != lagged["populated_execution_clock_bins"]:
        raise RuntimeError("Lagged public bin accounting failed")

    # Digest of *only* publicly projected scalar fields: no agent IDs,
    # execution labels, raw quote snapshots or order-level data published.
    h = sha256()
    for p in public:
        h.update((
            str(p.time_ns) + "|" + str(p.price_cents) + "|" +
            str(p.quantity) + "|" + p.reported_aggressor_side + "\n"
        ).encode("utf-8"))

    return {
        "seed": seed,
        "cohort": cohort,
        "public_projection_sha256": h.hexdigest(),
        "public_executed_prints": len(public),
        "public_executed_lots": lagged["public_execution_lots"],
        "public_l2_snapshots": lagged["source_l2_snapshot_count"],
        "same_timestamp_l2_repeats": lagged["source_same_time_l2_updates_retained"],
        "same_timestamp_ambiguous_prints":
            strict["categories"]["same_timestamp_ambiguous"],
        "populated_trade_bins": lagged["populated_execution_clock_bins"],
        "eligible_previous_book_bins": lagged["eligible_lagged_bins"],
        "lagged_spearman":
            lagged["descriptive_lagged_imbalance_to_next_buy_share_spearman"],
        "rotated_bin_placebo_spearman":
            lagged["rotated_next_bin_share_placebo_spearman"],
        "private_agent_identifiers_accessed": False,
        "named_execution_agent_injected": False,
        "real_market_accuracy_calibrated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Will not overwrite prior research evidence")
    # Freeze the full matrix in source; no CLI seed or parameter override.
    cases = [simulate_case(seed, cohort)
             for seed in SEEDS for cohort in COHORTS]
    result = summarize_cases(cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as target:
        json.dump(result, target, indent=2, sort_keys=True)
        target.write("\n")
    for cohort in result["cohorts"]:
        print("ABIDES_BACKGROUND_PUBLIC_NULL", json.dumps(cohort, sort_keys=True))
    print("ABIDES_BACKGROUND_PUBLIC_NULL_DONE", json.dumps({
        "cases": len(cases), "seeds": list(SEEDS), "truth_used": False
    }, sort_keys=True))


if __name__ == "__main__":
    main()
