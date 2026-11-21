#!/usr/bin/env python3
"""Preregistered DEVELOPMENT contrast of public L2 under injected ABIDES TWAP.

Exactly four actual simulations / twelve correlated 30s clock-origin views.
Never a blind real-market holdout, attribution method or live trading signal.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import statistics
from typing import Any

from abides_export import UPSTREAM_COMMIT
from abides_l2_binphase_sensitivity import shift_public_clock
from l2_trade_context import public_projection
from lagged_l2_bin import summarize_lagged_book
from public_tape_fingerprint import fingerprint_public_tape

SEEDS = (2401, 2402)
SCENARIOS = ("background_only", "twap_injected")
PHASES_SECONDS = (0, 10, 20)
BIN_SECONDS = 30
DEPTH = 5
START = "09:30:00"
END = "09:42:00"


def frozen_plan() -> dict:
    return {
        "schema_version": "abides-l2-controlled-twap-phase-contrast-v1",
        "simulator_revision": UPSTREAM_COMMIT,
        "development_seeds_local_only": list(SEEDS),
        "globally_unused_seeds_certified": False,
        "scenarios": list(SCENARIOS),
        "phases_seconds": list(PHASES_SECONDS),
        "bin_seconds": BIN_SECONDS, "depth": DEPTH,
        "session": [START, END], "noise_agents": 60,
        "noise_agent_wake_up": "20s Poisson",
        "twap": {
            "order_style": "market", "direction": "BID", "quantity": 1200,
            "freq": "45s", "start_time_offset": "00:01:00",
            "end_time_offset": "00:01:00"
        },
        "genuine_matching_runs": 4,
        "correlated_public_phase_views": 12,
        "internal_truth_is_posthoc_count_only": True,
        "no_phase_or_threshold_selection": True,
        "no_real_market_accuracy_or_owner_claim": True,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict:
    expected={(s,m,p) for s in SEEDS for m in SCENARIOS for p in PHASES_SECONDS}
    if type(rows) is not list or any(type(x) is not dict for x in rows):
        raise ValueError("Cases must be a list of public run summaries")
    allowed_fields={
        "seed","scenario","phase_seconds","full_public_tape_sha256",
        "public_prints","public_lots","l2_snapshots","eligible_lagged_bins",
        "populated_trade_bins","abstained_bins","rho",
        "posthoc_controlled_prints","private_identity_used_for_feature",
        "best_phase_selected","real_market_calibrated",
    }
    keys=[]
    for row in rows:
        if set(row)!=allowed_fields:
            raise ValueError("Missing or unexpected case fields: private data must not leak")
        keys.append((row.get("seed"),row.get("scenario"),row.get("phase_seconds")))
        for field in ("seed","phase_seconds","public_prints","public_lots",
                      "l2_snapshots","eligible_lagged_bins","populated_trade_bins",
                      "abstained_bins","posthoc_controlled_prints"):
            if type(row.get(field)) is not int:
                raise ValueError("Only exact integer public count or seed fields allowed")
        digest=row.get("full_public_tape_sha256")
        if (type(digest) is not str or len(digest)!=64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError("Missing or malformed full tape SHA")
        if (row["public_prints"]<=0 or row["public_lots"]<row["public_prints"]
                or row["l2_snapshots"]<=0 or row["populated_trade_bins"]<=0
                or row["eligible_lagged_bins"]<0
                or row["eligible_lagged_bins"]>row["l2_snapshots"]
                or row["eligible_lagged_bins"]+row["abstained_bins"]!=
                   row["populated_trade_bins"]
                or row["public_prints"]<row["populated_trade_bins"]
                or not 0<=row["posthoc_controlled_prints"]<=row["public_prints"]
                or (row.get("private_identity_used_for_feature") is not False)
                or row.get("best_phase_selected") is not False
                or row.get("real_market_calibrated") is not False):
            raise ValueError("Invalid source counts or forbidden evidence claim")
        rho=row.get("rho")
        if rho is not None and (type(rho) not in (int,float)
                or not math.isfinite(rho) or not -1<=rho<=1
                or row["eligible_lagged_bins"]<5):
            raise ValueError("Untrustworthy rho")
    if len(keys)!=len(expected) or set(keys)!=expected:
        raise ValueError("Changed/duplicated four-run, three-phase frozen design")
    for seed in SEEDS:
        for scenario in SCENARIOS:
            group=[r for r in rows if r["seed"]==seed and r["scenario"]==scenario]
            if (len({r["full_public_tape_sha256"] for r in group})!=1
                or len({r["public_prints"] for r in group})!=1
                or len({r["public_lots"] for r in group})!=1
                or len({r["l2_snapshots"] for r in group})!=1
                or len({r["posthoc_controlled_prints"] for r in group})!=1):
                raise ValueError("Phase views unexpectedly describe different tapes")
            if (scenario=="background_only" and
                any(r["posthoc_controlled_prints"]!=0 for r in group)):
                raise ValueError("Controlled print in genuine background-only run")
            if (scenario=="twap_injected" and
                any(r["posthoc_controlled_prints"]<=0 for r in group)):
                raise ValueError("Controlled TWAP generated no executions")
    cohorts=[]
    for scenario in SCENARIOS:
        for phase in PHASES_SECONDS:
            selected=[r for r in rows if r["scenario"]==scenario
                      and r["phase_seconds"]==phase]
            vals=[r["rho"] for r in selected if r["rho"] is not None]
            cohorts.append({
                "scenario":scenario,"phase_seconds":phase,
                "original_runs":len(selected),
                "defined_rho_runs":len(vals),
                "median_descriptive_rho":statistics.median(vals) if vals else None,
                "eligible_lagged_bins":sum(r["eligible_lagged_bins"] for r in selected),
                "synthetic_truth_count_is_not_real_owner_count":True,
            })
    return {
        "schema_version":"abides-l2-controlled-twap-phase-contrast-v1",
        "frozen_plan":frozen_plan(),
        "cases":sorted(rows,key=lambda x:(x["seed"],x["scenario"],x["phase_seconds"])),
        "cohorts":cohorts,
        "genuine_matching_runs":4,
        "non_independent_analytical_views":12,
        "private_truth_used_for_feature":False,
        "private_truth_exported":False,
        "provider_feed_completeness_proven":False,
        "real_market_significance_established":False,
        "physical_bot_count_known":False,
        "trade_execution_enabled":False,
        "limitations":[
            "The injected strategy can change the synthetic market endogenously.",
            "Two locally registered development seeds are not independent blind evidence.",
            "Clock-phase views of one tape are correlated, not new market runs.",
            "Post-hoc count verifies controlled fills only; it does not tune rho.",
            "ABIDES market physics need not match MOEX/SPB/NEO market microstructure."
        ],
    }


def run_case(seed: int, scenario: str) -> list[dict]:
    if seed not in SEEDS or scenario not in SCENARIOS:
        raise ValueError("Only source-precommitted development cases")
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import (
        NoiseAgentConfig, TWAPExecutionAgentConfig
    )
    from abides_markets.config_system.models import ExchangeConfig
    from abides_markets.simulation import ResultProfile, run_simulation
    builder=(SimulationBuilder().apply_template("liquid_market").ticker("ABM")
             .start_time(START).end_time(END)
             .exchange(ExchangeConfig(book_capture="l2",book_log_depth=DEPTH))
             .enable_agent(NoiseAgentConfig(
                 multi_wake=True,wake_up_freq="20s",poisson_arrival=True,
                 noise_mkt_close_time=END),count=60).seed(seed))
    if scenario=="twap_injected":
        builder=builder.enable_agent(TWAPExecutionAgentConfig(
            start_time_offset="00:01:00",end_time_offset="00:01:00",
            freq="45s",direction="BID",quantity=1200,trade=True,
            order_style="market"),count=1)
    result=run_simulation(builder.build(),profile=ResultProfile.QUANT)
    market=result.markets["ABM"]
    if market.l2_series is None or not market.trades:
        raise RuntimeError("Genuine public book/print data absent")
    public=public_projection(market.trades)  # no agent IDs cross feature boundary
    source=fingerprint_public_tape(market.l2_series,public,maximum_depth=DEPTH)
    rows=[]
    for phase in PHASES_SECONDS:
        book,prints=shift_public_clock(market.l2_series,public,phase)
        digest=fingerprint_public_tape(
            book,prints,restore_clock_ns=phase*1_000_000_000,
            maximum_depth=DEPTH)
        if digest["public_tape_sha256"]!=source["public_tape_sha256"]:
            raise RuntimeError("Phase transformation changed original public tape")
        report=summarize_lagged_book(
            book,prints,bin_seconds=BIN_SECONDS,
            maximum_quote_age_seconds=BIN_SECONDS,maximum_depth=DEPTH)
        rows.append({
            "seed":seed,"scenario":scenario,"phase_seconds":phase,
            "full_public_tape_sha256":digest["public_tape_sha256"],
            "public_prints":report["public_execution_prints"],
            "public_lots":report["public_execution_lots"],
            "l2_snapshots":report["source_l2_snapshot_count"],
            "eligible_lagged_bins":report["eligible_lagged_bins"],
            "populated_trade_bins":report["populated_execution_clock_bins"],
            "abstained_bins":sum(report["abstained_clock_bins"].values()),
            "rho":report["descriptive_lagged_imbalance_to_next_buy_share_spearman"],
            "posthoc_controlled_prints":0,
            "private_identity_used_for_feature":False,
            "best_phase_selected":False,"real_market_calibrated":False,
        })
    # PRIVATE identity is consulted ONLY AFTER every public feature is computed.
    controlled={int(a.agent_id) for a in result.agents
                if str(a.agent_name).startswith("TWAP_EXECUTION_AGENT_")}
    if len(controlled)!=(1 if scenario=="twap_injected" else 0):
        raise RuntimeError("Unexpected source-controlled strategy configuration")
    posthoc=sum(t.passive_agent_id in controlled or t.aggressive_agent_id in controlled
                for t in market.trades)
    if scenario=="twap_injected" and posthoc<=0:
        raise RuntimeError("Controlled TWAP produced no executed prints")
    for row in rows:
        row["posthoc_controlled_prints"]=posthoc
    return rows


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Will not overwrite any existing source evidence")
    rows=[]
    for seed in SEEDS:
        for scenario in SCENARIOS:
            rows.extend(run_case(seed,scenario))
    outcome=aggregate(rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as file:
        json.dump(outcome,file,indent=2,sort_keys=True,allow_nan=False)
        file.write("\n")
    for cohort in outcome["cohorts"]:
        print("ABIDES_TWAP_PHASE_CONTRAST",json.dumps(cohort,sort_keys=True))

if __name__=="__main__":
    main()
