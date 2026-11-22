#!/usr/bin/env python3
"""Frozen source-free public execution rhythm toy with hard-negative equivalence.

This is a constructed illustrative process, not ABIDES, a live exchange,
or a calibrated detector. An injected periodic target and a periodic
BACKGROUND-only cohort are intentionally observationally identical.
No oracle source ID may reach score_public().
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from random import Random

SEEDS_DEVELOPMENT=(2601,2602,2603,2604)
SEEDS_HOLDOUT=(2701,2702,2703,2704)
COHORTS=("independent_noise_null","periodic_noise_hard_negative",
         "periodic_target_positive")
START_US=34_200_000_000
END_US=34_800_000_000
GRID_PERIOD_US=10_000_000
GRID_TOLERANCE_US=250_000
THRESHOLD=0.22
BACKGROUND_PRINTS=120
PERIODIC_PRINTS=60

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"research"/"fixed_clock_toy_rhythm_precommit_20261121.json"


@dataclass(frozen=True)
class PublicExecutedPrint:
    exchange_local_time_us: int
    executed_lots: int
    buyer_initiated: bool
    executed_price_ticks: int


def check_protocol() -> dict:
    data=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (data.get("schema_version")!="robot-detector-fixed-grid-toy-rhythm-frozen-v1"
            or data.get("development_seeds")!=list(SEEDS_DEVELOPMENT)
            or data.get("uninspected_holdout_seed_ids_at_freeze")!=list(SEEDS_HOLDOUT)
            or data.get("source")!="ONLY_CONSTRUCTED_TOY_NO_REAL_EXCHANGE_OR_GENUINE_ABIDES"
            or data.get("session_clock_seconds_after_midnight")!=[34200,34800]
            or data.get("periodic_clock_grid_seconds")!=10
            or data.get("within_phase_grid_tolerance_microseconds")!=GRID_TOLERANCE_US
            or data.get("phase_origin_seconds_after_midnight")!=34200
            or data.get("threshold_fraction_of_public_executed_prints_on_grid")!=THRESHOLD
            or [x.get("key") for x in data.get("scenarios",[])]!=list(COHORTS)
            or [x.get("source_public_prints") for x in data["scenarios"]] !=
               [BACKGROUND_PRINTS,BACKGROUND_PRINTS+PERIODIC_PRINTS,
                BACKGROUND_PRINTS+PERIODIC_PRINTS]
            or [x.get("truth_injected_target_present") for x in data["scenarios"]]!=
               [False,False,True]
            or data.get("private_truth_used_only_after_detection") is not True
            or data.get("identical_public_tape_between_hard_negative_and_target_positive_for_each_seed") is not True
            or data.get("no_best_phase_or_threshold_selection") is not True
            or data.get("not_true_market_traffic_simulation") is not True
            or data.get("must_record_false_positives_in_periodic_noise_cohort") is not True):
        raise ValueError("Toy hypothesis, held-out data identity or threshold changed after freeze")
    return data


def public_prints(seed: int, cohort: str) -> tuple[PublicExecutedPrint,...]:
    """Generate PUBLIC observations; no latent target IDs in the schema."""
    if type(seed) is not int or seed not in SEEDS_DEVELOPMENT+SEEDS_HOLDOUT:
        raise ValueError("Only preregistered project-local seed inputs")
    if cohort not in COHORTS:
        raise ValueError("Only three preregistered synthetic scenarios")
    rng=Random(seed)
    rows=[]
    for _ in range(BACKGROUND_PRINTS):
        stamp=START_US+rng.randrange(0,END_US-START_US)
        rows.append(PublicExecutedPrint(
            stamp,1+rng.randrange(1,4),bool(rng.randrange(0,2)),
            100000+rng.randrange(0,100)))
    if cohort != "independent_noise_null":
        for j in range(PERIODIC_PRINTS):
            stamp=START_US+j*GRID_PERIOD_US
            rows.append(PublicExecutedPrint(
                stamp,1+rng.randrange(1,4),bool(rng.randrange(0,2)),
                100000+rng.randrange(0,100)))
    return tuple(sorted(rows,key=lambda x:x.exchange_local_time_us))


def _validate_public(public: tuple[PublicExecutedPrint,...]) -> None:
    if type(public) is not tuple or not 1<=len(public)<=500:
        raise ValueError("Expected bounded public executed tape")
    prev=None
    for row in public:
        if type(row) is not PublicExecutedPrint:
            raise ValueError("Source-only projection cannot include oracle fields")
        t=row.exchange_local_time_us
        if (type(t) is not int or not START_US<=t<END_US
                or (prev is not None and t<prev)
                or type(row.executed_lots) is not int
                or row.executed_lots<1
                or type(row.buyer_initiated) is not bool
                or type(row.executed_price_ticks) is not int
                or row.executed_price_ticks<1):
            raise ValueError("Malformed public-only executed print")
        prev=t


def score_public(public: tuple[PublicExecutedPrint,...]) -> dict:
    """Freeze feature and threshold; only public market data are accepted."""
    _validate_public(public)
    matched=0
    for item in public:
        offset=(item.exchange_local_time_us-START_US)%GRID_PERIOD_US
        if min(offset,GRID_PERIOD_US-offset)<=GRID_TOLERANCE_US:
            matched+=1
    score=matched/len(public)
    return {
        "observed_public_trade_prints":len(public),
        "public_prints_near_fixed_grid":matched,
        "fraction_near_fixed_grid":round(score,8),
        "predicted_fixed_clock_pattern_present":score>=THRESHOLD,
        "fixed_clock_grid_seconds":10,
        "frozen_tolerance_microseconds":250000,
        "predeclared_threshold_fraction":THRESHOLD,
        "physical_owner_count_or_true_bot_identity_inferred":False,
    }


def public_fingerprint(public:tuple[PublicExecutedPrint,...])->str:
    _validate_public(public)
    rows=[
        (x.exchange_local_time_us,x.executed_lots,x.buyer_initiated,
         x.executed_price_ticks) for x in public
    ]
    return sha256(json.dumps(rows,separators=(",",":")).encode()).hexdigest()


def evaluate_fixed_cohorts(seeds:tuple[int,...]) -> dict:
    check_protocol()
    if type(seeds) is not tuple or seeds not in (
        SEEDS_DEVELOPMENT,SEEDS_HOLDOUT):
        raise ValueError("Not the exact frozen development or holdout set")
    cases=[]
    for seed in seeds:
        fingerprints={}
        for cohort in COHORTS:
            # Market observations consumed FIRST. Truth only for evaluation
            # after score_public returned; never passed to features.
            public=public_prints(seed,cohort)
            measured=score_public(public)
            fingerprint=public_fingerprint(public)
            target_present=(cohort=="periodic_target_positive")
            if (cohort=="periodic_noise_hard_negative" and target_present):
                raise AssertionError("Hard negative must contain no target")
            fingerprints[cohort]=fingerprint
            cases.append({
                "seed":seed,
                "cohort":cohort,
                "source_free_public_prints":measured["observed_public_trade_prints"],
                "on_grid_public_fraction":measured["fraction_near_fixed_grid"],
                "predicted_periodicity":measured["predicted_fixed_clock_pattern_present"],
                "private_oracle_target_present_only_after_scoring":target_present,
                "true_positive":target_present and measured["predicted_fixed_clock_pattern_present"],
                "false_positive":not target_present and measured["predicted_fixed_clock_pattern_present"],
                "false_negative":target_present and not measured["predicted_fixed_clock_pattern_present"],
                "no_source_owner_id_in_public_data":True,
            })
        if (fingerprints["periodic_noise_hard_negative"] !=
                fingerprints["periodic_target_positive"]):
            raise AssertionError("Synthetic hard negative must be public-indistinguishable from target")
    if len(cases)!=len(seeds)*len(COHORTS):
        raise AssertionError("Missing an original preregistered synthetic scenario")
    summary={}
    for cohort in COHORTS:
        found=[x for x in cases if x["cohort"]==cohort]
        summary[cohort]={
            "source_free_cases":len(found),
            "predicted_periodic":sum(x["predicted_periodicity"] for x in found),
            "false_positive":sum(x["false_positive"] for x in found),
            "true_positive":sum(x["true_positive"] for x in found),
            "false_negative":sum(x["false_negative"] for x in found),
        }
    return {
        "schema_version":"toy-public-execution-fixed-clock-holdout-v1",
        "toy_only_not_real_exchange_simulation":True,
        "seeds_local_project_ledger_globally_unseen_not_verified":True,
        "phase_or_threshold_selected_after_holdout":False,
        "fixed_period_seconds":10,
        "tolerance_microseconds":GRID_TOLERANCE_US,
        "threshold":THRESHOLD,
        "cohorts":list(COHORTS),
        "cases":cases,
        "scenario_summary":summary,
        "same_public_tape_for_periodic_noise_and_positive_each_seed":True,
        "any_true_physical_owner_labels_from_real_market":False,
        "real_market_precision_recall_or_FDR_calibrated":False,
        "real_market_trade_or_l2_archive_loaded":False,
        "trading_enabled":False,
        "limitations":[
            "Artificial 10-second grid with fixed threshold, not a learned market detector.",
            "Periodic non-target background is deliberately public-indistinguishable from target.",
            "Classifications concern fixed-grid public rhythm, not actual physical robot ownership.",
            "Results are not ABIDES or a real exchange holdout and cannot calibrate market FDR.",
            "Only the specified local project ledger can establish spent seed provenance.",
        ],
    }


def main()->None:
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists():
        p.error("Do not overwrite frozen research evidence")
    result=evaluate_fixed_cohorts(SEEDS_HOLDOUT)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,sort_keys=True,indent=2,allow_nan=False)
        f.write("\n")
    print("TOY_EXECUTION_RHYTHM_HARD_NEGATIVE",json.dumps({
        "holdout_seeds":list(SEEDS_HOLDOUT),
        "cases":len(result["cases"]),
        "cohort_results":result["scenario_summary"],
        "hard_negative_publicly_indistinguishable":True,
        "real_market_detector_accuracy_proven":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
