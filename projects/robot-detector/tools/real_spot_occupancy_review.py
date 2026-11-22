#!/usr/bin/env python3
"""Strict no-network review of predeclared occupancy-conditioned source controls.

17 November real public spot trades are sourced after fixing occupancy >=5
and both symbols in git. This script only audits anonymous public aggregates,
never prints, private agent truth, commercial signals, or false discovery rates.
"""
from __future__ import annotations

import argparse
from datetime import datetime, time, timezone
import json
from pathlib import Path
import re

from binance_public_trade_archive import frozen_source
from public_trade_direction_null import NULL_SEEDS, PHASES_SECONDS, OCCUPANCY_CLASSES
from real_spot_transfer_review import load_json, require_exact_int

ROOT=Path(__file__).resolve().parents[1]
PRECOMMIT=ROOT/"research"/"real_spot_occupancy_precommit_20261121.json"
FROZEN=(("LTCUSDT","2026-11-17"),("BCHUSDT","2026-11-17"))
MODEL="public_within_minute_cluster_direction_null_v1"
STRATA=list(OCCUPANCY_CLASSES)
PHASES=list(PHASES_SECONDS)
SHA=re.compile("[a-f0-9]{64}")


def validate_precommit(config: dict) -> None:
    if (type(config) is not dict
            or config.get("schema_version")!="robot-detector-real-spot-occupancy-precommit-v1"
            or config.get("source_day_is_earlier_than_development_days") is not True
            or config.get("not_prospective_forward_time_holdout") is not True
            or config.get("predeclared_phase_origins_seconds")!=PHASES
            or config.get("primary_origin_seconds")!=0
            or config.get("bin_width_seconds")!=30
            or config.get("occupancy_mutually_exclusive_classes")!=STRATA
            or config.get("primary_occupancy_filter_min_prints_per_bin")!=5
            or config.get("fixed_eight_null_seeds")!=list(NULL_SEEDS)
            or config.get("no_symbol_date_or_threshold_substitution") is not True
            or config.get("report_both_positive_and_negative_case_results") is not True
            or config.get("source_sha256_must_match_provider_published_checksum") is not True
            or config.get("not_a_real_market_robot_FDR_or_physical_owner_detector") is not True
            or config.get("not_for_live_or_commercial_trading") is not True):
        raise ValueError("Research protocol or non-release gate altered")
    sources=config.get("new_source_pairs_frozen_before_any_download")
    expected=[
        {"symbol":"LTCUSDT","day":"2026-11-17",
         "role":"new_uninspected_earlier_calendar_day_same_instrument"},
        {"symbol":"BCHUSDT","day":"2026-11-17",
         "role":"new_uninspected_earlier_calendar_day_second_instrument"}
    ]
    if sources != expected:
        raise ValueError("Source identity/date changed after protocol freeze")
    metric=config.get("primary_metric")
    if (type(metric) is not str
            or not metric.startswith("in complete full-UTC-day 30s bins at phase0 with >=5")):
        raise ValueError("Changed primary outcome after precommit")


def analyze(config: dict, reports: list[dict]) -> dict:
    validate_precommit(config)
    if type(reports) is not list or len(reports)!=2:
        raise ValueError("Exactly both source reports required")
    cases=[]
    for symbol_day, source in zip(FROZEN,reports):
        symbol, day=symbol_day
        name,d,url,checksum_url=frozen_source(symbol,day)
        if type(source) is not dict:
            raise ValueError("Source must be aggregate-only object")
        if (source.get("symbol")!=symbol or source.get("utc_date")!=day
                or source.get("source_url")!=url
                or source.get("checksum_url")!=checksum_url
                or source.get("dataset_license")!=
                "CC BY-NC-SA 4.0; Binance Vision Dataset Terms 2026-08-26"
                or source.get("provider_published_checksum_matched") is not True):
            raise ValueError("Unexpected source date, instrument or license")
        sh=source.get("source_zip_sha256")
        if type(sh) is not str or not SHA.fullmatch(sh):
            raise ValueError("Provider ZIP checksum missing or malformed")
        for key in ("l2_orderbook_present",
                    "all_exchange_trades_independently_verified",
                    "market_specific_false_alarm_rate_estimated",
                    "real_world_owner_count_known",
                    "live_or_commercial_trading_enabled",
                    "commercial_use_allowed_without_license",
                    "raw_trades_or_ids_exported"):
            if source.get(key) is not False:
                raise ValueError("Falsely enabled an unavailable/unsafe source capability")
        count=require_exact_int(source,"public_trade_count",1)
        if (require_exact_int(source,"aggressive_buy_prints")
                +require_exact_int(source,"aggressive_sell_prints")!=count):
            raise ValueError("Source BUY/SELL totals do not conserve")
        if (require_exact_int(source,"last_trade_id")
                -require_exact_int(source,"first_trade_id")+1
                !=count+require_exact_int(source,"missing_ids_inside_observed_range")):
            raise ValueError("Missing or duplicate trade-ID interval anomaly")
        origin=int(datetime.combine(d,time(),timezone.utc).timestamp())*1_000_000
        if not (origin<=require_exact_int(source,"first_public_timestamp_us")
                <=require_exact_int(source,"last_public_timestamp_us")
                <origin+86_400_000_000):
            raise ValueError("Not fully inside frozen UTC archive day")
        desc=source.get("clock_origin_descriptive_v1")
        n=source.get(MODEL)
        if (type(desc) is not dict or type(n) is not dict
                or desc.get("predeclared_origin_seconds")!=PHASES
                or desc.get("all_source_prints_accounted_for_each_phase") is not True
                or desc.get("source_event_count")!=count
                or n.get("source_event_count")!=count
                or n.get("clock_phases_seconds")!=PHASES
                or n.get("bin_occupancy_classes")!=STRATA
                or n.get("primary_conditioned_bin_occupancy_minimum")!=5
                or n.get("same_timestamp_side_vector_clusters_preserved") is not True
                or n.get("physical_robot_identification_validated") is not False
                or n.get("market_false_discovery_rate_calibrated") is not False
                or n.get("optimal_phase_selected") is not False
                or n.get("commercial_or_live_trading_allowed") is not False):
            raise ValueError("Missing fixed clock/occupancy/null source parameters")
        source_phases=desc.get("variants")
        strong_phases=n.get("variants")
        if (type(source_phases) is not list or len(source_phases)!=3
                or type(strong_phases) is not list or len(strong_phases)!=3):
            raise ValueError("Expected original 0/10/20s phase cases")
        rows=[]
        for phase,drow,nrow in zip(PHASES,source_phases,strong_phases):
            if (type(drow) is not dict or type(nrow) is not dict
                    or drow.get("origin_seconds")!=phase
                    or nrow.get("origin_seconds")!=phase
                    or nrow.get("predeclared_null_seeds")!=list(NULL_SEEDS)
                    or nrow.get("num_predeclared_weak_null_replicates")!=8):
                raise ValueError("Clock phase/seed preregistration mismatch")
            nonempty=require_exact_int(drow,"eligible_nonempty_bins")
            one=require_exact_int(drow,"strictly_buy_one_sided_bins_or_sell_one_sided_bins")
            included=require_exact_int(drow,"public_prints_in_full_bins")
            excluded=require_exact_int(drow,"boundary_trades_excluded")
            total_bins=(86_400-phase)//30
            if (drow.get("fully_contained_utc_day_bins")!=total_bins
                    or nonempty>total_bins or one>nonempty
                    or included+excluded!=count
                    or nrow.get("observed_complete_nonempty_bins")!=nonempty
                    or nrow.get("observed_one_sided_bins")!=one
                    or nrow.get("observed_prints_in_full_bins")!=included
                    or nrow.get("excluded_utc_edge_prints")!=excluded):
                raise ValueError("Source UTC bin coverage mismatch")
            strata=nrow.get("one_sided_bins_by_public_print_occupancy")
            if (type(strata) is not list or len(strata)!=len(STRATA)):
                raise ValueError("Incomplete precommitted occupancy classes")
            s_rows=[]
            for index, (bucket,cur) in enumerate(zip(STRATA,strata)):
                if type(cur) is not dict or cur.get("class")!=bucket:
                    raise ValueError("Wrong bin occupancy class")
                bins=require_exact_int(cur,"eligible_complete_bins")
                observed=require_exact_int(cur,"observed_one_sided_bins")
                low=cur.get("null_one_sided_min")
                med=cur.get("null_one_sided_median")
                high=cur.get("null_one_sided_max")
                if (observed>bins or any(type(v) not in (int,float) for v in (low,med,high))
                        or not 0<=low<=med<=high<=bins
                        or cur.get("above_all_eight_controls") is not (observed>high)):
                    raise ValueError("Impossible occupancy-conditioned null statistics")
                if index==0 and (observed!=bins or low!=bins or med!=bins or high!=bins):
                    raise ValueError("One-print bins mechanically one-sided in EVERY control")
                s_rows.append({
                    "class":bucket,
                    "eligible_bins":bins,"observed_one_sided":observed,
                    "null_min":low,"null_median":med,"null_max":high
                })
            if (sum(x["eligible_bins"] for x in s_rows)!=nonempty
                    or sum(x["observed_one_sided"] for x in s_rows)!=one):
                raise ValueError("Occupancy-strata subtotals are not complete")
            qualifying=sum(r["eligible_bins"] for r in s_rows[3:])
            observed5=sum(r["observed_one_sided"] for r in s_rows[3:])
            cmin=nrow.get("null_ge5_one_sided_min")
            cmed=nrow.get("null_ge5_one_sided_median")
            cmax=nrow.get("null_ge5_one_sided_max")
            if (any(type(v) not in (float,int) for v in (cmin,cmed,cmax))
                    or not 0<=cmin<=cmed<=cmax<=qualifying
                    or nrow.get("qualifying_bins_with_at_least_five_prints")!=qualifying
                    or nrow.get("one_sided_bins_with_at_least_five_prints")!=observed5
                    or nrow.get("observed_ge5_one_sided_above_all_eight_nulls") is not
                    (observed5>cmax)):
                raise ValueError("Five-print-conditioned null inconsistency")
            rows.append({
                "origin_seconds":phase,"complete_nonempty_bins":nonempty,
                "source_public_prints_in_complete_bins":included,
                "excluded_source_utc_edge_prints":excluded,
                "one_sided_unconditional":one,
                "one_sided_bins_with_5_or_more_prints":observed5,
                "qualifying_bins_with_5_or_more_prints":qualifying,
                "cluster_null_5plus_min":cmin,
                "cluster_null_5plus_median":cmed,
                "cluster_null_5plus_max":cmax,
                "observed_5plus_exceeds_all_eight_strong_controls":observed5>cmax,
                "strata":s_rows,
            })
        cases.append({
            "symbol":symbol,"utc_day":day,
            "public_trade_count":count,"published_zip_sha256_verified":True,
            "provider_source_zip_sha256":sh,
            "primary_phase0_5plus_exceeds_null_max":
                rows[0]["observed_5plus_exceeds_all_eight_strong_controls"],
            "phases":rows,
        })
    return {
        "schema_version":"real-public-spot-occupancy-conditioned-transfer-v1",
        "precommit_path":"research/real_spot_occupancy_precommit_20261121.json",
        "precommitted_before_provider_download":True,
        "distinct_market_utc_days":1,
        "distinct_instruments":2,
        "source_public_trades_total":sum(c["public_trade_count"] for c in cases),
        "occupancy_primary_min_trades_per_30s_bin":5,
        "predeclared_primary_phase_origin_seconds":0,
        "original_frozen_null_seed_count":8,
        "all_predeclared_sources_exceeded_null_max":all(
            x["primary_phase0_5plus_exceeds_null_max"] for x in cases),
        "cases":cases,
        "not_prospective_forward_time_validation":True,
        "not_independently_labelled_real_robot_detection":True,
        "statistically_calibrated_p_value_or_false_discovery_rate":False,
        "physical_market_actor_count_known":False,
        "has_full_exchange_l2_book":False,
        "commercial_use_permitted_without_provider_license":False,
        "original_public_tape_or_event_vectors_exported":False,
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ltc-report",required=True,type=Path)
    parser.add_argument("--bch-report",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite previous historical source review")
    cfg=load_json(PRECOMMIT,max_bytes=12000)
    raw=[load_json(x,max_bytes=100000) for x in (args.ltc_report,args.bch_report)]
    result=analyze(cfg,raw)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as file:
        json.dump(result,file,sort_keys=True,indent=2,allow_nan=False)
        file.write("\n")
    print("REAL_SPOT_FIXED_OCCUPANCY_TRANSFER",json.dumps({
        "source_real_public_trades":result["source_public_trades_total"],
        "distinct_utc_days":result["distinct_market_utc_days"],
        "cases":[{"symbol":x["symbol"],
                  "primary_pass":x["primary_phase0_5plus_exceeds_null_max"],
                  "phase0_real_5plus_one_sided":x["phases"][0]["one_sided_bins_with_5_or_more_prints"],
                  "phase0_strong_null_max":x["phases"][0]["cluster_null_5plus_max"]}
                 for x in result["cases"]],
        "independent_actor_FDR_established":False,
        "commercial_trading_authorized":False
    },sort_keys=True))


if __name__=="__main__":
    main()
