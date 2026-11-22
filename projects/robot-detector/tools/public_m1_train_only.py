"""Conservative source-free M1 single-prior-BBO slice. NOT calibrated inference.

Frozen before coding: docs/CONDITIONAL_M1_SOURCE_FREE_IMPLEMENTATION_GATE_20261122.md
One locally stable BBO per run is an asserted source-coverage assumption, not proof
of exchange completeness. Any changing/unknown L2 window must abstain.
"""
from dataclasses import dataclass
from math import isfinite
from statistics import median

from tools.public_intensity_rescaling import Abstain, Exposure

_BBO_FIELDS = frozenset({"timestamp_ms", "bid_price", "ask_price", "complete", "source_precision_ms"})
_MAX_AGE_MS = 1000  # frozen technical age gate, not verified vendor specification


@dataclass(frozen=True)
class M1TrainingRun:
    run_id: str
    start_ms: int
    end_ms: int
    cluster_times_ms: tuple
    book_snapshot: dict
    interval_complete: bool


@dataclass(frozen=True)
class M1EvaluationWindow:
    run_id: str
    start_ms: int
    end_ms: int
    book_snapshot: dict
    interval_complete: bool


@dataclass(frozen=True)
class M1SpreadStrata:
    median_relative_spread: float
    low_rate_per_second: float
    high_rate_per_second: float
    training_run_ids: tuple
    low_cluster_count: int
    high_cluster_count: int
    low_exposure_ms: int
    high_exposure_ms: int


def _valid_identifier(run_id):
    return type(run_id) is str and 0 < len(run_id.strip()) <= 128


def _valid_ms(t):
    return type(t) is int and t >= 0


def _valid_price(x):
    try:
        return type(x) in (int, float) and isfinite(x) and x > 0
    except (OverflowError, TypeError, ValueError):
        return False


def _quality_spread(run):
    if not _valid_identifier(run.run_id) or not _valid_ms(run.start_ms) or not _valid_ms(run.end_ms):
        raise Abstain("INVALID_RUN_OR_WINDOW")
    if run.start_ms >= run.end_ms or type(run.interval_complete) is not bool or not run.interval_complete:
        raise Abstain("MISSING_ASSERTED_COMPLETE_EXPOSURE")
    s = run.book_snapshot
    if type(s) is not dict or set(s) != _BBO_FIELDS:
        raise Abstain("FORBIDDEN_OR_MISSING_L2_FIELDS")
    t, precision, complete = s["timestamp_ms"], s["source_precision_ms"], s["complete"]
    if not _valid_ms(t) or type(precision) is not int or precision != 1 or type(complete) is not bool or not complete:
        raise Abstain("UNVERIFIED_CLOCK_OR_INCOMPLETE_L2")
    if not (t + precision < run.start_ms) or run.end_ms - t > _MAX_AGE_MS:
        raise Abstain("SAME_TIME_FUTURE_OR_STALE_L2")
    bid, ask = s["bid_price"], s["ask_price"]
    if not _valid_price(bid) or not _valid_price(ask) or bid > ask:
        raise Abstain("INVALID_OR_CROSSED_BBO")
    rel = (ask - bid) / ((ask + bid) / 2.0)
    if not isfinite(rel) or rel < 0:
        raise Abstain("INVALID_RELATIVE_SPREAD")
    return rel


def fit_m1_train_only(runs):
    """One spread observation per declared training run; no evaluation input."""
    if not isinstance(runs, (tuple, list)) or not runs:
        raise Abstain("NO_TRAINING_RUNS")
    rows = []
    seen = set()
    for run in runs:
        if type(run) is not M1TrainingRun:
            raise Abstain("INVALID_TRAINING_RUN")
        spread = _quality_spread(run)
        if run.run_id in seen:
            raise Abstain("DUPLICATE_OR_DEPENDENT_TRAINING_RUN_ID")
        seen.add(run.run_id)
        times = run.cluster_times_ms
        if not isinstance(times, (list, tuple)) or any(not _valid_ms(t) for t in times):
            raise Abstain("INVALID_TRAINING_CLUSTER_TIMES")
        if list(times) != sorted(times) or any(not (run.start_ms < t < run.end_ms) for t in times):
            raise Abstain("NONCAUSAL_OR_OUTSIDE_TRAINING_EVENTS")
        rows.append((spread, len(set(times)), run.end_ms - run.start_ms))
    boundary = median(r[0] for r in rows)
    clusters = [0, 0]
    exposures = [0, 0]
    for spread, count, duration in rows:
        i = 0 if spread <= boundary else 1
        clusters[i] += count
        exposures[i] += duration
    if min(clusters) <= 0 or min(exposures) <= 0:
        raise Abstain("EMPTY_OR_ZERO_CLUSTER_TRAINING_STRATUM")
    low_rate = clusters[0] * 1000.0 / exposures[0]
    high_rate = clusters[1] * 1000.0 / exposures[1]
    if any(not isfinite(x) or x <= 0 for x in (low_rate, high_rate)):
        raise Abstain("INVALID_TRAINED_RATE")
    return M1SpreadStrata(boundary, low_rate, high_rate, tuple(sorted(seen)),
                          clusters[0], clusters[1], exposures[0], exposures[1])


def predict_m1_exposure(model, window):
    """Fixed evaluation exposure; no evaluation events/labels accepted."""
    if type(model) is not M1SpreadStrata or type(window) is not M1EvaluationWindow:
        raise Abstain("INVALID_M1_PREDICTION_INPUT")
    if (not isfinite(model.median_relative_spread) or model.median_relative_spread < 0 or
        any(type(rate) not in (int, float) or not isfinite(rate) or rate <= 0
            for rate in (model.low_rate_per_second, model.high_rate_per_second))):
        raise Abstain("INVALID_TRAINED_MODEL")
    if window.run_id in model.training_run_ids:
        raise Abstain("TRAIN_EVALUATION_RUN_OVERLAP")
    spread = _quality_spread(window)
    rate = model.low_rate_per_second if spread <= model.median_relative_spread else model.high_rate_per_second
    return (Exposure(window.start_ms, window.end_ms, rate, complete=True, causal=True),)
