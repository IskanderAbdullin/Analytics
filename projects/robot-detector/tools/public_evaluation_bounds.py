"""Source-free exact binomial bounds; descriptive only, not real-market FDR."""
import math


def _validate(k, n, alpha):
    if type(k) is not int or type(n) is not int or n <= 0 or not 0 <= k <= n:
        raise ValueError("INVALID_COUNTS")
    if not isinstance(alpha, (float, int)) or isinstance(alpha, bool) or not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("INVALID_ALPHA")


def _cdf(k, n, p):
    if p == 0:
        return 1.0
    if p == 1:
        return float(k == n)
    # Exact binomial probability sum, stable for moderate n and extreme p.
    logs = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
            + i * math.log(p) + (n - i) * math.log1p(-p) for i in range(k + 1)]
    m = max(logs)
    return math.exp(m) * math.fsum(math.exp(x - m) for x in logs)


def upper_one_sided(k, n, alpha=0.05):
    """Clopper-Pearson one-sided upper bound, not multiplicity-adjusted."""
    _validate(k, n, alpha)
    if k == n:
        return 1.0
    if k == 0:
        return 1 - alpha ** (1 / n)
    lo, hi = 0.0, 1.0
    for _ in range(65):
        mid = (lo + hi) / 2
        if _cdf(k, n, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def lower_one_sided(k, n, alpha=0.05):
    """Clopper-Pearson lower bound, with k successes in n independent units."""
    _validate(k, n, alpha)
    if k == 0:
        return 0.0
    if k == n:
        return alpha ** (1 / n)
    lo, hi = 0.0, 1.0
    for _ in range(65):
        mid = (lo + hi) / 2
        if 1 - _cdf(k - 1, n, mid) < alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def conservative_outcome_bounds(alarms, eligible, total, alpha=0.05):
    """Report alarms among eligible, plus abstentions; fail closed on bad coverage."""
    for value in (alarms, eligible, total):
        if type(value) is not int or value < 0:
            raise ValueError("INVALID_COUNTS")
    if not (alarms <= eligible <= total) or total == 0:
        raise ValueError("INVALID_COVERAGE")
    if eligible == 0:
        return {"status": "ABSTAIN", "abstentions": total, "upper_alarm": None, "lower_alarm_all": 0.0}
    return {"status": "ELIGIBLE", "abstentions": total - eligible,
            "upper_alarm": upper_one_sided(alarms, eligible, alpha),
            "lower_alarm_all": lower_one_sided(alarms, total, alpha)}
