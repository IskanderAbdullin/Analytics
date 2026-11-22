"""Descriptive public timestamp-gap scan; no owner identification or p-values.

Frozen periods/tolerance: docs/PUBLIC_CONDITIONAL_NULL_IDENTIFIABILITY_20261121.md.
"""
from collections import Counter

PERIODS_MS = (5000, 10000, 15000, 20000, 30000, 45000, 60000)
TOLERANCE_MS = 50


def scan_public_timestamps(timestamps_ms):
    stamps = list(timestamps_ms)
    if any(type(t) is not int or t < 0 for t in stamps):
        raise ValueError("Expected nonnegative integer millisecond timestamps")
    unique = sorted(set(stamps))
    gaps = [b - a for a, b in zip(unique, unique[1:])]
    multiplicities = Counter(stamps)
    return {
        "status": "DESCRIPTIVE_ONLY" if gaps else "ABSTAIN_NO_GAPS",
        "unique_timestamps": len(unique),
        "public_print_count": len(stamps),
        "cluster_multiplicity_histogram": dict(sorted(Counter(multiplicities.values()).items())),
        "utc_minute_occupancy": dict(sorted(Counter(t // 60000 for t in unique).items())),
        "gap_count": len(gaps),
        "periods": [
            {
                "period_ms": period,
                "tolerance_ms": TOLERANCE_MS,
                "hits": sum(min(g % period, period - g % period) <= TOLERANCE_MS for g in gaps),
                "denominator": len(gaps),
                "fraction": (sum(min(g % period, period - g % period) <= TOLERANCE_MS for g in gaps) / len(gaps)) if gaps else None,
            }
            for period in PERIODS_MS
        ],
        "inference": "NO_PVALUE_NO_OWNER_ID_NO_MARKET_FDR",
    }
