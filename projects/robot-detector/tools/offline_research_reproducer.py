#!/usr/bin/env python3
"""One-command, source-free scientific negative-test and evidence reproducer.

Does NOT download any exchange market source, rerun a vendor model,
start a background agent or claim real-world robot-detection precision.
The immutable suite list is deliberately explicit: if a required
suite is missing or returns zero tests, the reproducer FAILS CLOSED.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable

if __package__:
    from .autonomy_checkpoint import load_checkpoint, validate_state
else:
    from autonomy_checkpoint import load_checkpoint, validate_state

ROOT=Path(__file__).resolve().parents[1]
TEST_ROOT=ROOT/"tests_background"
SCHEMA="robot-detector-offline-scientific-evidence-repro-v1"
SUITES=(
    "test_autonomy_checkpoint.py",
    "test_master_research_plan.py",
    "test_lobster_public_sample_format_audit.py",
    "test_lobster_event_time_features.py",
    "test_l2_duration_weighting.py",
    "test_public_l2_ownership_nonidentifiability.py",
    "test_public_l2_feed_coverage_gate.py",
    "test_toy_public_execution_rhythm.py",
    "test_abides_fixed_clock_transfer.py",
    "test_binance_public_trade_archive.py",
    "test_public_trade_direction_null.py",
    "test_real_public_trade_pair_review.py",
    "test_real_spot_transfer_review.py",
    "test_real_spot_occupancy_review.py",
    "test_real_bch_four_day_panel_review.py",
    "test_public_tape_fingerprint.py",
    "test_abides_l2_phase_fragility.py",
)
FIXTURES=(
    "fixtures/lobster_amzn_20120621_10level_format_observed_20261121.json",
    "fixtures/lobster_amzn_event_time_observed_20261121.json",
    "fixtures/lobster_amzn_clock_vs_event_observed_20261121.json",
    "fixtures/l2_synthetic_owner_worlds_observed_20261121.json",
    "fixtures/l2_synthetic_coverage_gate_20261121.json",
    "fixtures/binance_spot_transfer_20261120_observed.json",
    "fixtures/binance_spot_occupancy_20261117_observed.json",
    "fixtures/binance_bch_four_day_public_panel_20261121.json",
    "fixtures/toy_public_rhythm_hard_negative_holdout_20261121.json",
)
DOCS=(
    "docs/AUTONOMOUS_RESEARCH_TZ.md",
    "docs/MASTER_RESEARCH_PLAN.md",
    "docs/LOBSTER_EVENT_TIME_FEATURES_20261121.md",
    "docs/LOBSTER_CLOCK_VS_EVENT_WEIGHTING_20261121.md",
    "docs/SYNTHETIC_L2_OWNER_NONIDENTIFIABILITY_20261121.md",
    "docs/EXCHANGE_L2_COVERAGE_ABSTENTION_20261121.md",
)
REFERENCES=(
    "https://github.com/IskanderAbdullin/Analytics/actions/runs/44925498585",
    "https://github.com/IskanderAbdullin/Analytics/actions/runs/44926012965",
    "https://github.com/IskanderAbdullin/Analytics/actions/runs/44926352634",
    "https://github.com/IskanderAbdullin/Analytics/actions/runs/44926821602",
    "https://github.com/IskanderAbdullin/Analytics/actions/runs/44921851326",
)


def _require_local_paths() -> None:
    if len(SUITES)<10 or len(set(SUITES))!=len(SUITES):
        raise ValueError("Missing or duplicated required research tests")
    if len(set(FIXTURES))!=len(FIXTURES):
        raise ValueError("Duplicate original source fixture listing")
    for name in SUITES:
        if not re.fullmatch(r"test_[a-z0-9_]+\.py",name):
            raise ValueError("Unexpected suite outside explicit research allowlist")
        if not (TEST_ROOT/name).is_file():
            raise ValueError("Required source-free unit test absent: "+name)
    for name in DOCS:
        if not (ROOT/name).is_file():
            raise ValueError("Missing scientific method/release caveat document: "+name)
    for name in FIXTURES:
        f=ROOT/name
        if not f.is_file() or f.stat().st_size>20000:
            raise ValueError("Required original evidence fixture absent or unexpectedly large")
        raw=json.loads(f.read_text(encoding="utf-8"))
        if type(raw) is not dict or not raw:
            raise ValueError("Original aggregate fixture corrupt")


def _run_source_free_suite(
    name: str,
    runner: Callable | None = None
) -> dict:
    if name not in SUITES:
        raise ValueError("Unregistered test not permitted")
    args=(sys.executable,"-m","unittest","discover","-s",
          "tests_background","-p",name,"-v")
    if runner is None:
        env=os.environ.copy()
        env["PYTHONNOUSERSITE"]="1"
        result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,
                              env=env,timeout=40,check=False)
    else:
        result=runner(args)
    out=getattr(result,"stdout","")+getattr(result,"stderr","")
    if not isinstance(out,str):
        raise ValueError("Missing deterministic unittest output")
    match=re.findall(r"\bRan\s+(\d+)\s+tests?\b",out)
    if (getattr(result,"returncode",None)!=0 or len(match)!=1
            or int(match[0])<1 or not re.search(r"(?m)^OK\s*$",out)):
        raise ValueError("Required source-free suite failed or produced zero tests: "+name)
    return {
        "suite":name,
        "tests_passed":int(match[0]),
        "passed":True,
        "source_network_download_requested":False,
    }


def reproduce(*, runner:Callable|None=None) -> dict:
    _require_local_paths()
    state=validate_state(load_checkpoint())
    checks=[_run_source_free_suite(name,runner) for name in SUITES]
    if [x["suite"] for x in checks]!=list(SUITES):
        raise AssertionError("Required test-suite coverage was silently changed")
    manifests=[]
    for filename in FIXTURES:
        path=ROOT/filename
        payload=path.read_bytes()
        manifests.append({
            "local_aggregate_fixture":filename,
            "checked_in_aggregate_bytes":len(payload),
            "checked_in_sha256":sha256(payload).hexdigest(),
            "raw_exchange_archive_in_fixture":False,
        })
    return {
        "schema_version":SCHEMA,
        "repository":"IskanderAbdullin/Analytics",
        "project":"projects/robot-detector",
        "master_issue":state["master_issue"],
        "scientific_goal_completed":state["scientific_final_goal_already_verified"],
        "source_free_offline_suites":checks,
        "suite_count":len(checks),
        "tests_passed_total":sum(x["tests_passed"] for x in checks),
        "all_required_negative_suites_passed":True,
        "original_aggregate_evidence":manifests,
        "original_historical_source_research_runs":list(REFERENCES),
        "original_source_network_download_or_subscription_performed":False,
        "independent_reverification_of_vendor_original_zip_bytes_performed":False,
        "actual_physical_robot_owner_truth_available":False,
        "real_market_classifier_FDR_calibrated":False,
        "complete_exchange_L2_feed_proven":False,
        "synthetic_oracle_result_not_an_empirical_real_market_accuracy_estimate":True,
        "source_public_demo_research_scope_only":True,
        "raw_source_event_book_rows_exported":False,
        "next_action_from_checkpoint":state["current_stage_id"],
        "no_background_execution_promised":True,
        "limitations":[
            "Offline tests and pinned summaries reproduce code invariants, not original vendor source authenticity.",
            "Original source acquisition requires separate source access and manual, bounded research runs.",
            "No physical owner/agent IDs, calibrated real-market FDR or complete live full-depth L2.",
            "Passing the test suite is not sufficient to close master scientific issue #72.",
        ],
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Refuse to overwrite previous verified research report")
    report=reproduce()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(report,f,sort_keys=True,indent=2,allow_nan=False)
        f.write("\n")
    print("MARKET_ROBOT_DETECTOR_OFFLINE_REPRODUCED",json.dumps({
        "required_suites":report["suite_count"],
        "source_free_tests_passed":report["tests_passed_total"],
        "original_source_fixtures":len(report["original_aggregate_evidence"]),
        "physical_owner_detection_validated":False,
        "full_scientific_release_achieved":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
