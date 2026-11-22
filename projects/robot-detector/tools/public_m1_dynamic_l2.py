"""M1-v2: conservative dynamically lagged public-L2 spread intensity, source-free.

Prospective protocol: docs/CONDITIONAL_M1_DYNAMIC_LAGGED_L2_PREREG_20261122.md
1000ms fixed lag is an engineering sensitivity choice, NOT exchange latency.
The caller asserts continuous book/source coverage; code cannot verify real feed.
"""
from bisect import bisect_right
from dataclasses import dataclass
from math import isfinite
import re

from tools.public_intensity_rescaling import Abstain, Exposure

LAG_MS = 1000
MAX_STALE_MS = 10000
MAX_SAFE_MS = 2**53 - 1
MAX_RECORDS_PER_RUN = 100000
_ALLOWED_BOOK_FIELDS = frozenset(("timestamp_ms", "bid_price", "ask_price", "complete"))


@dataclass(frozen=True)
class M1DynamicTrainingRun:
    run_id: str
    start_ms: int
    end_ms: int
    cluster_times_ms: tuple
    snapshots: tuple
    source_precision_ms: int = 1
    interval_complete: bool = True


@dataclass(frozen=True)
class M1DynamicEvaluationWindow:
    run_id: str
    start_ms: int
    end_ms: int
    snapshots: tuple
    source_precision_ms: int = 1
    interval_complete: bool = True


@dataclass(frozen=True)
class M1DynamicRateModel:
    median_relative_spread: float
    low_rate_per_second: float
    high_rate_per_second: float
    training_run_ids: tuple
    low_cluster_count: int
    high_cluster_count: int
    low_exposure_ms: int
    high_exposure_ms: int


def _valid_ms(t):
    return type(t) is int and 0 <= t <= MAX_SAFE_MS


def _valid_quote(v):
    return type(v) in (int, float) and isfinite(v) and v > 0


def _quality_segments(run):
    if type(run) not in (M1DynamicTrainingRun, M1DynamicEvaluationWindow):
        raise Abstain("INVALID_DYNAMIC_RUN")
    if type(run.run_id) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}",run.run_id) is None:
        raise Abstain("INVALID_SOURCE_RUN_IDENTIFIER")
    if not _valid_ms(run.start_ms) or not _valid_ms(run.end_ms) or run.start_ms >= run.end_ms:
        raise Abstain("INVALID_DYNAMIC_OBSERVATION_WINDOW")
    if type(run.source_precision_ms) is not int or run.source_precision_ms != 1:
        raise Abstain("UNVERIFIED_OR_COARSE_TIMESTAMP_PRECISION")
    if type(run.interval_complete) is not bool or not run.interval_complete:
        raise Abstain("MISSING_ASSERTED_SOURCE_CONTINUITY")
    if type(run.snapshots) not in (list, tuple) or not 1 <= len(run.snapshots) <= MAX_RECORDS_PER_RUN:
        raise Abstain("NO_PRIOR_OR_EXCESSIVE_L2_RECORDS")
    times, spreads = [], []
    for book in run.snapshots:
        if type(book) is not dict or set(book) != _ALLOWED_BOOK_FIELDS:
            raise Abstain("FORBIDDEN_OR_MISSING_PUBLIC_L2_FIELD")
        t, complete = book["timestamp_ms"], book["complete"]
        if not _valid_ms(t) or t >= run.end_ms or type(complete) is not bool or not complete:
            raise Abstain("INVALID_FUTURE_OR_INCOMPLETE_L2")
        bid, ask = book["bid_price"], book["ask_price"]
        if not _valid_quote(bid) or not _valid_quote(ask) or bid > ask:
            raise Abstain("INVALID_OR_CROSSED_PUBLIC_BBO")
        mid = (ask + bid)/2.0
        spread = (ask - bid)/mid
        if not isfinite(spread) or spread < 0:
            raise Abstain("INVALID_PUBLIC_RELATIVE_SPREAD")
        if times and t <= times[-1]:
            raise Abstain("TIED_OR_UNSORTED_L2_TIMESTAMPS")
        times.append(t)
        spreads.append(spread)
    effective = [t + LAG_MS for t in times]
    first_idx = bisect_right(effective, run.start_ms) - 1
    if first_idx < 0:
        raise Abstain("MISSING_STRICT_PRIOR_LAGGED_BBO")
    bounds = [run.start_ms] + [t for t in effective if run.start_ms < t < run.end_ms] + [run.end_ms]
    segments = []
    for left,right in zip(bounds,bounds[1:]):
        idx = bisect_right(effective,left) - 1
        if idx < 0 or left >= right or right - times[idx] > MAX_STALE_MS:
            raise Abstain("INCOMPLETE_OR_STALE_DYNAMIC_L2_EXPOSURE")
        segments.append((left,right,spreads[idx]))
    if not segments or sum(right-left for left,right,_ in segments) != run.end_ms-run.start_ms:
        raise Abstain("MISSING_DYNAMIC_EXPOSURE")
    return tuple(segments)


def _training_clusters(run, segments):
    ts = run.cluster_times_ms
    if type(ts) not in (tuple,list) or len(ts) > MAX_RECORDS_PER_RUN:
        raise Abstain("INVALID_OR_EXCESSIVE_CLUSTER_TIMES")
    if any(not _valid_ms(t) for t in ts) or list(ts) != sorted(ts):
        raise Abstain("INVALID_OR_UNSORTED_TRAINING_CLUSTERS")
    if any(not run.start_ms < t < run.end_ms for t in ts):
        raise Abstain("EVENT_OUTSIDE_TRAINING_EXPOSURE")
    unique = tuple(dict.fromkeys(ts))
    begins = [left for left,_,_ in segments]
    assignments = []
    for t in unique:
        idx = bisect_right(begins,t)-1
        if idx < 0 or t >= segments[idx][1]:
            raise Abstain("NONCAUSAL_EVENT_EXPOSURE")
        assignments.append(segments[idx][2])
    return assignments


def _weighted_spread_median(weighted):
    ranked = sorted(weighted, key=lambda x:x[0])
    duration = sum(w for _,w in ranked)
    if duration <= 0:
        raise Abstain("NO_TRAINING_EXPOSURE")
    so_far = 0
    for spread,w in ranked:
        so_far += w
        if 2*so_far >= duration:
            return spread
    raise Abstain("INVALID_MEDIAN_EXPOSURE")


def fit_m1_dynamic_train_only(runs):
    if type(runs) not in (list,tuple) or not runs:
        raise Abstain("NO_TRAINING_SOURCE_RUNS")
    ids = set()
    training = []
    weighted = []
    for run in runs:
        if type(run) is not M1DynamicTrainingRun:
            raise Abstain("INVALID_TRAINING_RUN_INPUT")
        segments = _quality_segments(run)
        if run.run_id in ids:
            raise Abstain("DUPLICATE_OR_DEPENDENT_TRAINING_SOURCE_RUN")
        ids.add(run.run_id)
        clusters = _training_clusters(run,segments)
        training.append((segments,clusters))
        weighted.extend((spread,right-left) for left,right,spread in segments)
    boundary = _weighted_spread_median(weighted)
    counts=[0,0]
    exposure=[0,0]
    for segments,clusters in training:
        for left,right,spread in segments:
            exposure[0 if spread<=boundary else 1] += right-left
        for spread in clusters:
            counts[0 if spread<=boundary else 1] += 1
    if min(counts) <= 0 or min(exposure) <= 0:
        raise Abstain("MISSING_STRATUM_OR_ZERO_CLUSTER_RATE")
    low=counts[0]*1000.0/exposure[0]
    high=counts[1]*1000.0/exposure[1]
    if not isfinite(low) or not isfinite(high) or low<=0 or high<=0:
        raise Abstain("INVALID_DYNAMIC_TRAINED_RATE")
    return M1DynamicRateModel(boundary,low,high,tuple(sorted(ids)),
                              counts[0],counts[1],exposure[0],exposure[1])


def predict_m1_dynamic_exposure(model,window):
    if type(model) is not M1DynamicRateModel or type(window) is not M1DynamicEvaluationWindow:
        raise Abstain("INVALID_DYNAMIC_M1_MODEL_OR_EVALUATION")
    if (type(model.training_run_ids) is not tuple or
        type(model.median_relative_spread) not in (int,float) or
        not isfinite(model.median_relative_spread) or model.median_relative_spread<0 or
        any(type(rate) not in (int,float) or not isfinite(rate) or rate<=0
            for rate in (model.low_rate_per_second,model.high_rate_per_second))):
        raise Abstain("INVALID_DYNAMIC_TRAINED_MODEL")
    if window.run_id in model.training_run_ids:
        raise Abstain("TRAIN_EVALUATION_SOURCE_RUN_OVERLAP")
    segments = _quality_segments(window)
    out=[]
    for left,right,spread in segments:
        rate=(model.low_rate_per_second if spread<=model.median_relative_spread
              else model.high_rate_per_second)
        out.append(Exposure(left,right,rate,complete=True,causal=True))
    return tuple(out)
