"""Exact hypothetical paired-world power bounds; no original source jobs/seeds.

Frozen before evaluation: docs/PAIRED_INDEPENDENT_POWER_GRID_PREREG_20261122.md
Marginal world-level binomial pass probabilities; joint bounds are union/
intersection bounds under unrestricted within-world cohort dependence.
"""
import json
import math
from pathlib import Path

from tools.public_evaluation_bounds import upper_one_sided, lower_one_sided

N_GRID = (100, 160, 250, 400, 600, 1000)
P_POS_GRID = (0.85, 0.90, 0.95)
P_NEG_GRID = (0.0, 0.005, 0.01, 0.02)
FAMILY_ALPHA = 0.05
PER_COMPARISON_ALPHA = FAMILY_ALPHA / 4
POSITIVE_LOWER_GATE = 0.80
NEGATIVE_UPPER_GATE = 0.05


def binomial_tail_probability(n, p, k, *, upper):
    """Inclusive tail, log-sum-exp-free finite sum for bounded n<=1000.

    This is a *marginal* hypothetical Bin(n,p) law; not joint/market power.
    """
    if type(n) is not int or not 1 <= n <= 1000:
        raise ValueError("INVALID_BOUNDED_WORLD_COUNT")
    if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("INVALID_HYPOTHETICAL_PROBABILITY")
    if type(k) is not int or not 0 <= k <= n:
        raise ValueError("INVALID_BINOMIAL_CUTOFF")
    if p == 0:
        return float(0 >= k) if upper else 1.0
    if p == 1:
        return 1.0 if upper else float(n <= k)
    start, stop = (k, n + 1) if upper else (0, k + 1)
    lp, lq, g = math.log(p), math.log1p(-p), math.lgamma(n + 1)
    probs = (math.exp(g - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                      + i * lp + (n - i) * lq) for i in range(start, stop))
    return min(1., max(0., math.fsum(probs)))


def frozen_cutoffs(n):
    """First k with lower L>0.80; last k with upper U<0.05."""
    if type(n) is not int or n not in N_GRID:
        raise ValueError("UNREGISTERED_SAMPLE_SIZE")
    lo, hi = 0, n
    while lo < hi:
        mid = (lo + hi) // 2
        if lower_one_sided(mid, n, PER_COMPARISON_ALPHA) > POSITIVE_LOWER_GATE:
            hi = mid
        else:
            lo = mid + 1
    pos = lo if lower_one_sided(lo, n, PER_COMPARISON_ALPHA) > POSITIVE_LOWER_GATE else None

    lo, hi = -1, n
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if upper_one_sided(mid, n, PER_COMPARISON_ALPHA) < NEGATIVE_UPPER_GATE:
            lo = mid
        else:
            hi = mid
    neg = lo if lo >= 0 else None
    return pos, neg


def preregistered_hypothetical_power_panel():
    """Compute all 6*3*4 scenarios without favorable subset selection."""
    out = []
    cutoffs = {n: frozen_cutoffs(n) for n in N_GRID}
    for n in N_GRID:
        pos, neg = cutoffs[n]
        for p_pos in P_POS_GRID:
            q_pos = 0. if pos is None else binomial_tail_probability(n, p_pos, pos, upper=True)
            for p_neg in P_NEG_GRID:
                q_neg = 0. if neg is None else binomial_tail_probability(n, p_neg, neg, upper=False)
                joint_lower = max(0.0, 1.0 - (1.0-q_pos) - 3.0*(1.0-q_neg))
                joint_upper = min(q_pos, q_neg)
                out.append({
                    "n_original_seed_worlds": n,
                    "hypothetical_positive_success_probability": p_pos,
                    "hypothetical_per_negative_worst_case_error_probability": p_neg,
                    "minimum_positive_alarms_for_lower_gt_080": pos,
                    "maximum_each_negative_errors_for_upper_lt_005": neg,
                    "marginal_positive_gate_power": q_pos,
                    "marginal_single_negative_gate_power": q_neg,
                    "joint_power_lower_union_bound": joint_lower,
                    "joint_power_upper_marginal_bound": joint_upper,
                })
    return {
        "status": "HYPOTHETICAL_SOURCE_FREE_NOT_EMPIRICAL_POWER",
        "original_seed_worlds_only": True,
        "within_world_cross_cohort_independence_assumed": False,
        "source_independence_verified": False,
        "real_market_fdr_known": False,
        "familywise_alpha": FAMILY_ALPHA,
        "per_comparison_alpha": PER_COMPARISON_ALPHA,
        "scenarios": "one TWAP positive plus all three Poisson, fixed20, momentum hard negatives",
        "cases": out,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = json.dumps(preregistered_hypothetical_power_panel(), indent=2, sort_keys=True)
    if args.output:
        p = Path(args.output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
