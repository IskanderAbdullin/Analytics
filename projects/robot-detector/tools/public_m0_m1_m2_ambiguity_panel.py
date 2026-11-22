"""Constructed public-tape M0/M1/M2 identifiability boundary, not source data.

Frozen: docs/CONDITIONAL_PUBLIC_TAPE_AMBIGUITY_PREREG_20261122.md
All public-only algorithms MUST be invariant to an unobserved private story.
"""
import json
from math import fsum, isfinite

from tools.public_intensity_rescaling import Abstain, rescaled_cluster_gaps
from tools.public_m0_train_only import TrainingRun, fit_m0_train_only, predict_m0_exposure
from tools.public_m1_train_only import (
    M1TrainingRun, M1EvaluationWindow, fit_m1_train_only, predict_m1_exposure,
)
from tools.public_m1_dynamic_l2 import (
    M1DynamicTrainingRun, M1DynamicEvaluationWindow,
    fit_m1_dynamic_train_only, predict_m1_dynamic_exposure,
)
from tools.public_m2_train_only import M2Run, fit_m2_train_only, evaluate_m2_run
from tools.public_m2_rescaled_gaps import m2_rescaled_cluster_gaps

PERIODIC_PUBLIC_TAPE = (20100, 21000, 21900, 22800)
MOMENTUM_NON_TARGET_TAPE = (20100, 20101, 20102, 22800)
IRREGULAR_NON_TARGET_TAPE = (20100, 20710, 21930, 22850)
WINDOW_START = 20000
WINDOW_END = 23000


def _book(ts, ask=102.):
    return {"timestamp_ms": ts, "bid_price": 100., "ask_price": ask, "complete": True}


def _old_book(ts, ask=102.):
    return dict(_book(ts, ask), source_precision_ms=1)


def toy_models_train_only():
    """Training records are predeclared independent toy observations, not source."""
    m0 = fit_m0_train_only([TrainingRun(0, 5000, (100, 500, 2000, 3000, 4500))])
    m2 = fit_m2_train_only([M2Run("m2train", 0, 5000, (100, 500, 2000, 3000, 4500))])
    dynamic = fit_m1_dynamic_train_only([
        M1DynamicTrainingRun("low-world", 2000, 5000, (2500, 4200),
                             (_book(0), _book(3000, 104.))),
        M1DynamicTrainingRun("high-world", 10000, 13000, (11000, 12000),
                             (_book(8000, 104.), _book(10500))),
    ])
    original_m1 = fit_m1_train_only([
        M1TrainingRun("old-low", 2000, 2400, (2100,), _old_book(1800), True),
        M1TrainingRun("old-high", 3000, 3400, (3200,), _old_book(2800, 104.), True),
    ])
    return m0, dynamic, m2, original_m1


def _gap_aggregate(gaps):
    if not gaps or any(not isfinite(x) or x <= 0 for x in gaps):
        raise Abstain("INCOMPLETE_OR_NONPOSITIVE_CONSTRUCTED_GAPS")
    return {
        "count": len(gaps),
        "integral_sum": fsum(gaps),
        "integral_mean": fsum(gaps)/len(gaps),
        "integral_min": min(gaps),
        "integral_max": max(gaps),
    }


def public_only_tape_aggregate(cluster_times, trained=None):
    """No private story or source-oracle parameter can enter this function."""
    m0,m1dyn,m2,m1old=trained or toy_models_train_only()
    event_times = tuple(cluster_times)
    m2_run = M2Run("source_free_evaluation", WINDOW_START, WINDOW_END, event_times)
    # Validate the complete toy public event window before either rate model.
    score = evaluate_m2_run(m2,m2_run)
    m0_exposure = predict_m0_exposure(m0, WINDOW_START, WINDOW_END)
    l2_window = M1DynamicEvaluationWindow(
        "source_free_evaluation", WINDOW_START, WINDOW_END,
        (_book(18500), _book(20500, 104.)),
    )
    dyn_exposure = predict_m1_dynamic_exposure(m1dyn,l2_window)
    m0_gaps = rescaled_cluster_gaps(event_times,m0_exposure)
    dyn_gaps = rescaled_cluster_gaps(event_times,dyn_exposure)
    m2_gaps = m2_rescaled_cluster_gaps(m2,m2_run)
    # Original stable M1 cannot carry a 4.5s-old quote through this 3s
    # toy window. Its abstention is a coverage result, NOT a market miss.
    try:
        predict_m1_exposure(m1old,M1EvaluationWindow(
            "source_free_evaluation", WINDOW_START, WINDOW_END,
            _old_book(18500),True))
        old_status = "ELIGIBLE"
    except Abstain:
        old_status = "ABSTAIN_SOURCE_FREE_AGE_GATE"
    return {
        "classification": "CONSTRUCTED_PUBLIC_ONLY_NOT_ACTOR_OR_MARKET_INFERENCE",
        "unique_public_clusters": score.unique_clusters,
        "m0_rescaled_gap_aggregate": _gap_aggregate(m0_gaps),
        "m1v2_rescaled_gap_aggregate": _gap_aggregate(dyn_gaps),
        "m2_rescaled_gap_aggregate": _gap_aggregate(m2_gaps),
        "m2_out_of_train_log_likelihood": score.log_likelihood,
        "old_stable_m1_quality_status": old_status,
        "dynamic_m1_quality_status": "ELIGIBLE_ASSERTED_LOCAL_COVERAGE_ONLY",
        "dynamic_m1_segments": len(dyn_exposure),
        "source_completeness_independently_verified": False,
        "physical_owner_identity_known": False,
        "real_market_fdr_known": False,
    }


def constructed_nonidentifiability_panel():
    trained = toy_models_train_only()
    return {
        "status": "DETERMINISTIC_SOURCE_FREE_IDENTIFIABILITY_NEGATIVE",
        "public_tapes": {
            "unrelated_periodic_public_observation": public_only_tape_aggregate(PERIODIC_PUBLIC_TAPE,trained),
            "non_target_momentum_public_observation": public_only_tape_aggregate(MOMENTUM_NON_TARGET_TAPE,trained),
            "non_target_irregular_public_observation": public_only_tape_aggregate(IRREGULAR_NON_TARGET_TAPE,trained),
        },
        "same_public_tape_can_have_distinct_hidden_world_stories": True,
        "hidden_owner_count_deducible": False,
        "new_ABIDES_source_runs": 0,
    }


if __name__ == "__main__":
    print(json.dumps(constructed_nonidentifiability_panel(), sort_keys=True, indent=2))
