"""V2 positive-harmonic public timestamp-gap scan (legacy v1 preserved).

Avoids 0xperiod counts that make <=50ms microbursts look like all 5..60s
cadences. Descriptive only; harmonic aliasing and unrelated periodic
backgrounds remain. No market p-values, owner inference or real FDR.
"""
from __future__ import annotations

from tools.public_period_scan import PERIODS_MS, TOLERANCE_MS, scan_public_timestamps


def positive_harmonic_hit(gap_ms: int, period_ms: int, tolerance_ms: int = 50) -> bool:
    if (type(gap_ms) is not int or gap_ms < 0 or type(period_ms) is not int or
            period_ms <= 0 or type(tolerance_ms) is not int or tolerance_ms < 0):
        raise ValueError("positive integer gap/period and nonnegative integer tolerance required")
    # Round to the closest POSITIVE integer harmonic, never zero.
    harmonic = max(1, (gap_ms + period_ms // 2) // period_ms)
    return abs(gap_ms - harmonic * period_ms) <= tolerance_ms


def scan_positive_harmonics_v2(timestamps_ms) -> dict:
    stamps = list(timestamps_ms)
    if stamps != sorted(stamps):
        raise ValueError("public print timestamps must be sorted")
    baseline = scan_public_timestamps(stamps)
    times = sorted(set(stamps))
    gaps = [b-a for a,b in zip(times,times[1:])]
    baseline["status"] = "DESCRIPTIVE_POSITIVE_HARMONICS_ONLY" if gaps else "ABSTAIN_NO_GAPS"
    baseline["periods"] = [{
        "period_ms": p,
        "tolerance_ms": TOLERANCE_MS,
        "hits": sum(positive_harmonic_hit(g,p,TOLERANCE_MS) for g in gaps),
        "denominator": len(gaps),
        "fraction": (sum(positive_harmonic_hit(g,p,TOLERANCE_MS) for g in gaps)/len(gaps))
                    if gaps else None,
    } for p in PERIODS_MS]
    baseline["method_version"] = "public-positive-harmonic-gap-scan-v2"
    baseline["legacy_v1_warning"] = "v1 aliases sub-50ms zero-harmonic gaps into all periods"
    baseline["inference"] = "DESCRIPTIVE_ONLY_NO_PVALUE_NO_OWNER_ID_NO_MARKET_FDR"
    return baseline
