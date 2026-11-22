"""One command aggregate-only source-free ns type4 training/heldout reproduction.

Preregistered: docs/NS_VISIBLE_NS_SINGLE_COMMAND_REPRO_PREREG_20261122.md
ONLY constructed public toy records; no source download, seeds or trading.
"""
import json
from decimal import Decimal
from math import log

from tools.public_lobster_ns_time import UNIT, exact_decimal_to_ns
from tools.public_ns_source_binding import (
    bind_public_ns_source, BoundNsEvaluation, score_bound_public_ns_source,
)
from tools.public_ns_visible_train_only import (
    NsBoundVisibleTrainingSpec, fit_ns_m1v3_from_visible_bound_sources,
)
from tools.public_m1_v3_ns_l2 import NsEvaluationWindow


def _ns(x):
    return exact_decimal_to_ns(Decimal(str(x)))


def _msg(time, kind=1, side=-1, ask=102):
    return {
        "timestamp_ns": _ns(time),
        "event_type": kind,
        "resting_side": side,
        "bid_price": 100,
        "ask_price": ask,
        "complete": True,
    }


def source_free_ns_pipeline_aggregate():
    """No event rows/source digests in resulting JSON-compatible summary."""
    low = bind_public_ns_source((
        _msg("34200",1),
        _msg("34202.5",4),
        _msg("34203",2,ask=104),
        _msg("34203.5",4,ask=104),
        _msg("34204.25",4,ask=104),
    ),original_run_label="toy-low-world")
    high = bind_public_ns_source((
        _msg("34210",1,ask=104),
        _msg("34212.5",4,ask=104),
        _msg("34213",2),
        _msg("34214.25",4),
    ),original_run_label="toy-high-world")
    trained = fit_ns_m1v3_from_visible_bound_sources((
        NsBoundVisibleTrainingSpec("toy-low-world",_ns("34202"),_ns("34206"),low),
        NsBoundVisibleTrainingSpec("toy-high-world",_ns("34212"),_ns("34216"),high),
    ))
    ev=bind_public_ns_source((
        _msg("34220",1),
        _msg("34222.5",4,-1),
        _msg("34222.5",4,1,ask=104),
        _msg("34222.5",5,1,ask=104),
        _msg("34223",2),
    ),original_run_label="toy-eval-world")
    bound=BoundNsEvaluation(
        "toy-eval-world",ev.source_public_sha256,
        NsEvaluationWindow("toy-eval-world",_ns("34222"),_ns("34226"),
                           ev.projection.post_event_bbo_snapshots),
    )
    result=score_bound_public_ns_source(ev,trained.model,bound)
    output={
        "status":"SOURCE_FREE_NS_REPRO_NOT_MARKET_VALIDATED",
        "model_unit":UNIT,
        "original_training_source_worlds":trained.safe_aggregate["structural_original_training_sources"],
        "training_visible_clusters":trained.safe_aggregate["training_unique_type4_ns_timestamp_clusters"],
        "training_low_rate":trained.model.low_rate_per_second,
        "training_high_rate":trained.model.high_rate_per_second,
        "evaluation_public_messages":result["source_message_rows"],
        "evaluation_visible_type4_executions":result["visible_type4_executions"],
        "evaluation_visible_type4_clusters":result["visible_type4_distinct_ns_clusters"],
        "evaluation_hidden_type5":result["hidden_type5_executions_excluded"],
        "integrated_intensity":result["integrated_intensity"],
        "heldout_log_likelihood":result["heldout_log_likelihood"],
        "source_accuracy_calibrated":False,
        "real_market_fdr_known":False,
        "physical_owner_identity_known":False,
        "original_ABIDES_or_vendor_source_runs":0,
        "raw_vendor_rows_exported":False,
        "external_source_completeness_verified":False,
        "source_study_execution_authorized":False,
    }
    assert output["original_training_source_worlds"]==2
    assert output["evaluation_visible_type4_clusters"]==1
    assert abs(output["heldout_log_likelihood"]-(log(.75)-2.875))<1e-12
    return output


if __name__=="__main__":
    print(json.dumps(source_free_ns_pipeline_aggregate(),sort_keys=True,allow_nan=False))
