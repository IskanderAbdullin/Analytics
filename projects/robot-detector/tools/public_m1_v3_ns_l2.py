"""Strict ns-unit M1-v3 trained only on causal public post-event BBO, source-free.

Method frozen: docs/CONDITIONAL_M1_V3_NS_LAGGED_L2_PREREG_20261122.md
No market owner labels, real exchange completeness certification or FDR.
"""
from bisect import bisect_right
from dataclasses import dataclass
from math import isfinite
import re

from tools.public_intensity_rescaling import Abstain
from tools.public_lobster_ns_time import (
    UNIT, MAX_SAFE_TICK, NS_PER_SECOND, SESSION_START, SESSION_END,
)

LAG_NS = NS_PER_SECOND
MAX_AGE_NS = 10 * NS_PER_SECOND
MAX_SOURCE_RECORDS = 100000
SESSION_START_NS = int(SESSION_START) * NS_PER_SECOND
SESSION_END_NS = int(SESSION_END) * NS_PER_SECOND
_BOOK_KEYS = frozenset(("timestamp_ns", "bid_price", "ask_price", "complete"))


@dataclass(frozen=True)
class NsTrainingRun:
    run_id: str
    start_ns: int
    end_ns: int
    cluster_times_ns: tuple
    post_event_bbo: tuple
    unit: str = UNIT
    declared_precision_ns: int = 1
    interval_complete: bool = True


@dataclass(frozen=True)
class NsEvaluationWindow:
    run_id: str
    start_ns: int
    end_ns: int
    post_event_bbo: tuple
    unit: str = UNIT
    declared_precision_ns: int = 1
    interval_complete: bool = True


@dataclass(frozen=True)
class NsM1Model:
    training_weighted_median_relative_spread: float
    low_rate_per_second: float
    high_rate_per_second: float
    training_run_ids: tuple
    low_cluster_count: int
    high_cluster_count: int
    low_exposure_ns: int
    high_exposure_ns: int


@dataclass(frozen=True)
class NsExposure:
    start_ns: int
    end_ns: int
    rate_per_second: float
    source_complete_asserted: bool = True
    causal_lagged: bool = True


def _valid_ns(t):
    return type(t) is int and SESSION_START_NS <= t <= SESSION_END_NS and t <= MAX_SAFE_TICK


def _valid_price(value):
    if type(value) not in (float, int):
        return False
    try:
        return isfinite(value) and value > 0
    except (OverflowError, TypeError, ValueError):
        return False


def _quality_exposure(run):
    if type(run) not in (NsTrainingRun, NsEvaluationWindow):
        raise Abstain("INVALID_OR_UNTYPED_NS_SOURCE_RUN")
    if type(run.run_id) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}",run.run_id) is None:
        raise Abstain("INVALID_NANOS_SOURCE_RUN_ID")
    if not _valid_ns(run.start_ns) or not _valid_ns(run.end_ns) or run.start_ns >= run.end_ns:
        raise Abstain("INVALID_NS_OBSERVATION_WINDOW")
    if run.unit != UNIT or type(run.unit) is not str:
        raise Abstain("INCORRECT_OR_UNTAGGED_SOURCE_TIME_UNIT")
    if type(run.declared_precision_ns) is not int or run.declared_precision_ns != 1:
        raise Abstain("UNVERIFIED_OR_COARSE_NS_SOURCE_PRECISION")
    if type(run.interval_complete) is not bool or not run.interval_complete:
        raise Abstain("UNVERIFIED_SOURCE_EVENT_OR_L2_CONTINUITY")
    books = run.post_event_bbo
    if type(books) not in (tuple, list) or not 1 <= len(books) <= MAX_SOURCE_RECORDS:
        raise Abstain("MISSING_OR_EXCESSIVE_POST_EVENT_PUBLIC_BBO")

    ticks = []
    spreads = []
    for book in books:
        if type(book) is not dict or set(book) != _BOOK_KEYS:
            raise Abstain("FORBIDDEN_OR_INCOMPLETE_PUBLIC_BOOK_FIELDS")
        t, complete = book["timestamp_ns"], book["complete"]
        if not _valid_ns(t) or t >= run.end_ns or type(complete) is not bool or not complete:
            raise Abstain("INVALID_FUTURE_OR_MISSING_NS_BOOK")
        bid, ask = book["bid_price"], book["ask_price"]
        if not _valid_price(bid) or not _valid_price(ask) or bid > ask:
            raise Abstain("INVALID_OR_CROSSED_PUBLIC_BBO")
        mid = (float(ask) + float(bid)) / 2
        spread = (float(ask) - float(bid)) / mid
        if mid <= 0 or not isfinite(mid) or not isfinite(spread) or spread < 0:
            raise Abstain("NONFINITE_NS_PUBLIC_RELATIVE_SPREAD")
        if ticks and t <= ticks[-1]:
            raise Abstain("UNSORTED_OR_TIED_POST_EVENT_PUBLIC_BOOKS")
        ticks.append(t)
        spreads.append(spread)
    effective = [t + LAG_NS for t in ticks]
    if bisect_right(effective, run.start_ns) == 0:
        raise Abstain("NO_CAUSALLY_LAG_ELIGIBLE_PRIOR_BBO")
    cutoffs = [run.start_ns] + [t for t in effective if run.start_ns < t < run.end_ns] + [run.end_ns]
    segments = []
    for left, right in zip(cutoffs, cutoffs[1:]):
        idx = bisect_right(effective, left) - 1
        if idx < 0 or left >= right or right - ticks[idx] > MAX_AGE_NS:
            raise Abstain("GAPPED_OR_STALE_NS_PUBLIC_L2_EXPOSURE")
        segments.append((left, right, spreads[idx]))
    if sum(right-left for left,right,_ in segments) != run.end_ns-run.start_ns:
        raise Abstain("NS_EXPOSURE_TILING_NOT_COMPLETE")
    return tuple(segments)


def _cluster_strata(run, segments):
    times = run.cluster_times_ns
    if type(times) not in (tuple, list) or len(times) > MAX_SOURCE_RECORDS:
        raise Abstain("INVALID_OR_EXCESSIVE_NS_PRINT_CLUSTERS")
    if any(not _valid_ns(t) for t in times) or list(times) != sorted(times):
        raise Abstain("INVALID_OR_UNSORTED_NS_PUBLIC_CLUSTERS")
    if any(not run.start_ns < t < run.end_ns for t in times):
        raise Abstain("NS_PUBLIC_CLUSTER_OUTSIDE_TRAINING_WINDOW")
    begins = [left for left,_,_ in segments]
    grouped = tuple(dict.fromkeys(times))
    output = []
    for t in grouped:
        idx = bisect_right(begins,t)-1
        if idx < 0 or t >= segments[idx][1]:
            raise Abstain("NONCAUSAL_NS_PUBLIC_CLUSTER_ASSIGNMENT")
        output.append(segments[idx][2])
    return output


def fit_ns_m1_v3_train_only(runs):
    if type(runs) not in (tuple,list) or not runs:
        raise Abstain("NO_ORIGINAL_NS_SOURCE_TRAINING_RUNS")
    ids = set()
    groups = []
    all_weighted = []
    for run in runs:
        if type(run) is not NsTrainingRun:
            raise Abstain("INVALID_NS_TRAINING_SOURCE")
        segs = _quality_exposure(run)
        if run.run_id in ids:
            raise Abstain("DUPLICATE_OR_DEPENDENT_NS_TRAINING_RUN_ID")
        ids.add(run.run_id)
        groups.append((segs,_cluster_strata(run,segs)))
        all_weighted.extend((spread,end-start) for start,end,spread in segs)
    weighted = sorted(all_weighted)
    duration = sum(weight for _,weight in weighted)
    cumulative = 0
    median = None
    for spread,weight in weighted:
        cumulative += weight
        if 2*cumulative >= duration:
            median = spread
            break
    if median is None:
        raise Abstain("NS_SOURCE_TRAINING_EXPOSURE_MISSING")
    exposure = [0,0]
    counts = [0,0]
    for segs,events in groups:
        for left,right,spread in segs:
            exposure[0 if spread <= median else 1] += right-left
        for spread in events:
            counts[0 if spread <= median else 1] += 1
    if min(counts) <= 0 or min(exposure) <= 0:
        raise Abstain("ZERO_OR_MISSING_NS_SPREAD_STRATUM")
    rates = [count*NS_PER_SECOND/exptime for count,exptime in zip(counts,exposure)]
    if any(not isfinite(r) or r<=0 for r in rates):
        raise Abstain("INVALID_NS_TRAINING_RATE")
    return NsM1Model(median,rates[0],rates[1],tuple(sorted(ids)),
                     counts[0],counts[1],exposure[0],exposure[1])


def predict_ns_m1_v3_exposure(model, window):
    if type(model) is not NsM1Model or type(window) is not NsEvaluationWindow:
        raise Abstain("INVALID_NS_MODEL_OR_EVAL_WINDOW")
    if type(model.training_run_ids) is not tuple or window.run_id in model.training_run_ids:
        raise Abstain("INVALID_OR_OVERLAPPING_NS_SOURCE_RUN_ID")
    if (type(model.training_weighted_median_relative_spread) not in (int,float) or
        not isfinite(model.training_weighted_median_relative_spread) or
        model.training_weighted_median_relative_spread < 0 or
        any(not _valid_price(v) for v in
            (model.low_rate_per_second,model.high_rate_per_second))):
        raise Abstain("INVALID_NS_TRAINED_MODEL")
    segments = _quality_exposure(window)
    return tuple(NsExposure(left,right,
                            model.low_rate_per_second if spread <= model.training_weighted_median_relative_spread
                            else model.high_rate_per_second)
                 for left,right,spread in segments)
