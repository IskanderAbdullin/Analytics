"""Source-free public visible trade projection -> frozen ns M1-v3 -> LL.

Prospectively specified in CONDITIONAL_NS_VISIBLE_SOURCE_TO_LIKELIHOOD_PREREG_20261122.md
No vendor raw rows, owner IDs, source calibration or real-market FDR.
"""
from tools.public_intensity_rescaling import Abstain
from tools.public_lobster_ns_time import UNIT
from tools.public_ns_visible_exec_projector import NsVisibleExecutionAndPostEventBBO
from tools.public_m1_v3_ns_l2 import (
    NsEvaluationWindow, NsM1Model, predict_ns_m1_v3_exposure,
)
from tools.public_ns_heldout_likelihood import (
    NsPublicEventWindow, heldout_ns_fixed_intensity_log_likelihood,
)


def score_same_source_visible_exec_ns(projection, trained_model, evaluation_window):
    """Aggregate score only; evaluation source books must match projection."""
    if type(projection) is not NsVisibleExecutionAndPostEventBBO:
        raise Abstain("INVALID_PUBLIC_NS_SOURCE_PROJECTION_TYPE")
    if type(trained_model) is not NsM1Model or type(evaluation_window) is not NsEvaluationWindow:
        raise Abstain("INVALID_TRAIN_FROZEN_MODEL_OR_PUBLIC_EVAL_WINDOW")
    if projection.unit != UNIT or evaluation_window.unit != UNIT:
        raise Abstain("INCOMPATIBLE_NS_EXCHANGE_LOCAL_UNITS")
    if (type(projection.post_event_bbo_snapshots) is not tuple or
        type(evaluation_window.post_event_bbo) is not tuple or
        projection.post_event_bbo_snapshots != evaluation_window.post_event_bbo):
        raise Abstain("EVENT_SOURCE_AND_BOOK_SOURCE_MISMATCH")
    a = projection.safe_aggregate
    if (type(a) is not dict or
        a.get("source_time_unit") != UNIT or
        a.get("source_completeness_independently_verified") is not False or
        a.get("real_market_fdr_known") is not False or
        type(a.get("visible_type4_executions")) is not int or
        type(a.get("visible_type4_exact_trade_timestamp_clusters")) is not int or
        a["visible_type4_exact_trade_timestamp_clusters"] != len(projection.visible_type4_trade_cluster_times_ns) or
        a["visible_type4_executions"] < len(projection.visible_type4_trade_cluster_times_ns)):
        raise Abstain("INCONSISTENT_OR_FORGED_PUBLIC_SOURCE_METADATA")
    # Never clip selected trade events when book exposure window is shorter.
    if any(not evaluation_window.start_ns < t < evaluation_window.end_ns
           for t in projection.visible_type4_trade_cluster_times_ns):
        raise Abstain("VISIBLE_TRADE_OUTSIDE_FROZEN_EVALUATION_WINDOW")
    causal_exposure = predict_ns_m1_v3_exposure(trained_model,evaluation_window)
    observed = NsPublicEventWindow(
        UNIT,evaluation_window.start_ns,evaluation_window.end_ns,
        projection.visible_type4_trade_cluster_times_ns,
        interval_complete=evaluation_window.interval_complete,
    )
    s=heldout_ns_fixed_intensity_log_likelihood(observed,causal_exposure)
    return {
        "status":"SOURCE_FREE_PUBLIC_VISIBLE_EXEC_NS_NOT_ACTOR_CALIBRATED",
        "source_message_rows":a["source_message_and_post_event_book_rows"],
        "visible_type4_executions":a["visible_type4_executions"],
        "visible_type4_distinct_ns_clusters":s["unique_public_clusters"],
        "hidden_type5_executions_excluded":a["hidden_type5_executions_not_direction_inferred"],
        "nonexecution_messages_excluded":a["other_source_message_events_not_visible_type4_trades"],
        "causal_bbo_exposure_segments":s["exposure_segments"],
        "integrated_intensity":s["integrated_intensity"],
        "heldout_log_likelihood":s["heldout_log_likelihood"],
        "source_completeness_independently_verified":False,
        "real_trade_only_ms_coarsening_rate_measured":False,
        "physical_owner_identity_known":False,
        "real_market_fdr_known":False,
        "vendor_raw_source_rows_exported":False,
    }
