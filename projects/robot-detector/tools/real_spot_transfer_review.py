#!/usr/bin/env python3
"""Fail-closed independent review of precommitted real spot descriptive transfer.

No network: reads compact public-source aggregate JSON, not raw trades.
The two 2026-11-20 source identities, clock offsets and both null
algorithms were frozen on GitHub BEFORE downloading either archive.
Does not establish participant identity, causal effect or classifier FDR.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from binance_public_trade_archive import frozen_source
from public_trade_direction_null import NULL_SEEDS, PHASES_SECONDS

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "real_spot_transfer_precommit_20261121.json"
FROZEN = (("LTCUSDT","2026-11-20"),("BCHUSDT","2026-11-20"))
NULLS = ("public_within_minute_weak_direction_null_v1",
         "public_within_minute_cluster_direction_null_v1")
PHASES = (0,10,20)
RESEARCH_LICENSE = "CC BY-NC-SA 4.0; Binance Vision Dataset Terms 2026-08-26"
SCHEMA = "robot-detector-real-spot-transfer-audited-v1"


def strict_pairs(pairs: list[tuple[str,Any]]) -> dict:
    out = {}
    for k,v in pairs:
        if k in out:
            raise ValueError("Duplicate JSON provenance key")
        out[k] = v
    return out


def load_json(path: Path, *, max_bytes: int = 80_000) -> dict:
    if path.stat().st_size > max_bytes:
        raise ValueError("Source report exceeds bounded aggregate limit")
    result = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs,
                        parse_constant=lambda n: (_ for _ in ()).throw(ValueError(n)))
    if type(result) is not dict:
        raise ValueError("Research source must be a JSON object")
    return result


def require_exact_int(obj: dict, field: str, minimum: int = 0) -> int:
    n = obj.get(field)
    if type(n) is not int or n < minimum:
        raise ValueError(f"Invalid source integer {field}")
    return n


def validate_precommit(config: dict) -> None:
    if type(config) is not dict:
        raise ValueError("Missing frozen research protocol")
    if config.get("schema_version") != "robot-detector-real-spot-transfer-precommit-v1":
        raise ValueError("Wrong research protocol schema")
    expected = [{"symbol":symbol,"day":day,"role":role} for symbol,day,role in (
        ("LTCUSDT","2026-11-20","prospective_next_day_same_instrument"),
        ("BCHUSDT","2026-11-20","prospective_same_day_distinct_spot_instrument")
    )]
    if config.get("frozen_new_sources_before_any_archive_download") != expected:
        raise ValueError("Research sources must not be replaced post-hoc")
    if config.get("clock_offsets_seconds") != list(PHASES):
        raise ValueError("Post-hoc phase selection forbidden")
    if config.get("complete_bin_width_seconds") != 30:
        raise ValueError("Binwidth was changed after precommit")
    if config.get("fixed_rng_seeds") != list(NULL_SEEDS):
        raise ValueError("Frozen shuffle seeds changed")
    if [v.get("key") for v in config.get("nulls",[]) if type(v) is dict] != list(NULLS):
        raise ValueError("Null algorithm set changed")
    if (config.get("no_hypothesis_or_threshold_fitting_on_new_sources") is not True
            or config.get("no_data_dependent_phase_selection") is not True):
        raise ValueError("Invalid precommitted non-tuning gate")
    if not str(config.get("primary_endpoint","")).startswith("at phase 0, actual count"):
        raise ValueError("Precommitted endpoint changed")
    if not str(config.get("noncommercial_license","")).startswith("CC BY-NC-SA 4.0"):
        raise ValueError("Missing noncommercial research license")


def analyze(config: dict, reports: list[dict]) -> dict:
    validate_precommit(config)
    if type(reports) is not list or len(reports) != 2:
        raise ValueError("Both fixed new sources must be observed, no substitute")
    audited = []
    for (symbol, day), report in zip(FROZEN, reports):
        if type(report) is not dict:
            raise ValueError("Unexpected source report shape")
        name, date_obj, url, check = frozen_source(symbol,day)
        if (report.get("symbol") != symbol or report.get("utc_date") != day
                or report.get("source_url") != url
                or report.get("checksum_url") != check
                or report.get("dataset_license") != RESEARCH_LICENSE):
            raise ValueError("Wrong date, symbol, URL, or source terms")
        checksum = report.get("source_zip_sha256")
        if type(checksum) is not str or not re.fullmatch("[a-f0-9]{64}", checksum):
            raise ValueError("Invalid or missing source checksum SHA256")
        for key in ("provider_published_checksum_matched",
                    "trade_ids_strictly_increasing",
                    "exchange_event_timestamps_monotonic"):
            if report.get(key) is not True:
                raise ValueError(f"Absent original source validation: {key}")
        for key in ("l2_orderbook_present","all_exchange_trades_independently_verified",
                    "market_specific_false_alarm_rate_estimated",
                    "real_world_owner_count_known","tuned_detector_or_threshold",
                    "live_or_commercial_trading_enabled",
                    "raw_trades_or_ids_exported",
                    "commercial_use_allowed_without_license"):
            if report.get(key) is not False:
                raise ValueError(f"Unjustified original report claim {key}")
        count = require_exact_int(report,"public_trade_count",1)
        buys = require_exact_int(report,"aggressive_buy_prints")
        sells = require_exact_int(report,"aggressive_sell_prints")
        if buys+sells != count:
            raise ValueError("Public trade-side counts do not conserve")
        first_id = require_exact_int(report,"first_trade_id")
        last_id = require_exact_int(report,"last_trade_id")
        gaps = require_exact_int(report,"missing_ids_inside_observed_range")
        if last_id-first_id+1 != count+gaps:
            raise ValueError("Public trade IDs and reported gaps inconsistent")
        start = int(datetime.combine(date_obj,time(),timezone.utc).timestamp())*1_000_000
        if not(start <= require_exact_int(report,"first_public_timestamp_us")
               <= require_exact_int(report,"last_public_timestamp_us")
               < start+86_400_000_000):
            raise ValueError("Source timestamps not from frozen full UTC day")
        desc = report.get("clock_origin_descriptive_v1")
        if (type(desc) is not dict or desc.get("predeclared_origin_seconds") != list(PHASES)
                or desc.get("source_event_count") != count
                or desc.get("all_source_prints_accounted_for_each_phase") is not True
                or desc.get("threshold_or_best_phase_selected") is not False):
            raise ValueError("Not the frozen 0/10/20 source phase bins")
        orig = desc.get("variants")
        if type(orig) is not list or len(orig) != 3:
            raise ValueError("Missing original public phase descriptors")
        checks = [report.get(key) for key in NULLS]
        if any(type(x) is not dict for x in checks):
            raise ValueError("Both frozen null controls required")
        for key, n in zip(NULLS, checks):
            if (n.get("source_event_count") != count
                    or n.get("clock_phases_seconds") != list(PHASES)
                    or n.get("same_public_tape_reused_in_phase_and_null_analyses") is not True
                    or n.get("market_false_discovery_rate_calibrated") is not False
                    or n.get("physical_robot_identification_validated") is not False
                    or n.get("optimal_phase_selected") is not False
                    or n.get("commercial_or_live_trading_allowed") is not False
                    or n.get("raw_print_timestamps_or_labels_exported") is not False
                    or n.get("same_timestamp_side_vector_clusters_preserved") is not
                    (key==NULLS[1])):
                raise ValueError("Null model metadata or release gate changed")
            v=n.get("variants")
            if type(v) is not list or len(v) != 3:
                raise ValueError("Expected 3 frozen null phases")
        rows = []
        for phase_index, phase in enumerate(PHASES):
            p = orig[phase_index]
            if type(p) is not dict or p.get("origin_seconds") != phase:
                raise ValueError("Original phase order changed")
            nonempty = require_exact_int(p,"eligible_nonempty_bins")
            observed = require_exact_int(p,"strictly_buy_one_sided_bins_or_sell_one_sided_bins")
            excluded = require_exact_int(p,"boundary_trades_excluded")
            valid = require_exact_int(p,"public_prints_in_full_bins")
            full = (86_400-phase)//30
            if (p.get("bin_width_seconds") != 30
                    or p.get("fully_contained_utc_day_bins") != full
                    or nonempty > full or observed > nonempty
                    or valid+excluded != count or valid < nonempty):
                raise ValueError("Original clock bin coverage mismatch")
            nullrows=[]
            for null, label in zip(checks,("weak_per_print","strong_equal_size_cluster")):
                c = null["variants"][phase_index]
                if (type(c) is not dict or c.get("origin_seconds") != phase
                        or c.get("observed_one_sided_bins") != observed
                        or c.get("observed_complete_nonempty_bins") != nonempty
                        or c.get("excluded_utc_edge_prints") != excluded
                        or c.get("observed_prints_in_full_bins") != valid
                        or c.get("predeclared_null_seeds") != list(NULL_SEEDS)
                        or c.get("num_predeclared_weak_null_replicates") != 8
                        or c.get("statistical_p_value_or_FDR_calibrated") is not False):
                    raise ValueError("Control group or original public bin reconciliation failed")
                nums = [c.get("null_one_sided_bin_count_"+suffix)
                        for suffix in ("min","median","max")]
                if (any(type(n) not in (float,int) for n in nums)
                        or not 0<=nums[0]<=nums[1]<=nums[2]<=nonempty):
                    raise ValueError("Impossible null one-sided bin envelope")
                nullrows.append({
                    "null_model": label,
                    "controls": 8,
                    "one_sided_count_min": nums[0],
                    "one_sided_count_median": nums[1],
                    "one_sided_count_max": nums[2],
                    "observed_minus_null_median": observed-nums[1],
                    "observed_above_all_eight_controls": observed>nums[2],
                    "descriptive_control_comparison_not_p_value": True,
                })
            rows.append({
                "origin_seconds":phase,
                "complete_bins":full,
                "nonempty_bins":nonempty,
                "source_prints_in_complete_bins":valid,
                "source_prints_excluded_at_utc_edges":excluded,
                "observed_one_sided_bins":observed,
                "observed_one_sided_fraction_of_nonempty_bins":observed/nonempty if nonempty else None,
                "null_controls":nullrows,
            })
        audited.append({
            "symbol":symbol,"utc_day":day,
            "precommitted_source_role":config["frozen_new_sources_before_any_archive_download"][len(audited)]["role"],
            "source_zip_sha256":checksum,
            "provider_sha256_matched":True,
            "source_prints":count,
            "source_first_id":first_id,
            "source_last_id":last_id,
            "missing_ids_within_observed_range":gaps,
            "phase0_strong_envelope_hypothesis_met":rows[0]["null_controls"][1]["observed_above_all_eight_controls"],
            "clock_bin_comparisons":rows,
        })
    return {
        "schema_version":SCHEMA,
        "protocol":"research/real_spot_transfer_precommit_20261121.json",
        "precommit_stored_prior_to_any_source_download":True,
        "research_type":"prospective descriptive transfer, NOT a labelled robot-detector holdout",
        "provider":"Binance Vision public spot original raw trades",
        "noncommercial_cc_by_nc_sa_restriction":True,
        "true_distinct_market_sessions":2,
        "distinct_utc_dates":1,
        "source_count_total":sum(x["source_prints"] for x in audited),
        "primary_phase_offset_seconds":0,
        "primary_strong_envelope_met_in_all_precommitted_sources":all(
            x["phase0_strong_envelope_hypothesis_met"] for x in audited
        ),
        "reports":audited,
        "no_fdr_or_statistical_significance_claimed":True,
        "no_l2_or_known_physical_owner_truth":True,
        "not_licensed_for_live_or_commercial_trading":True,
        "no_source_raw_tapes_or_print_ids_exported":True,
        "caveats":[
            "One market date and two instruments do not provide independent market regimes.",
            "Eight shuffles are neither a calibrated p-value nor a legitimate bot FDR estimate.",
            "Source archives are independently fetched with provider SHA-256, not independently exchange completeness certified.",
            "Equal-timestamp group vectors are swapped across timestamps; never assume the joint side vector is fixed to its own timestamp.",
            "No order-book L2, actual parent order labels or individual account/owner truth.",
        ]
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ltc-report",required=True,type=Path)
    parser.add_argument("--bch-report",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        parser.error("Cannot overwrite original prospective source evidence")
    config=load_json(PROTOCOL,max_bytes=12_000)
    reports=[load_json(p) for p in (args.ltc_report,args.bch_report)]
    summary=analyze(config,reports)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as file:
        json.dump(summary,file,sort_keys=True,indent=2,allow_nan=False)
        file.write("\n")
    print("REAL_SPOT_PRECOMMITTED_TRANSFER",json.dumps({
        "source_count_total":summary["source_count_total"],
        "case_count":len(summary["reports"]),
        "descriptive_primary_cases_passing":sum(
            x["phase0_strong_envelope_hypothesis_met"] for x in summary["reports"]),
        "physical_owner_fdr_estimated":False,
        "commercial_trading_licensed":False
    },sort_keys=True))


if __name__=="__main__":
    main()
