"""Strictly predictable M2 cluster time-rescaling, SOURCE-FREE diagnostic only.

Precommitted design: docs/CONDITIONAL_M2_RESCALED_GAPS_PREREG_20261122.md
No p-values, actor labels, market FDR or source independence assumptions.
"""
from math import exp, expm1, isfinite

from tools.public_intensity_rescaling import Abstain
from tools.public_m2_train_only import (
    M2Model, M2Run, _validate_run, evaluate_m2_run,
)


def m2_rescaled_cluster_gaps(model, run):
    """Return exact integrated predictable intensity between distinct clusters.

    lambda(t_i-) excludes the current event; its jump applies only to the
    strictly later interval. No event-based observations are fit here.
    """
    if type(model) is not M2Model or type(run) is not M2Run:
        raise Abstain("INVALID_M2_RESCALE_INPUT")
    if type(model.training_run_ids) is not tuple:
        raise Abstain("INVALID_TRAINING_SOURCE_IDS")
    unique = _validate_run(run)
    if len(unique) < 2:
        raise Abstain("INSUFFICIENT_UNIQUE_CLUSTERS")
    # Reuse exact-M2 validity, causal history and train/eval split guards
    # before any integration is interpreted.
    evaluated = evaluate_m2_run(model, run)
    mu, a, tau = model.mu_per_second, model.amplitude_per_second, model.tau_seconds
    excitation = 0.0
    last_time = None
    out = []
    for left, right in zip(unique, unique[1:]):
        time = (left - run.start_ms) / 1000.0
        if last_time is not None:
            excitation = (excitation + 1.0) * exp(-(time - last_time) / tau)
        delta = (right - left) / 1000.0
        z = mu * delta + a * tau * (excitation + 1.0) * (-expm1(-delta / tau))
        if z <= 0 or not isfinite(z):
            raise Abstain("ZERO_OR_NONFINITE_M2_RESCALED_GAP")
        out.append(z)
        last_time = time
    if len(out) != len(evaluated.pre_event_intensities) - 1:
        raise Abstain("INCONSISTENT_PUBLIC_CLUSTER_COUNT")
    return tuple(out)
