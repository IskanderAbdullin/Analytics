#!/usr/bin/env python3
"""Offline independent UTC-day real public trade source-continuity audit.

Two *observed* provider ZIP checksum reports, not source events or a
blinded classifier. Data-derived summaries are non-commercial only.
"""
from __future__ import annotations
import argparse
from datetime import date,datetime,time,timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from binance_public_trade_archive import frozen_source

ROOT = Path(__file__).resolve().parents[1]
FROZEN = (
    ("2026-11-18","2fbf1fe2f85c813b3d5e4922d674799adced6f306effe0e5cf9add62a57e6522"),
    ("2026-11-19","9208231cbd6b55e4de42d04d9c07aa636be235be6d1c08ddb3c6953dbc6f3c1a"),
)
SCHEMA="robot-detector-public-real-spot-observed-manifest-v1"


def review(reports: list[dict[str,Any]]) -> dict:
    if type(reports) is not list or len(reports)!=2:
        raise ValueError("Exactly two pinned consecutive UTC observations required")
    counts=[]
    for report,(day,sha) in zip(reports,FROZEN):
        if type(report) is not dict or report.get("schema_version")!=SCHEMA:
            raise ValueError("Unexpected source fixture schema")
        if (report.get("utc_date")!=day or report.get("symbol")!="LTCUSDT"
                or report.get("source_zip_sha256")!=sha):
            raise ValueError("Frozen source identity has changed")
        _,d,url,checksum=frozen_source("LTCUSDT",day)
        if report.get("source_zip_url")!=url or report.get("provider_checksum_url")!=checksum:
            raise ValueError("Source endpoints changed or unexpected")
        if (report.get("data_license")!=
                "CC BY-NC-SA 4.0; Binance Vision Dataset Terms 2026-08-26"):
            raise ValueError("Source license missing")
        for key in ("provider_checksum_verified",):
            if report.get(key) is not True:
                raise ValueError("Provider SHA match not recorded")
        for key in ("real_exchange_archive_completeness_independently_proven",
                    "orderbook_l2_in_archive","raw_event_data_redistributed",
                    "live_or_commercial_trading_enabled",
                    "market_bot_detection_accuracy_established",
                    "real_world_physical_owner_count_known"):
            if report.get(key) is not False:
                raise ValueError("Forbidden or missing source uncertainty")
        ints=("public_trade_count","first_trade_id","last_trade_id",
              "missing_ids_inside_observed_range","aggressive_buy_prints",
              "aggressive_sell_prints","first_public_timestamp_us",
              "last_public_timestamp_us")
        if any(type(report.get(k)) is not int for k in ints):
            raise ValueError("Public counts and source clock must be exact integers")
        n=report["public_trade_count"]
        b=report["aggressive_buy_prints"]
        s=report["aggressive_sell_prints"]
        if (n<=0 or b<0 or s<0 or b+s!=n
                or report["missing_ids_inside_observed_range"]!=0
                or report["last_trade_id"]-report["first_trade_id"]+1!=n):
            raise ValueError("Source within-day public execution conservation failure")
        begin=int(datetime.combine(d,time(),timezone.utc).timestamp())*1_000_000
        if not(begin<=report["first_public_timestamp_us"]
               <=report["last_public_timestamp_us"]<begin+86_400_000_000):
            raise ValueError("Source UTC day or observed clock bounds changed")
        for name in ("aggressive_buy_base_quantity","aggressive_sell_base_quantity"):
            v=report.get(name)
            if type(v) is not str:
                raise ValueError("Missing exact decimal quantity")
            try:
                decimal=Decimal(v)
            except Exception as exc:
                raise ValueError("Invalid source volume") from exc
            if not decimal.is_finite() or decimal<0:
                raise ValueError("Invalid source volume")
        counts.append(n)
    first,second=reports
    if (second["first_trade_id"]!=first["last_trade_id"]+1
            or second["first_public_timestamp_us"]<first["last_public_timestamp_us"]):
        raise ValueError("Adjacent public trade archives violate observed ID/time continuity")
    phase=second.get("clock_origin_descriptive_v1")
    if (type(phase) is not dict
            or phase.get("predeclared_origin_seconds")!=[0,10,20]
            or phase.get("source_event_count")!=second["public_trade_count"]
            or phase.get("all_source_prints_accounted_for_each_phase") is not True
            or phase.get("threshold_or_best_phase_selected") is not False
            or phase.get("real_world_bot_calibration_claimed") is not False):
        raise ValueError("Original phase-study provenance missing")
    variants=phase.get("variants")
    if type(variants) is not list or len(variants)!=3:
        raise ValueError("Three frozen clock origin cases required")
    for v,origin in zip(variants,(0,10,20)):
        if type(v) is not dict or v.get("origin_seconds")!=origin:
            raise ValueError("Changed order or identity of phase cases")
        keys=("bin_width_seconds","fully_contained_utc_day_bins",
              "eligible_nonempty_bins","empty_complete_bins",
              "public_prints_in_full_bins","boundary_trades_excluded",
              "strictly_buy_one_sided_bins_or_sell_one_sided_bins",
              "buy_dominant_bins","sell_dominant_bins",
              "equal_buy_sell_print_count_bins")
        if any(type(v.get(k)) is not int for k in keys):
            raise ValueError("Wrong phase case integer type")
        total=(86_400-origin)//30
        eligible=v["eligible_nonempty_bins"]
        if (v["bin_width_seconds"]!=30
                or v["fully_contained_utc_day_bins"]!=total
                or not 0<=eligible<=total
                or v["empty_complete_bins"]!=total-eligible
                or v["public_prints_in_full_bins"]<eligible
                or v["public_prints_in_full_bins"]+v["boundary_trades_excluded"]!=counts[1]
                or not 0<=v["strictly_buy_one_sided_bins_or_sell_one_sided_bins"]<=eligible
                or any(v[k]<0 for k in keys)
                or v["buy_dominant_bins"]+v["sell_dominant_bins"]
                   +v["equal_buy_sell_print_count_bins"]!=eligible):
            raise ValueError("Public print clock-phase summary does not conserve cases")
    total=sum(counts)
    buys=sum(r["aggressive_buy_prints"] for r in reports)
    sells=sum(r["aggressive_sell_prints"] for r in reports)
    return {
        "schema_version":"real-spot-two-adjacent-days-public-provenance-v1",
        "symbol":"LTCUSDT","utc_days":[day for day,_ in FROZEN],
        "real_exchange_daily_archives":2,"dependent_time_origin_views_for_second_day":3,
        "observed_source_trade_count":total,
        "first_day_public_trades":counts[0],"second_day_public_trades":counts[1],
        "public_aggressive_buy_prints":buys,"public_aggressive_sell_prints":sells,
        "overall_buy_print_fraction":buys/total,
        "first_day_buy_fraction":first["aggressive_buy_prints"]/counts[0],
        "second_day_buy_fraction":second["aggressive_buy_prints"]/counts[1],
        "adjacent_day_observed_public_trade_ids_consecutive":True,
        "provider_checksum_evidence_stored_in_original_workflows":True,
        "original_raw_files_reverified_by_this_review":False,
        "provider_exchange_completeness_independently_proven":False,
        "public_spot_l2_available":False,
        "real_market_bot_identification_proven":False,
        "independent_blind_detector_holdout_established":False,
        "commercial_or_live_trading_authorized":False,
        "read_only_original_market_sessions":True,
        "limitations":[
            "Two source tapes are separate UTC market sessions; phase views reuse day 2.",
            "This offline review checks committed source attestations, not original ZIP bytes.",
            "Continuous observed IDs and provider ZIP SHA cannot prove all actual exchange events.",
            "Trade direction ratios do not identify bots or validate market predictions.",
            "CC BY-NC-SA 4.0 and source terms restrict use to non-commercial research.",
        ],
    }


def _unique_pairs(pairs):
    obj={}
    for k,v in pairs:
        if k in obj:
            raise ValueError("Duplicate provenance JSON field")
        obj[k]=v
    return obj


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Will not overwrite historical source evidence")
    files=[ROOT/"fixtures"/f"binance_spot_ltcusdt_real_observed_{d.replace('-','')}.json"
           for d,_ in FROZEN]
    reports=[]
    for file in files:
        if file.stat().st_size>15000:
            raise ValueError("Source report unexpectedly large")
        reports.append(json.loads(file.read_text(encoding="utf-8"),
                                  object_pairs_hook=_unique_pairs,
                                  parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x))))
    result=review(reports)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,sort_keys=True,indent=2,allow_nan=False)
        f.write("\n")
    print("REAL_PUBLIC_PAIR_AUDIT",json.dumps({
        "days":result["real_exchange_daily_archives"],
        "trades":result["observed_source_trade_count"],
        "continuous_ids":result["adjacent_day_observed_public_trade_ids_consecutive"],
        "market_accuracy_proven":False
    },sort_keys=True))

if __name__=="__main__":
    main()
