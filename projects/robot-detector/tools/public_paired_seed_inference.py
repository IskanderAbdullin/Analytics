"""Source-free seed-world paired control diagnostics; not market significance.

Prerecorded: docs/PAIRED_SEED_CLUSTER_INFERENCE_PREREG_20261122.md
Must not use print rows, phases, replay exports or private simulator labels
as independent seed worlds. Cohort labels are for *post-inference* assessment.
"""
from math import comb

from tools.public_evaluation_bounds import (
    MAX_INDEPENDENT_WORLDS, lower_one_sided, upper_one_sided,
)

SCENARIOS = (
    "poisson_noise_null",
    "fixed_20s_noise_hard_negative",
    "momentum_noise_hard_negative",
    "twap_45s_positive",
)
NEGATIVES = SCENARIOS[:3]
POSITIVE = SCENARIOS[-1]
OUTCOMES = ("ALARM", "NO_ALARM", "ABSTAIN")


def _validated(rows, alpha):
    # Reuse exact n/alpha gate to avoid huge fake cohorts or numeric overflow.
    if type(rows) not in (tuple, list) or not rows:
        raise ValueError("NO_ORIGINAL_SEED_WORLDS")
    upper_one_sided(0, len(rows), alpha / 4 if type(alpha) in (int, float) and 0 < alpha < 1 else alpha)
    seen = set()
    checked = []
    for entry in rows:
        if type(entry) is not dict or set(entry) != {"seed", "outcomes"}:
            raise ValueError("FORBIDDEN_OR_MISSING_WORLD_FIELDS")
        seed, statuses = entry["seed"], entry["outcomes"]
        if type(seed) is not int or seed <= 0:
            raise ValueError("INVALID_ORIGINAL_SEED_WORLD_ID")
        if seed in seen:
            raise ValueError("DEPENDENT_REPLAY_OR_DUPLICATED_SEED_WORLD")
        seen.add(seed)
        if type(statuses) is not dict or set(statuses) != set(SCENARIOS):
            raise ValueError("INCOMPLETE_OR_PRIVILEGED_COHORT_FIELDS")
        if any(type(statuses[k]) is not str or statuses[k] not in OUTCOMES for k in SCENARIOS):
            raise ValueError("INVALID_PUBLIC_DECISION_STATUS")
        checked.append(statuses)
    return checked


def paired_seed_world_diagnostic(rows, *, alpha=0.05):
    """Simultaneous conservative marginal CP bounds, paired sign diagnostic.

    This is a deterministic algebraic diagnostic conditional on *actual*
    original-world independence and frozen public-only decisions. The checker
    cannot establish either precondition, and the results are not real FDR.
    """
    observed = _validated(rows, alpha)
    n = len(observed)
    status_counts = {k: {s: sum(v[k] == s for v in observed) for s in OUTCOMES} for k in SCENARIOS}
    positive_success = status_counts[POSITIVE]["ALARM"]
    # Bonferroni across all four predeclared one-sided marginal intervals:
    per_comparison_alpha = alpha / 4
    sens_lower = lower_one_sided(positive_success, n, per_comparison_alpha)
    negative_error_counts = {k: n - status_counts[k]["NO_ALARM"] for k in NEGATIVES}
    upper_neg = {
        k: upper_one_sided(negative_error_counts[k], n, per_comparison_alpha)
        for k in NEGATIVES
    }
    paired_b = paired_c = any_negative_error = 0
    for record in observed:
        p = record[POSITIVE] == "ALARM"
        q = any(record[k] != "NO_ALARM" for k in NEGATIVES)
        any_negative_error += int(q)
        paired_b += int(p and not q)
        paired_c += int(q and not p)
    discordant = paired_b + paired_c
    # Exact conditional one-sided sign/McNemar tail; no normal approximation.
    sign_p = sum(comb(discordant, i) for i in range(paired_b, discordant + 1)) / (2 ** discordant)
    return {
        "status": "SOURCE_FREE_METHOD_DIAGNOSTIC_NOT_CALIBRATED",
        "original_world_count": n,
        "status_counts": status_counts,
        "familywise_alpha": alpha,
        "per_comparison_alpha": per_comparison_alpha,
        "positive_alarm_sensitivity_lower": sens_lower,
        "negative_worst_case_error_counts": negative_error_counts,
        "negative_upper_simultaneous": upper_neg,
        "contrast_lower_vs_worst_negative": sens_lower - max(upper_neg.values()),
        "paired_any_negative_error_count": any_negative_error,
        "paired_discordant_favorable": paired_b,
        "paired_discordant_unfavorable": paired_c,
        "paired_conditional_one_sided_sign_p": sign_p,
        "real_market_fdr_known": False,
        "physical_owner_identity_known": False,
        "independence_established_by_this_checker": False,
    }
