"""All-case ABIDES source-free hard negatives: LL gain != algorithmic owner.

Frozen first in ABIDES_M1V4_NONTARGET_LL_FALSIFIER_PREREG_20261122.md.
No new original matching-engine seeds, real feed, private oracle or trades.
"""
import json
from datetime import date
from decimal import Decimal
from math import log

from tools.public_abides_epoch_ns_clock import NS,ORIGIN
from tools.public_abides_sparse_l2_screen import screen_abides_public_execution_sparse_l2
from tools.public_abides_full_window_exposure import qualify_abides_full_window_l2_exposure
from tools.public_abides_m0_m1v4_ll import (
    ABIDESPublicOriginalCase,fit_abides_public_m0_m1v4_train_only,
    evaluate_abides_public_fixed_m0_m1v4,
)

DAY_NS=(date(2021,2,5)-ORIGIN).days*86400*NS


def _ns(sec):
    return DAY_NS+int(Decimal(sec)*NS)


def _trade(sec):
    return {"epoch_ns":_ns(sec),"price_cents":101,
            "quantity":1,"aggressor_side":"BUY"}


def _book(sec,ask=102):
    return {"epoch_ns":_ns(sec),"bid_cents":100,
            "ask_cents":ask,"depth_complete":True}


def _case(label,start,end,printed,quoted):
    stream=screen_abides_public_execution_sparse_l2(
        tuple(_trade(t) for t in printed),
        tuple(_book(t,ask) for t,ask in quoted),
        source_run_id=label,simulation_date="20210205",
        window_start_ns=int(Decimal(start)*NS),
        window_end_ns=int(Decimal(end)*NS),
    )
    exposure=qualify_abides_full_window_l2_exposure(
        stream,start_ns=int(Decimal(start)*NS),
        end_ns=int(Decimal(end)*NS),
    )
    return ABIDESPublicOriginalCase(
        label,int(Decimal(start)*NS),int(Decimal(end)*NS),stream,exposure,
    )


def _frozen_train():
    low=_case("nonmarket-train-low","34202","34206",
              ("34202.5","34203.5","34204.25"),
              (("34200",102),("34203",104)))
    high=_case("nonmarket-train-high","34212","34216",
               ("34212.5","34214.25"),
               (("34210",104),("34213",102)))
    return fit_abides_public_m0_m1v4_train_only((low,high))


def fixed_nontarget_public_panel_aggregate():
    """Returns complete, unselected constructed non-target tape comparisons."""
    model=_frozen_train()
    plans=(
        ("SINGLE_PUBLIC_LOW_CLUSTER",("34222.5","34222.5")),
        ("UNRELATED_REGULAR_LOW_CLUSTER_BACKGROUND",("34222.5","34224.5","34225.5")),
        ("UNRELATED_MOMENTUM_LIKE_HIGH_CLUSTER_BURST",("34223.6","34223.7","34223.8")),
    )
    quotes=(("34220",102),("34222.5",104),("34223",102))
    results=[]
    for label,prints in plans:
        scored=evaluate_abides_public_fixed_m0_m1v4(
            model,_case("demo-"+label,"34222","34226",prints,quotes))
        results.append({
            "constructed_non_target_case":label,
            "public_unique_execution_timestamp_clusters":scored["heldout_unique_exact_ns_exec_clusters"],
            "M0_full_window_LL":scored["m0_full_window_LL"],
            "M1v4_full_window_LL":scored["m1_full_window_LL"],
            "M1v4_minus_M0_LL":scored["m1_minus_m0_LL"],
            "physical_owner_identity_known":False,
            "pattern_classifier_label_calibrated":False,
        })
    one,regular,burst=results
    if (one["public_unique_execution_timestamp_clusters"]!=1 or
        regular["public_unique_execution_timestamp_clusters"]!=3 or
        burst["public_unique_execution_timestamp_clusters"]!=3 or
        not one["M1v4_minus_M0_LL"]<0<regular["M1v4_minus_M0_LL"] or
        not burst["M1v4_minus_M0_LL"]<0):
        raise AssertionError("Previously fixed source-free LL non-target controls changed")
    # A hypothetical private ownership story never enters the scoring API.
    again=evaluate_abides_public_fixed_m0_m1v4(
        model,_case("identical-public-tape-new-name","34222","34226",
                    plans[1][1],quotes))
    if again["m1_minus_m0_LL"]!=regular["M1v4_minus_M0_LL"]:
        raise AssertionError("Same public tape gained an invented owner dependency")
    return {
        "status":"SOURCE_FREE_ABIDES_NON_TARGET_LL_FALSIFIER_NOT_MARKET_VALIDATION",
        "cases":results,
        "all_precommitted_public_background_cases_reported":True,
        "same_public_tape_under_different_unobserved_owner_stories_has_same_score":True,
        "source_free_constructed_case_count":len(results),
        "original_independent_ABIDES_engine_source_cases_generated":0,
        "source_feed_completeness_externally_verified":False,
        "actual_market_owner_count_known":False,
        "real_market_fdr_known":False,
        "source_model_predictions_are_not_robot_classifications":True,
        "raw_market_events_or_quote_rows_exported":False,
    }


if __name__=="__main__":
    print(json.dumps(fixed_nontarget_public_panel_aggregate(),
                     sort_keys=True,allow_nan=False))
