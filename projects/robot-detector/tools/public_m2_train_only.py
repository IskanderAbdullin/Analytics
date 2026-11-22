"""Source-free M2 predictable-history exponential intensity; NOT market detection.

Prospective protocol: docs/CONDITIONAL_M2_PREDICTABLE_HISTORY_PREREG_20261122.md
Fixed grid and tau; never use private agent IDs, oracle labels or test-run fitting.
"""
from dataclasses import dataclass
from math import exp, isfinite, log

from tools.public_intensity_rescaling import Abstain

TAU_SECONDS = 1.0
MU_MULTIPLIERS = (0.5, 1.0, 2.0)
EXCITATION_AMPLITUDES = (0.0, 0.2, 0.4)
MAX_UNIQUE_CLUSTERS = 100_000
MAX_SAFE_TIMESTAMP_MS = 2**53 - 1  # integer milliseconds exactly representable as float


def _finite_real(value):
    if type(value) not in (int, float):
        return False
    try:
        return isfinite(value)
    except (OverflowError, ValueError, TypeError):
        return False


@dataclass(frozen=True)
class M2Run:
    run_id: str
    start_ms: int
    end_ms: int
    cluster_times_ms: tuple
    source_precision_ms: int = 1
    interval_complete: bool = True


@dataclass(frozen=True)
class M2Model:
    mu_per_second: float
    amplitude_per_second: float
    tau_seconds: float
    training_run_ids: tuple
    training_unique_clusters: int
    training_exposure_ms: int
    full_grid_train_log_likelihood: tuple


@dataclass(frozen=True)
class M2Evaluation:
    run_id: str
    unique_clusters: int
    exposure_ms: int
    log_likelihood: float
    pre_event_intensities: tuple
    integrated_intensity: float


def _validate_run(run):
    if type(run) is not M2Run or type(run.run_id) is not str or not 0 < len(run.run_id.strip()) <= 128:
        raise Abstain("INVALID_RUN_OR_IDENTIFIER")
    if (type(run.start_ms) is not int or type(run.end_ms) is not int or
        run.start_ms < 0 or run.start_ms >= run.end_ms):
        raise Abstain("INVALID_EXPOSURE_WINDOW")
    if run.start_ms > MAX_SAFE_TIMESTAMP_MS or run.end_ms > MAX_SAFE_TIMESTAMP_MS:
        raise Abstain("TIMESTAMP_OUTSIDE_SAFE_EXACT_RANGE")
    if (type(run.source_precision_ms) is not int or run.source_precision_ms != 1 or
        type(run.interval_complete) is not bool or not run.interval_complete):
        raise Abstain("UNVERIFIED_PRECISION_OR_COVERAGE")
    ts = run.cluster_times_ms
    if not isinstance(ts, (tuple, list)) or len(ts) > MAX_UNIQUE_CLUSTERS:
        raise Abstain("INVALID_OR_EXCESSIVE_PUBLIC_EVENTS")
    if any(type(t) is not int or t < 0 for t in ts) or list(ts) != sorted(ts):
        raise Abstain("INVALID_OR_UNSORTED_PUBLIC_TIMESTAMPS")
    if any(t > MAX_SAFE_TIMESTAMP_MS for t in ts):
        raise Abstain("TIMESTAMP_OUTSIDE_SAFE_EXACT_RANGE")
    if any(not (run.start_ms < t < run.end_ms) for t in ts):
        raise Abstain("EVENT_OUTSIDE_EXPOSURE")
    return tuple(dict.fromkeys(ts))


def _strictly_previous_score(run, unique, mu, a, tau):
    """O(N) exact log likelihood; each event contributes only AFTER itself."""
    if any(not _finite_real(x) for x in (mu, a, tau)):
        raise Abstain("INVALID_M2_PARAMETERS")
    if mu <= 0 or a < 0 or tau != TAU_SECONDS or a * tau >= 1:
        raise Abstain("UNSTABLE_OR_INVALID_M2_PARAMETERS")
    running = 0.0
    last = None
    pre = []
    log_sum = 0.0
    integral_tail = 0.0
    for timestamp_ms in unique:
        t = (timestamp_ms - run.start_ms) / 1000.0
        if last is not None:
            running = (running + 1.0) * exp(-(t - last) / tau)
        intensity = mu + a * running
        if intensity <= 0 or not isfinite(intensity):
            raise Abstain("INVALID_PREDICTABLE_INTENSITY")
        pre.append(intensity)
        log_sum += log(intensity)
        integral_tail += 1.0 - exp(-((run.end_ms - timestamp_ms) / 1000.0) / tau)
        last = t
    exposure_s = (run.end_ms - run.start_ms) / 1000.0
    integral = mu * exposure_s + a * tau * integral_tail
    score = log_sum - integral
    if not isfinite(score) or not isfinite(integral):
        raise Abstain("INVALID_M2_INTEGRAL")
    return score, tuple(pre), integral


def fit_m2_train_only(runs):
    if not isinstance(runs, (tuple, list)) or not runs:
        raise Abstain("NO_TRAINING_RUNS")
    parsed = []
    seen = set()
    total_clusters = total_exposure_ms = 0
    for run in runs:
        unique = _validate_run(run)
        if run.run_id in seen:
            raise Abstain("DUPLICATE_TRAINING_SOURCE_RUN")
        seen.add(run.run_id)
        parsed.append((run, unique))
        total_clusters += len(unique)
        total_exposure_ms += run.end_ms - run.start_ms
    if total_clusters <= 0:
        raise Abstain("NO_OBSERVED_TRAINING_CLUSTERS")
    baseline = total_clusters * 1000.0 / total_exposure_ms
    if baseline <= 0 or not isfinite(baseline):
        raise Abstain("INVALID_TRAINING_BASELINE")
    all_scores = []
    for c in MU_MULTIPLIERS:
        for a in EXCITATION_AMPLITUDES:
            mu = c * baseline
            score = sum(_strictly_previous_score(run, unique, mu, a, TAU_SECONDS)[0]
                        for run, unique in parsed)
            all_scores.append((c, a, score))
    # Fixed grid maximization; ties prefer lowest excitation then lowest c.
    best_c, best_a, best_score = sorted(all_scores, key=lambda x: (-x[2], x[1], x[0]))[0]
    return M2Model(best_c * baseline, best_a, TAU_SECONDS, tuple(sorted(seen)),
                   total_clusters, total_exposure_ms, tuple(all_scores))


def evaluate_m2_run(model, run):
    if type(model) is not M2Model:
        raise Abstain("INVALID_FITTED_M2_MODEL")
    unique = _validate_run(run)
    if run.run_id in model.training_run_ids:
        raise Abstain("TRAIN_EVALUATION_SOURCE_RUN_OVERLAP")
    score, pre, integral = _strictly_previous_score(
        run, unique, model.mu_per_second, model.amplitude_per_second, model.tau_seconds)
    return M2Evaluation(run.run_id, len(unique), run.end_ms-run.start_ms, score, pre, integral)
