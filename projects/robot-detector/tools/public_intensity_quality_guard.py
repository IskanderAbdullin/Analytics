"""Conservative precision and previous-only L2 gate for an uncalibrated sampler.

Constructed source-free diagnostic only. The wrapper does not validate a real
exchange feed or justify inferential p-values or owner identification.
"""
from __future__ import annotations

from tools.public_period_l2_gate import scan_with_prior_l2
from tools.public_intensity_conditioned_null import intensity_conditioned_cluster_sample


def quality_gated_intensity_sample(timestamps_ms, snapshots, *,
                                   source_precision_ms, seed=404, replicate=0):
    """Never sample on coarse/unknown timing or insufficient strictly prior L2."""
    if type(seed) is not int or type(replicate) is not int or replicate < 0:
        raise ValueError("seed and nonnegative replicate must be integers")
    stamps = list(timestamps_ms)
    public = scan_with_prior_l2(stamps, snapshots)
    outcome = {
        "status": "ABSTAIN",
        "reason": None,
        "sampled_timestamps_ms": None,
        "l2_quality": public["l2_quality"],
        "exchange_completeness": "UNKNOWN",
        "inference": "NO_PVALUE_NO_OWNER_ID_NO_MARKET_FDR",
    }
    if public["gap_count"] == 0:
        outcome["reason"] = "ABSTAIN_NO_GAPS"
    elif type(source_precision_ms) is not int or source_precision_ms != 1:
        outcome["reason"] = "UNSUPPORTED_OR_UNKNOWN_PRINT_PRECISION"
    elif public["l2_quality"]["status"] != "ELIGIBLE_LOCAL_OBSERVATION_ONLY":
        outcome["reason"] = "PRIOR_L2_QUALITY"
    else:
        outcome["status"] = "DESCRIPTIVE_SOURCE_FREE_ONLY"
        outcome["sampled_timestamps_ms"] = intensity_conditioned_cluster_sample(
            stamps, seed=seed, replicate=replicate)
    return outcome
