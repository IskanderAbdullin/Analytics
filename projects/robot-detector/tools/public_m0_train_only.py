"""Train-only source-free M0 cluster-rate baseline; NOT statistical calibration.

Protocol: docs/CONDITIONAL_M0_TRAIN_ONLY_PREREG_20261122.md
No market labels, owners, oracle identifiers or evaluation observations accepted.
"""
from dataclasses import dataclass
from math import isfinite

from tools.public_intensity_rescaling import Abstain, Exposure


@dataclass(frozen=True)
class TrainingRun:
    start_ms: int
    end_ms: int
    cluster_times_ms: tuple


@dataclass(frozen=True)
class M0ConstantRate:
    rate_per_second: float
    training_run_count: int
    training_cluster_count: int
    training_exposure_ms: int


def _valid_ms(value):
    return type(value) is int and value >= 0


def _validate_window(start_ms, end_ms):
    if not _valid_ms(start_ms) or not _valid_ms(end_ms) or start_ms >= end_ms:
        raise Abstain("INVALID_OBSERVATION_WINDOW")


def fit_m0_train_only(runs):
    """Fit only from explicitly supplied training runs; caller must audit split."""
    if not isinstance(runs, (list, tuple)) or not runs:
        raise Abstain("NO_TRAINING_RUNS")
    count = 0
    duration = 0
    for run in runs:
        if type(run) is not TrainingRun:
            raise Abstain("INVALID_TRAINING_RUN")
        _validate_window(run.start_ms, run.end_ms)
        ts = run.cluster_times_ms
        if not isinstance(ts, (tuple, list)) or any(not _valid_ms(t) for t in ts):
            raise Abstain("INVALID_CLUSTER_TIMES")
        if list(ts) != sorted(ts):
            raise Abstain("UNSORTED_CLUSTER_TIMES")
        if any(not (run.start_ms < t < run.end_ms) for t in ts):
            raise Abstain("OUT_OF_WINDOW_CLUSTER")
        count += len(set(ts))
        duration += run.end_ms - run.start_ms
    if count <= 0 or duration <= 0:
        raise Abstain("NO_TRAINING_CLUSTERS")
    rate = count * 1000.0 / duration
    if not isfinite(rate) or rate <= 0:
        raise Abstain("INVALID_TRAINED_RATE")
    return M0ConstantRate(rate, len(runs), count, duration)


def predict_m0_exposure(model, start_ms, end_ms):
    """Predict fixed intensity without accepting any evaluation event counts."""
    if type(model) is not M0ConstantRate or not isfinite(model.rate_per_second) or model.rate_per_second <= 0:
        raise Abstain("INVALID_TRAINED_MODEL")
    _validate_window(start_ms, end_ms)
    return (Exposure(start_ms, end_ms, model.rate_per_second, complete=True, causal=True),)
