#!/usr/bin/env python3
"""BCH four-day source-only public-print occupancy panel.

Previously inspected 17/20 cases are DEV/retrospective. The exact
18/19 BCH archives were preregistered before their original download.
No real robot labels, calibrated FDR, L2 orderbook or commercial signal.
"""
from __future__ import annotations
import argparse
from datetime import datetime,time,timezone
import json
from pathlib import Path
import re
from binance_public_trade_archive import frozen_source
from public_trade_direction_null import NULL_SEEDS,OCCUPANCY_CLASSES,PHASES_SECONDS
from real_spot_transfer_review import load_json,require_exact_int

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"research"/"real_bch_full_panel_precommit_20261121.json"
EARLIER=ROOT/"fixtures"/"binance_spot_occupancy_20261117_observed.json"
NEW_DAYS=("2026-11-18","2026-11-19")
LAST_DAY="2026-11-20"
ALL_DAYS=("2026-11-17",)+NEW_DAYS+(LAST_DAY,)
EXPECTED_SEEN_SHA="553421be8eaf1e339eb0e111a25604ce7d2965e85ad15cea1650ffa0d012e46c"


def validate_protocol(cfg:dict) -> None:
    if type(cfg) is not dict or cfg.get("schema_version")!="robot-detector-bch-full-spot-panel-precommit-v1":
        raise ValueError("Missing frozen study provenance")
    expected=[{"symbol":"BCHUSDT","day":day,
               "status":"never_inspected_in_this_project"} for day in NEW_DAYS]
    seen=cfg.get("previously_inspected_BCH_2026_11_20_to_recompute_for_same_5plus_occupancy_method")
    if (cfg.get("new_precommitted_archives")!=expected
            or cfg.get("four_day_panel_expected_dates")!=list(ALL_DAYS)
            or cfg.get("frozen_primary_origin_seconds")!=0
            or cfg.get("frozen_secondary_origins_seconds")!=[10,20]
            or cfg.get("frozen_bin_width_seconds")!=30
            or cfg.get("frozen_minimum_fills_per_bin")!=5
            or cfg.get("frozen_occupancy_groups")!=list(OCCUPANCY_CLASSES)
            or cfg.get("frozen_null_rng_seeds")!=list(NULL_SEEDS)
            or cfg.get("record_both_archive_outcomes_including_negative") is not True
            or cfg.get("never_select_best_phase_after_results") is not True
            or cfg.get("not_forward_time_or_labelled_bot_holdout") is not True
            or cfg.get("only_noncommercial_public_source_research") is not True
            or type(seen) is not dict
            or seen.get("symbol")!="BCHUSDT" or seen.get("day")!=LAST_DAY
            or seen.get("original_source_sha256")!=EXPECTED_SEEN_SHA
            or seen.get("original_verified_public_trades")!=73279
            or seen.get("already_seen_source_not_independent_validation") is not True
            or cfg.get("earlier_2026_11_17_occupancy_fixture")!=
               "fixtures/binance_spot_occupancy_20261117_observed.json"):
        raise ValueError("Frozen market dates, nulls, licensing or truth caveats changed")


def _read_source(report:dict,day:str,*, expected_count=None,expected_sha=None)->dict:
    if type(report) is not dict:
        raise ValueError("Missing public source observation")
    name,d,url,check=frozen_source("BCHUSDT",day)
    sha=report.get("source_zip_sha256")
    if (report.get("symbol")!="BCHUSDT" or report.get("utc_date")!=day
            or report.get("source_url")!=url or report.get("checksum_url")!=check
            or report.get("provider_published_checksum_matched") is not True
            or report.get("dataset_license")!=
               "CC BY-NC-SA 4.0; Binance Vision Dataset Terms 2026-08-26"
            or type(sha) is not str or not re.fullmatch("[a-f0-9]{64}",sha)):
        raise ValueError("Source URL, provider SHA or license missing")
    if expected_sha is not None and sha!=expected_sha:
        raise ValueError("Inspected Nov20 source file changed")
    n=require_exact_int(report,"public_trade_count",1)
    if expected_count is not None and n!=expected_count:
        raise ValueError("Inspected Nov20 source trade count changed")
    if (require_exact_int(report,"aggressive_buy_prints")
            +require_exact_int(report,"aggressive_sell_prints")!=n):
        raise ValueError("Public execution direction conservation failed")
    first=require_exact_int(report,"first_trade_id")
    last=require_exact_int(report,"last_trade_id")
    if last-first+1 != n+require_exact_int(report,"missing_ids_inside_observed_range"):
        raise ValueError("ID range does not reconcile with public source count")
    start=int(datetime.combine(d,time(),timezone.utc).timestamp())*1_000_000
    if not(start<=require_exact_int(report,"first_public_timestamp_us")
           <=require_exact_int(report,"last_public_timestamp_us")
           <start+86_400_000_000):
        raise ValueError("Source timestamp outside selected UTC day")
    for k in ("l2_orderbook_present",
              "all_exchange_trades_independently_verified",
              "market_specific_false_alarm_rate_estimated",
              "real_world_owner_count_known",
              "tuned_detector_or_threshold",
              "live_or_commercial_trading_enabled",
              "commercial_use_allowed_without_license",
              "raw_trades_or_ids_exported"):
        if report.get(k) is not False:
            raise ValueError("Fake source market capability: "+k)
    desc=report.get("clock_origin_descriptive_v1")
    strong=report.get("public_within_minute_cluster_direction_null_v1")
    if (type(desc) is not dict or type(strong) is not dict
            or desc.get("predeclared_origin_seconds")!=[0,10,20]
            or desc.get("all_source_prints_accounted_for_each_phase") is not True
            or desc.get("source_event_count")!=n
            or strong.get("source_event_count")!=n
            or strong.get("clock_phases_seconds")!=[0,10,20]
            or strong.get("bin_occupancy_classes")!=list(OCCUPANCY_CLASSES)
            or strong.get("primary_conditioned_bin_occupancy_minimum")!=5
            or strong.get("same_timestamp_side_vector_clusters_preserved") is not True
            or strong.get("market_false_discovery_rate_calibrated") is not False
            or strong.get("physical_robot_identification_validated") is not False):
        raise ValueError("Wrong fixed null, phase or clustering study")
    drows=desc.get("variants")
    srows=strong.get("variants")
    if (type(drows) is not list or len(drows)!=3
            or type(srows) is not list or len(srows)!=3):
        raise ValueError("Incomplete 0/10/20 original clock bins")
    phases=[]
    for phase,drow,srow in zip(PHASES_SECONDS,drows,srows):
        if (type(drow) is not dict or type(srow) is not dict
                or drow.get("origin_seconds")!=phase
                or srow.get("origin_seconds")!=phase
                or srow.get("predeclared_null_seeds")!=list(NULL_SEEDS)
                or srow.get("num_predeclared_weak_null_replicates")!=8):
            raise ValueError("Original frozen clock/seed study drift")
        total=require_exact_int(drow,"eligible_nonempty_bins")
        one=require_exact_int(drow,"strictly_buy_one_sided_bins_or_sell_one_sided_bins")
        included=require_exact_int(drow,"public_prints_in_full_bins")
        edge=require_exact_int(drow,"boundary_trades_excluded")
        if (total>(86_400-phase)//30 or one>total or included+edge!=n
                or srow.get("observed_complete_nonempty_bins")!=total
                or srow.get("observed_one_sided_bins")!=one
                or srow.get("excluded_utc_edge_prints")!=edge):
            raise ValueError("Public source time bins do not reconcile")
        strata=srow.get("one_sided_bins_by_public_print_occupancy")
        if type(strata) is not list or len(strata)!=5:
            raise ValueError("Missing occupancy classes")
        counts=[]
        ones=[]
        for j,(k,entry) in enumerate(zip(OCCUPANCY_CLASSES,strata)):
            if type(entry) is not dict or entry.get("class")!=k:
                raise ValueError("Renamed occupancy class after precommit")
            ct=require_exact_int(entry,"eligible_complete_bins")
            oc=require_exact_int(entry,"observed_one_sided_bins")
            low=entry.get("null_one_sided_min")
            med=entry.get("null_one_sided_median")
            high=entry.get("null_one_sided_max")
            if (oc>ct or any(type(v) not in (int,float) for v in (low,med,high))
                    or not 0<=low<=med<=high<=ct
                    or entry.get("above_all_eight_controls") is not (oc>high)):
                raise ValueError("Impossible occupancy null strata count")
            if j==0 and (oc!=ct or low!=ct or med!=ct or high!=ct):
                raise ValueError("One printed fill per interval is always one-sided")
            counts.append(ct)
            ones.append(oc)
        if sum(counts)!=total or sum(ones)!=one:
            raise ValueError("Occupancy subtotals do not conserve")
        ge5=sum(counts[3:])
        one5=sum(ones[3:])
        mn=srow.get("null_ge5_one_sided_min")
        md=srow.get("null_ge5_one_sided_median")
        mx=srow.get("null_ge5_one_sided_max")
        if (srow.get("qualifying_bins_with_at_least_five_prints")!=ge5
                or srow.get("one_sided_bins_with_at_least_five_prints")!=one5
                or any(type(v) not in (int,float) for v in (mn,md,mx))
                or not 0<=mn<=md<=mx<=ge5
                or srow.get("observed_ge5_one_sided_above_all_eight_nulls") is not
                (one5>mx)):
            raise ValueError("Five-print threshold or original null envelope altered")
        phases.append({
            "phase_seconds":phase,"nonempty_bins":total,
            "one_sided_all":one,"one_fill_bins":counts[0],
            "five_plus_eligible":ge5,"five_plus_one_sided":one5,
            "strong_null_five_plus_min":mn,
            "strong_null_five_plus_median":md,
            "strong_null_five_plus_max":mx,
            "observed_above_all_eight":one5>mx
        })
    return {
        "symbol":"BCHUSDT","utc_day":day,
        "public_trade_count":n,"provider_zip_sha256":sha,
        "observed_first_public_trade_id":first,
        "observed_last_public_trade_id":last,
        "observed_within_file_id_gaps":require_exact_int(report,"missing_ids_inside_observed_range"),
        "phase0_conditioned_primary_met":phases[0]["observed_above_all_eight"],
        "phases":phases,
    }


def _read_seen_nov17_fixture(original:dict)->dict:
    if (original.get("original_run_id")!=44921288804
            or original.get("source_public_trades_total")!=150466
            or original.get("precommitted_joint_primary_both_pass") is not False):
        raise ValueError("Original Nov17 source fixture mutated")
    cases=original.get("cases")
    if type(cases) is not list or len(cases)!=2:
        raise ValueError("Missing source Nov17 cases")
    c=cases[1]
    if (c.get("symbol")!="BCHUSDT" or c.get("utc_day")!="2026-11-17"
            or c.get("public_trades")!=42678 or c.get("primary_pass") is not False
            or c.get("sha256")!="dca1e3983106d787d10a80e6a8a6b7fd9dc4866afef6ea25379e065abdae1b53"
            or c.get("first_observed_trade_id")!=296851413
            or c.get("last_observed_trade_id")!=296894090):
        raise ValueError("Nov17 original BCH source identity changed")
    phases=c.get("phases")
    if (type(phases) is not list or len(phases)!=3
            or [v.get("origin_seconds") for v in phases]!=[0,10,20]):
        raise ValueError("Nov17 original source phases missing")
    return {
        "symbol":"BCHUSDT","utc_day":"2026-11-17",
        "public_trade_count":42678,"provider_zip_sha256":c["sha256"],
        "observed_first_public_trade_id":296851413,
        "observed_last_public_trade_id":296894090,
        "observed_within_file_id_gaps":0,
        "phase0_conditioned_primary_met":False,
        "phases":[{
            "phase_seconds":v["origin_seconds"],
            "nonempty_bins":sum(v["occupancy_bin_counts"]),
            "one_sided_all":v["observed_all_one_sided"],
            "one_fill_bins":v["occupancy_bin_counts"][0],
            "five_plus_eligible":v["eligible_ge5"],
            "five_plus_one_sided":v["observed_ge5_one_sided"],
            "strong_null_five_plus_min":v["null_ge5_min"],
            "strong_null_five_plus_median":v["null_ge5_median"],
            "strong_null_five_plus_max":v["null_ge5_max"],
            "observed_above_all_eight":v["precommitted_strong_null_envelope_pass"]
        } for v in phases],
    }


def analyze(config:dict,new18:dict,new19:dict,seen20:dict,earlier17:dict)->dict:
    validate_protocol(config)
    r17=_read_seen_nov17_fixture(earlier17)
    r18=_read_source(new18,"2026-11-18")
    r19=_read_source(new19,"2026-11-19")
    r20=_read_source(seen20,"2026-11-20",expected_count=73279,
                     expected_sha=EXPECTED_SEEN_SHA)
    four=[r17,r18,r19,r20]
    continuity=[four[i]["observed_last_public_trade_id"]+1==
                four[i+1]["observed_first_public_trade_id"] for i in range(3)]
    return {
        "schema_version":"bch-public-real-spot-four-day-occupancy-panel-v1",
        "frozen_new_archive_dates":list(NEW_DAYS),
        "all_observed_dates_in_UTC_order":list(ALL_DAYS),
        "original_precommit_path":"research/real_bch_full_panel_precommit_20261121.json",
        "new_source_days_precommitted_before_download":True,
        "previously_inspected_dates":["2026-11-17","2026-11-20"],
        "independent_utc_market_dates":4,
        "independent_real_market_actor_labels_available":False,
        "bch_published_zip_provider_checksums_verified_for_new_sources":True,
        "full_bch_public_tape_observed_trade_id_adjacent_boundaries":continuity,
        "full_bch_observed_ids_contiguous_across_four_utc_days":all(continuity),
        "provider_exchange_completeness_independently_verified":False,
        "sum_original_public_trade_prints":sum(x["public_trade_count"] for x in four),
        "uninspected_source_phase0_5plus_cases_passed":sum(
            x["phase0_conditioned_primary_met"] for x in (r18,r19)),
        "uninspected_source_phase0_5plus_cases_total":2,
        "all_cases":four,
        "calibrated_real_actor_p_values_or_FDR":False,
        "commercial_or_live_trading_authorized":False,
        "full_depth_exchange_l2_available":False,
        "raw_public_source_event_tapes_exported":False,
        "limitations":[
            "Only BCH 18/19 were preregistered as previously uninspected. BCH 17/20 previously inspected.",
            "All four dates are close and not statistically independent regimes.",
            "Eight timestamp-preserving shuffles are not a validated physical-market null.",
            "Observed provider public trade-ID continuity cannot certify exchange completeness.",
            "No real bot owner labels, calibrated FDR, L2, trading or commercial data rights."
        ]
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bch18",required=True,type=Path)
    p.add_argument("--bch19",required=True,type=Path)
    p.add_argument("--bch20",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    if args.output.exists():
        p.error("Never overwrite original research source report")
    cfg=load_json(PROTOCOL,max_bytes=12000)
    old=load_json(EARLIER,max_bytes=12000)
    reports=[load_json(x,max_bytes=100000) for x in
             (args.bch18,args.bch19,args.bch20)]
    result=analyze(cfg,*reports,old)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as file:
        json.dump(result,file,indent=2,sort_keys=True,allow_nan=False)
        file.write("\n")
    print("BCH_FOUR_DAY_PUBLIC_TRADE_PANEL",json.dumps({
        "public_trades_four_days":result["sum_original_public_trade_prints"],
        "new_source_dates":result["frozen_new_archive_dates"],
        "new_source_primary_successes":result["uninspected_source_phase0_5plus_cases_passed"],
        "new_source_primary_cases":2,
        "consecutive_provider_public_id_boundaries":
            result["full_bch_public_tape_observed_trade_id_adjacent_boundaries"],
        "physical_bot_truth_established":False,
        "commercial_market_data_entitlement":False
    },sort_keys=True))


if __name__=="__main__":
    main()
