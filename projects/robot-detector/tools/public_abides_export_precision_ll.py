"""Exact source-time vs legacy CSV microsecond quantization LL falsifier.

Frozen prereg: docs/ABIDES_EXPORTED_US_LL_QUANTIZATION_PREREG_20261122.md
No new ABIDES simulator runs, independent source tape or owner identities.
"""
from math import isclose, log
import json

from tools.abides_export import _date_utc
from tools.public_abides_m1v4_nontarget_panel import _case,_frozen_train,_ns
from tools.public_abides_m0_m1v4_ll import evaluate_abides_public_fixed_m0_m1v4


CASES=(
    ("ONE_EXACT_NS_EXEC",("34222.5",)),
    ("TWO_EXACT_SAME_NS_SPLIT_FILLS",("34222.5","34222.5")),
    ("TWO_SOURCE_EVENTS_ONE_NS_APART",("34222.5","34222.500000001")),
)
QUOTES=(("34220",102),("34222.5",104),("34223",102))


def abides_lossy_us_clock_LL_falsifier():
    model=_frozen_train()
    results=[]
    for name,prints in CASES:
        original=_case("clock-source-free-"+name,"34222","34226",prints,QUOTES)
        stats=evaluate_abides_public_fixed_m0_m1v4(model,original)
        results.append({
            "constructed_source_free_case":name,
            "source_public_executions":len(prints),
            "exact_distinct_ns_public_clusters":stats["heldout_unique_exact_ns_exec_clusters"],
            "old_csv_distinct_microsecond_text_timestamps":len(set(_date_utc(_ns(s)) for s in prints)),
            "M0_LL":stats["m0_full_window_LL"],
            "M1v4_LL":stats["m1_full_window_LL"],
            "M1v4_minus_M0_LL":stats["m1_minus_m0_LL"],
            "M0_complete_time_integral":stats["m0_full_window_integral"],
            "M1v4_complete_time_integral":stats["m1_full_window_integral"],
            "real_market_fdr_known":False,
            "physical_owner_identity_known":False,
        })
    one,same,apart=results
    if (one["exact_distinct_ns_public_clusters"]!=1 or
        same["exact_distinct_ns_public_clusters"]!=1 or
        apart["exact_distinct_ns_public_clusters"]!=2 or
        apart["old_csv_distinct_microsecond_text_timestamps"]!=1):
        raise AssertionError("Lost distinction between exact ns and old CSV microseconds")
    if not (one["M1v4_LL"]==same["M1v4_LL"] and one["M0_LL"]==same["M0_LL"]):
        raise AssertionError("Exact same-time dependent fills must collapse in fixed point process")
    dm0=apart["M0_LL"]-same["M0_LL"]
    dm1=apart["M1v4_LL"]-same["M1v4_LL"]
    delta=apart["M1v4_minus_M0_LL"]-same["M1v4_minus_M0_LL"]
    if not (isclose(dm0,log(.625),abs_tol=1e-12) and
            isclose(dm1,log(.75),abs_tol=1e-12) and
            isclose(delta,log(.75/.625),abs_tol=1e-12)):
        raise AssertionError("Registered exact-1ns conditional likelihood difference changed")
    return {
        "status":"SOURCE_FREE_EXACT_NS_VS_LEGACY_US_LL_LOSS_NOT_ORIGINAL_MARKET_RESULT",
        "cases":results,
        "M0_LL_one_extra_distinct_ns_cluster_delta":dm0,
        "M1v4_LL_one_extra_distinct_ns_cluster_delta":dm1,
        "conditional_minus_constant_LL_change_due_to_1ns_clock_distinction":delta,
        "CSV_clock_text_loses_1ns_distinction_for_constructed_pair":True,
        "old_160_original_matching_engine_used_legacy_CSV_for_source_scoring":False,
        "actual_original_ABIDES_submicrosecond_collisions_measured":False,
        "real_market_fdr_known":False,
        "physical_owner_identity_known":False,
        "original_matching_engine_source_worlds_generated":0,
        "raw_market_event_or_private_IDs_exported":False,
    }


if __name__=="__main__":
    print(json.dumps(abides_lossy_us_clock_LL_falsifier(),
                     sort_keys=True,allow_nan=False))
