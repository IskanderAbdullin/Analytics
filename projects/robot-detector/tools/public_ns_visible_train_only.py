"""Train ns M1-v3 on same public type4-visible event process as evaluation.

Frozen protocol: docs/CONDITIONAL_NS_VISIBLE_TRAIN_ONLY_PREREG_20261122.md
No arbitrary event timestamps supplied by caller; they derive from bound
public paired original message/post-event BBO source. Structural only.
"""
from dataclasses import dataclass

from tools.public_intensity_rescaling import Abstain
from tools.public_lobster_ns_time import UNIT
from tools.public_ns_source_binding import (
    BoundPublicNsSource, audit_structural_unique_bound_sources,
)
from tools.public_m1_v3_ns_l2 import (
    NsTrainingRun, _valid_ns, fit_ns_m1_v3_train_only,
)

MAX_SOURCE_FREE_TRAIN_WORLDS=1000


@dataclass(frozen=True)
class NsBoundVisibleTrainingSpec:
    original_run_label: str
    start_ns: int
    end_ns: int
    bound_public_source: BoundPublicNsSource
    unit: str=UNIT
    interval_complete: bool=True


@dataclass(frozen=True)
class NsVisibleTrainOnlyModel:
    model: object
    safe_aggregate: dict


def fit_ns_m1v3_from_visible_bound_sources(specs):
    """Train only on source-bound visible type4 public clusters and same BBO."""
    if type(specs) not in (tuple,list) or not 1<=len(specs)<=MAX_SOURCE_FREE_TRAIN_WORLDS:
        raise Abstain("EMPTY_OR_EXCESSIVE_ORIGINAL_SOURCE_TRAINING")
    for x in specs:
        if type(x) is not NsBoundVisibleTrainingSpec or type(x.bound_public_source) is not BoundPublicNsSource:
            raise Abstain("MISSING_TYPED_ORIGINAL_SOURCE_TRAINING_BINDING")
    registry=audit_structural_unique_bound_sources(
        [spec.bound_public_source for spec in specs],
    )
    original=[]
    visible_execs=hidden_execs=visible_clusters=0
    for spec in specs:
        bound=spec.bound_public_source
        if (type(spec.original_run_label) is not str or
            bound.original_run_label!=spec.original_run_label or
            type(spec.unit) is not str or spec.unit!=UNIT or
            type(spec.interval_complete) is not bool or not spec.interval_complete or
            not _valid_ns(spec.start_ns) or not _valid_ns(spec.end_ns) or
            spec.start_ns>=spec.end_ns):
            raise Abstain("TRAINING_RUN_SOURCE_ID_TIME_OR_COVERAGE_MISMATCH")
        p=bound.projection
        times=p.visible_type4_trade_cluster_times_ns
        if type(times) is not tuple or any(not spec.start_ns<t<spec.end_ns for t in times):
            raise Abstain("VISIBLE_TRAINING_TRADE_OUTSIDE_OR_UNVERIFIED_SOURCE_WINDOW")
        original.append(NsTrainingRun(
            bound.original_run_label,spec.start_ns,spec.end_ns,times,
            p.post_event_bbo_snapshots,UNIT,1,True,
        ))
        a=p.safe_aggregate
        if (type(a) is not dict or
            type(a.get("visible_type4_executions")) is not int or
            type(a.get("hidden_type5_executions_not_direction_inferred")) is not int or
            a.get("visible_type4_exact_trade_timestamp_clusters")!=len(times)):
            raise Abstain("SOURCE_VISIBILITY_COUNTS_FORGED_OR_MISSING")
        visible_execs+=a["visible_type4_executions"]
        visible_clusters+=len(times)
        hidden_execs+=a["hidden_type5_executions_not_direction_inferred"]
    trained=fit_ns_m1_v3_train_only(original)
    return NsVisibleTrainOnlyModel(trained,{
        "status":"SOURCE_FREE_TYPED_VISIBLE_TYPE4_TRAIN_ONLY_NOT_CALIBRATED",
        "structural_original_training_sources":registry["source_labels"],
        "training_visible_type4_execution_rows":visible_execs,
        "training_unique_type4_ns_timestamp_clusters":visible_clusters,
        "training_hidden_type5_executions_not_modelled":hidden_execs,
        "low_cluster_count":trained.low_cluster_count,
        "high_cluster_count":trained.high_cluster_count,
        "low_exposure_ns":trained.low_exposure_ns,
        "high_exposure_ns":trained.high_exposure_ns,
        "low_rate_per_second":trained.low_rate_per_second,
        "high_rate_per_second":trained.high_rate_per_second,
        "source_globally_independent_verified":False,
        "source_complete_exchange_capture_verified":False,
        "real_market_fdr_known":False,
        "physical_owner_identity_known":False,
        "raw_source_event_order_or_book_rows_exported":False,
    })
