"""Strict prior-only L2 gate for descriptive public timing scans.

No claim of complete exchange coverage: caller-supplied snapshots are observed
samples, and this gate only checks local causal eligibility.
"""
from collections import Counter
from tools.public_period_scan import scan_public_timestamps

_ALLOWED = frozenset(("timestamp_ms", "covered", "source_precision_ms"))
def scan_with_prior_l2(timestamps_ms, snapshots, *, max_age_ms=1000):
    """Return scan only with an unambiguous strictly prior public L2 sample.

    A newer timestamp-imprecise update blocks fallback to older covered
    quotes. Conflicting tied observations abstain independent of input order.
    No exchange-completeness, ownership, p-value or market FDR claim.
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
    samples.sort(key=lambda s: (s["timestamp_ms"], s["source_precision_ms"], s["covered"]))
    reasons = []
    for t in sorted(set(stamps)):
        prior_observed = [s for s in samples if s["timestamp_ms"] <= t
                          and t - s["timestamp_ms"] <= max_age_ms]
        eligible = [s for s in prior_observed
                    if s["timestamp_ms"] + s["source_precision_ms"] < t]
        if not eligible:
            reasons.append("NO_STRICT_PRIOR_L2")
            continue
        chosen_stamp = eligible[-1]["timestamp_ms"]
        # A newer update with overlapping precision invalidates fallback.
        if any(s["timestamp_ms"] >= chosen_stamp
               and s["timestamp_ms"] + s["source_precision_ms"] >= t
               for s in prior_observed):
            reasons.append("AMBIGUOUS_NEWER_L2_ORDER")
            continue
        tied_latest = [s for s in eligible if s["timestamp_ms"] == chosen_stamp]
        if len({(s["covered"], s["source_precision_ms"]) for s in tied_latest}) > 1:
            reasons.append("CONFLICTING_TIED_L2_SNAPSHOTS")
        elif not eligible[-1]["covered"]:
            reasons.append("PRIOR_L2_COVERAGE_MISSING")
    base["l2_quality"] = {
        "status": "ELIGIBLE_LOCAL_OBSERVATION_ONLY" if not reasons and base["gap_count"] else "ABSTAIN",
        "observed_snapshot_count": len(samples),
        "unique_print_count": base["unique_timestamps"],
        "failed_unique_prints": len(reasons),
        "reasons": dict(sorted(Counter(reasons).items())),
        "exchange_completeness": "UNKNOWN",
    }
    if reasons or not base["gap_count"]:
        base["status"] = "ABSTAIN_L2_QUALITY"
        for period in base["periods"]:
            period["fraction"] = None
            period["hits"] = None
    return base
