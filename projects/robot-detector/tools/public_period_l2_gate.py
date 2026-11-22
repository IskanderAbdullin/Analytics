"""Strict prior-only L2 gate for descriptive public timing scans.

No claim of complete exchange coverage: caller-supplied snapshots are observed
samples, and this gate only checks local causal eligibility.
"""
from tools.public_period_scan import scan_public_timestamps

_ALLOWED = frozenset(("timestamp_ms", "covered", "source_precision_ms"))
def scan_with_prior_l2(timestamps_ms, snapshots, *, max_age_ms=1000):
    """Return scan only when every unique print has an eligible earlier L2 sample.

    Strictly rejects future/equal-time snapshots, missing coverage and unknown
    source timestamp precision. No p-values, ownership or market FDR.
    """
    if type(max_age_ms) is not int or max_age_ms <= 0:
        raise ValueError("max_age_ms must be positive integer")
    stamps = list(timestamps_ms)
    base = scan_public_timestamps(stamps)
    samples = list(snapshots)
    for s in samples:
        if type(s) is not dict or set(s) != _ALLOWED:
            raise ValueError("L2 sample requires exact public quality field allowlist")
        t, p, c = s["timestamp_ms"], s["source_precision_ms"], s["covered"]
        if type(t) is not int or t < 0 or type(p) is not int or p <= 0 or type(c) is not bool:
            raise ValueError("Invalid L2 timestamp/precision/coverage")
    samples.sort(key=lambda s: s["timestamp_ms"])
    reasons = []
    for t in sorted(set(stamps)):
        eligible = [s for s in samples if s["timestamp_ms"] + s["source_precision_ms"] < t
                    and t - s["timestamp_ms"] <= max_age_ms]
        if not eligible:
            reasons.append("NO_STRICT_PRIOR_L2")
        elif not eligible[-1]["covered"]:
            reasons.append("PRIOR_L2_COVERAGE_MISSING")
    base["l2_quality"] = {
        "status": "ELIGIBLE_LOCAL_OBSERVATION_ONLY" if not reasons and base["gap_count"] else "ABSTAIN",
        "observed_snapshot_count": len(samples),
        "unique_print_count": base["unique_timestamps"],
        "failed_unique_prints": len(reasons),
        "reasons": dict(sorted(__import__("collections").Counter(reasons).items())),
        "exchange_completeness": "UNKNOWN",
    }
    if reasons or not base["gap_count"]:
        base["status"] = "ABSTAIN_L2_QUALITY"
        for period in base["periods"]:
            period["fraction"] = None
            period["hits"] = None
    return base
