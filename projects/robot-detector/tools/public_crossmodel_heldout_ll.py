"""Frozen-source-free three-tape M0/M1v2/M2 predictive log-likelihood comparison.

Prospective design: docs/CONDITIONAL_CROSSMODEL_HELDOUT_LL_PREREG_20261122.md
No source-run, holdout, oracle/owner, calibrated significance or market FDR.
"""
import json
from math import isfinite

from tools.public_fixed_intensity_likelihood import heldout_fixed_intensity_log_likelihood
from tools.public_m0_train_only import predict_m0_exposure
from tools.public_m1_dynamic_l2 import M1DynamicEvaluationWindow, predict_m1_dynamic_exposure
from tools.public_m2_train_only import M2Run, evaluate_m2_run
from tools.public_m0_m1_m2_ambiguity_panel import (
    WINDOW_START, WINDOW_END,
    PERIODIC_PUBLIC_TAPE, MOMENTUM_NON_TARGET_TAPE, IRREGULAR_NON_TARGET_TAPE,
    toy_models_train_only, _book,
)

FROZEN_CONSTRUCTED_TAPES=(
    ("unrelated_periodic_hard_negative", PERIODIC_PUBLIC_TAPE),
    ("non_target_momentum_burst", MOMENTUM_NON_TARGET_TAPE),
    ("non_target_irregular_control", IRREGULAR_NON_TARGET_TAPE),
)


def score_frozen_constructed_public_tape(cluster_times, trained):
    """No private story parameter; all parameter estimation belongs to training."""
    m0,m1v2,m2,_ = trained
    times=tuple(cluster_times)
    m0_exposure=predict_m0_exposure(m0, WINDOW_START, WINDOW_END)
    m1v2_exposure=predict_m1_dynamic_exposure(
        m1v2,M1DynamicEvaluationWindow(
            "source_free_evaluation",WINDOW_START,WINDOW_END,
            (_book(18500),_book(20500,104.))
        )
    )
    kw={"start_ms":WINDOW_START,"end_ms":WINDOW_END}
    s0=heldout_fixed_intensity_log_likelihood(times,m0_exposure,**kw)
    s1=heldout_fixed_intensity_log_likelihood(times,m1v2_exposure,**kw)
    s2=evaluate_m2_run(m2,M2Run("source_free_evaluation",WINDOW_START,WINDOW_END,times))
    numbers=(s0["heldout_log_likelihood"],s1["heldout_log_likelihood"],s2.log_likelihood)
    if not all(isfinite(v) for v in numbers):
        raise ValueError("UNEXPECTED_NONFINITE_PREDICTIVE_SCORE")
    return {
        "status":"CONSTRUCTED_NON_TARGET_PREDICTION_NOT_ACTOR_DETECTION",
        "unique_public_clusters":s2.unique_clusters,
        "source_asserted_continuity_not_independently_verified":True,
        "m1v2_exposure_segments":len(m1v2_exposure),
        "m0_heldout_log_likelihood":numbers[0],
        "m1v2_heldout_log_likelihood":numbers[1],
        "m2_heldout_log_likelihood":numbers[2],
        "m1v2_minus_m0_log_likelihood":numbers[1]-numbers[0],
        "m2_minus_m0_log_likelihood":numbers[2]-numbers[0],
        "m2_fixed_trained_mu_per_second":m2.mu_per_second,
        "m2_fixed_trained_amplitude_per_second":m2.amplitude_per_second,
        "m2_fixed_tau_seconds":m2.tau_seconds,
        "physical_owner_identity_known":False,
        "real_market_fdr_known":False,
    }


def all_three_frozen_non_target_ll_panel():
    trained=toy_models_train_only()
    return {
        "status":"COMPLETE_FROZEN_SOURCE_FREE_NON_TARGET_LIKELIHOOD_PANEL",
        "source_runs_generated":0,
        "new_source_seeds_used":0,
        "all_tapes_are_constructed_and_previously_inspected":True,
        "within_world_and_source_independence_not_established":True,
        "calibrated_significance_claimed":False,
        "tapes":{name:score_frozen_constructed_public_tape(times,trained)
                 for name,times in FROZEN_CONSTRUCTED_TAPES},
    }


if __name__=="__main__":
    print(json.dumps(all_three_frozen_non_target_ll_panel(),sort_keys=True,indent=2))
