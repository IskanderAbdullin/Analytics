#!/usr/bin/env python3
"""Strict source-free 160-case ABIDES retrospective audit (synthetic-only).

The compact snapshot reconstructs all original seed/cohort decision labels.
An optional original source JSON is validated by the frozen SHA256 and all
160 anonymous rows; it must never supply private agent IDs to inference.
Nominal exact CP intervals assume hypothetical IID simulated Bernoulli
seed/cohort trials. Fixed local seeds cannot certify this, and neither result
is a real-market FDR, owner identity, or p-value.
"""
from __future__ import annotations

import argparse
from collections import Counter
from math import comb, isfinite
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "abides_grid_160_source_aggregate_reconciled_20261121.json"
SEEDS = tuple(range(3301, 3341))
COHORTS = ("poisson_noise_null", "fixed_20s_noise_hard_negative",
           "momentum_noise_hard_negative", "twap_45s_positive")
EXPECTED_SHA = "55394e5dfda274613cb081ee4ad44e9b2b8e051eb2e0f0c361e4ee8016431d62"
REQUIRED_FLAGS = frozenset((
    "not_real_market_data", "real_market_FDR_unknown", "physical_owner_identity_unknown",
    "repeat_is_not_160_additional_independent_cases",
    "method_threshold_phase_and_seed_selection_unchanged",
    "source_positive_eligibility_and_abstentions_explicit",
    "original_raw_events_and_private_agent_ids_not_in_fixture",
))
COHORT_FIELDS = frozenset((
    "type", "public_prints", "unique_execution_timestamps", "l2_snapshots",
    "posthoc_twap_fills", "naive_positive_seeds", "grouped_positive_seeds",
    "naive_abstain_seeds", "grouped_abstain_seeds",
))
ALLOWED_CASE_FIELDS = frozenset((
    "actual_market_owner_identity_or_FDR_known", "eligible_previous_completed_30s_L2_bins",
    "largest_timestamp_cluster_prints", "per_print_abstain_reason",
    "per_print_decision", "per_print_false_alarm", "per_print_hits20",
    "per_print_hits45", "per_print_missed_TWAP", "per_print_ratio_45_over_20",
    "per_unique_abstain_reason", "per_unique_decision", "per_unique_false_alarm",
    "per_unique_missed_TWAP", "per_unique_ratio_45_over_20",
    "per_unique_timestamp_hits20", "per_unique_timestamp_hits45",
    "posthoc_controlled_TWAP_fills", "private_oracle_agent_IDs_entered_public_features",
    "public_L2_snapshot_events", "public_prints", "public_tape_sha256",
    "raw_prints_or_L2_snapshots_exported", "same_timestamp_extra_prints",
    "source_cohort", "source_complete_real_exchange_feed_proven", "source_seed",
    "synthetic_target_present_posthoc", "unique_execution_timestamps",
))


def _exact_keys(obj: dict, keys: set | frozenset, label: str) -> None:
    if type(obj) is not dict or set(obj) != set(keys):
        raise ValueError(f"Unexpected or missing fields in {label}")


def _mask(values: list, label: str) -> set[int]:
    if type(values) is not list or len(values) != len(set(map(str, values))):
        raise ValueError(f"Nonunique {label} list")
    if any(type(x) is not int or x not in SEEDS for x in values):
        raise ValueError(f"Non-frozen seed in {label}")
    return set(values)


def _tail_at_least(k: int, n: int, p: float) -> float:
    return sum(comb(n, i) * p**i * (1-p)**(n-i) for i in range(k, n+1))


def _cdf_at_most(k: int, n: int, p: float) -> float:
    return sum(comb(n, i) * p**i * (1-p)**(n-i) for i in range(k+1))


def nominal_cp_95(k: int, n: int = 40) -> tuple[float, float]:
    if type(k) is not int or type(n) is not int or n != 40 or not 0 <= k <= n:
        raise ValueError("Only exact frozen 40 seed trials permitted")
    alpha_half = .025
    if k == 0:
        low = 0.
    else:
        lo, hi = 0., 1.
        for _ in range(90):
            mid = (lo+hi)/2
            if _tail_at_least(k, n, mid) < alpha_half:
                lo = mid
            else:
                hi = mid
        low = (lo+hi)/2
    if k == n:
        high = 1.
    else:
        lo, hi = 0., 1.
        for _ in range(90):
            mid = (lo+hi)/2
            if _cdf_at_most(k, n, mid) > alpha_half:
                lo = mid
            else:
                hi = mid
        high = (lo+hi)/2
    if not 0 <= low <= k/n <= high <= 1:
        raise AssertionError("Clopper-Pearson numerical inversion failed")
    return round(low,8), round(high,8)


def audit_fixture(data: dict) -> dict:
    if (data.get("schema_version") != "genuine-abides-160-original-compact-reconciled-v1"
        or data.get("classification") != "POSTHOC_SOURCE_ONLY_AUDIT_FROZEN_METHODS_NO_RETUNING"
        or data.get("engine_revision") != "ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242"
        or data.get("precommitted_protocol_blob_sha") !=
          "124f1700d403d731190cb628355ac8fb3fc6e87a"
        or data.get("original_source_run") != 44944144915
        or data.get("original_artifact_id") != 14723036950
        or data.get("repeat_same_seeds_source_run") != 44944168231
        or data.get("repeat_same_seeds_artifact_id") != 14722847672
        or data.get("original_uncompressed_full_source_json_sha256") != EXPECTED_SHA
        or data.get("repeat_uncompressed_full_source_json_sha256") != EXPECTED_SHA
        or data.get("source_full_case_count") != 160
        or data.get("seeds") != list(SEEDS)):
        raise ValueError("Source provenance, full artifact hash or local seeds changed")
    _exact_keys(data.get("interpretation_flags"), REQUIRED_FLAGS, "interpretation")
    if any(v is not True for v in data["interpretation_flags"].values()):
        raise ValueError("Scientific inference limitations were weakened")
    cohorts = data.get("source_cohorts")
    if type(cohorts) is not dict or set(cohorts) != set(COHORTS):
        raise ValueError("Missing negative or injected source cohort")
    expected = {}
    for cohort in COHORTS:
        c = cohorts[cohort]
        is_target = cohort == "twap_45s_positive"
        _exact_keys(c, COHORT_FIELDS | ({"grouped_missed_twap_seeds"} if is_target else set()), cohort)
        if c["type"] != ("injected_positive" if is_target else "negative"):
            raise ValueError("Posthoc simulation cohort label changed")
        if (type(c["public_prints"]) is not int
            or type(c["unique_execution_timestamps"]) is not int
            or not 0 < c["unique_execution_timestamps"] <= c["public_prints"]
            or c["l2_snapshots"] is not None
            or type(c["posthoc_twap_fills"]) is not int
            or (c["posthoc_twap_fills"] > 0) != is_target):
            raise ValueError("Invalid source totals or controlled execution counts")
        pp = _mask(c["naive_positive_seeds"], cohort + ".print_positive")
        gp = _mask(c["grouped_positive_seeds"], cohort + ".grouped_positive")
        pa = _mask(c["naive_abstain_seeds"], cohort + ".print_abstain")
        ga = _mask(c["grouped_abstain_seeds"], cohort + ".grouped_abstain")
        if pp & pa or gp & ga:
            raise ValueError("A seed cannot simultaneously alarm and abstain")
        pm = set(SEEDS) - pp - pa if is_target else set()
        gm = set(SEEDS) - gp - ga if is_target else set()
        if is_target and gm != _mask(c["grouped_missed_twap_seeds"], "grouped_missed"):
            raise ValueError("Controlled TWAP misses suppressed or changed")
        pair = Counter()
        for seed in SEEDS:
            pstatus = "ABSTAIN" if seed in pa else ("TARGET_PATTERN" if seed in pp else "NO_TARGET_PATTERN")
            gstatus = "ABSTAIN" if seed in ga else ("TARGET_PATTERN" if seed in gp else "NO_TARGET_PATTERN")
            pair[(pstatus,gstatus)] += 1
        if sum(pair.values()) != 40:
            raise AssertionError("Some source trials were lost")
        expected[cohort] = {
            "naive_positive":len(pp),"grouped_positive":len(gp),
            "naive_abstain":len(pa),"grouped_abstain":len(ga),
            "naive_missed_TWAP":len(pm),"grouped_missed_TWAP":len(gm),
            "paired_print_only_positive":pair[("TARGET_PATTERN","NO_TARGET_PATTERN")],
            "paired_group_only_positive":pair[("NO_TARGET_PATTERN","TARGET_PATTERN")],
            "nominal_CP95_naive":list(nominal_cp_95(len(pp))),
            "nominal_CP95_grouped":list(nominal_cp_95(len(gp))),
        }
    t = data.get("totals")
    _exact_keys(t, {"source_public_prints", "source_unique_execution_timestamps",
                    "source_L2_snapshots","source_posthoc_controlled_TWAP_fills"}, "totals")
    if (t["source_public_prints"] != sum(c["public_prints"] for c in cohorts.values())
        or t["source_unique_execution_timestamps"] !=
           sum(c["unique_execution_timestamps"] for c in cohorts.values())
        or t["source_L2_snapshots"] != 253386
        or t["source_posthoc_controlled_TWAP_fills"] !=
           sum(c["posthoc_twap_fills"] for c in cohorts.values())):
        raise ValueError("Original source totals no longer conserve")
    return {
        "scope":"genuine_ABIDES_simulation_only_not_real_market",
        "original_source_cases":160,
        "independent_source_ensembles_per_cohort":40,
        "exact_nominal_two_sided_95_CP_requires_hypothetical_IID_seeds":True,
        "physical_owner_count_or_real_market_FDR_known":False,
        "repeat_same_seeds_is_new_holdout":False,
        "all_negative_source_cohorts_retained":True,
        "source_json_uncompressed_sha256":EXPECTED_SHA,
        "per_cohort":expected,
    }


def validate_original_source_bytes(blob: bytes, compact: dict) -> None:
    if hashlib.sha256(blob).hexdigest() != EXPECTED_SHA:
        raise ValueError("Raw original aggregate bytes mismatch source SHA256")
    raw = json.loads(blob)
    if (raw.get("schema_version")!="genuine-abides-public-clock-160source-replication-original-v1"
        or raw.get("original_matching_engine_source_case_count")!=160
        or raw.get("genuine_abides_engine_revision")!=compact["engine_revision"]
        or raw.get("physical_owner_or_real_market_FDR_calibrated") is not False
        or raw.get("raw_source_trades_L2_books_private_agent_IDs_exported") is not False):
        raise ValueError("Original data release source identity or limitations invalid")
    cases = raw["all_original_160_anonymous_case_aggregates"]
    if len(cases)!=160 or {(x["source_seed"],x["source_cohort"]) for x in cases} != (
        {(s,c) for s in SEEDS for c in COHORTS}):
        raise ValueError("Missing, duplicate or substituted original source cases")
    if (sum(x["public_prints"] for x in cases)!=compact["totals"]["source_public_prints"]
        or sum(x["unique_execution_timestamps"] for x in cases)!=
           compact["totals"]["source_unique_execution_timestamps"]
        or sum(x["public_L2_snapshot_events"] for x in cases)!=
           compact["totals"]["source_L2_snapshots"]
        or sum(x["posthoc_controlled_TWAP_fills"] for x in cases)!=
           compact["totals"]["source_posthoc_controlled_TWAP_fills"]):
        raise ValueError("Original source prints/timestamps/L2/TWAP totals changed")
    for x in cases:
        _exact_keys(x, ALLOWED_CASE_FIELDS, "original source-only case")
        cohort = compact["source_cohorts"][x["source_cohort"]]
        s = x["source_seed"]
        for prefix, mask in (("per_print", "naive"), ("per_unique", "grouped")):
            decision = x[prefix+"_decision"]
            expected = ("ABSTAIN" if s in cohort[mask+"_abstain_seeds"] else
                        "TARGET_PATTERN" if s in cohort[mask+"_positive_seeds"] else
                        "NO_TARGET_PATTERN")
            if decision != expected:
                raise ValueError("Original per-source precommitted decision changed")
        if (x["private_oracle_agent_IDs_entered_public_features"] is not False
            or x["raw_prints_or_L2_snapshots_exported"] is not False
            or x["actual_market_owner_identity_or_FDR_known"] is not False
            or not isfinite(x["per_print_ratio_45_over_20"] or 0.0)):
            raise ValueError("Original public-only inference privacy/ratio guard failed")


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-json",type=Path,help="Optional ORIGINAL aggregate-only JSON, never raw market tape")
    args=p.parse_args()
    compact=json.loads(FIXTURE.read_text(encoding="utf-8"))
    result=audit_fixture(compact)
    if args.source_json:
        validate_original_source_bytes(args.source_json.read_bytes(), compact)
        result["full_source_artifact_sha256_matched"]=True
    print("GENUINE_ABIDES_160_POSTHOC_AUDIT",json.dumps(result,sort_keys=True))


if __name__ == "__main__":
    main()
