"""Lossy microsecond clock identifies only LL interval, not precise source LL.

Frozen docs/ABIDES_US_CLOCK_LL_IDENTIFICATION_SET_PREREG_20261122.md.
One coarse-time bucket only, full model rates locally constant. NOT CI/FDR.
"""
from math import isfinite,log

from tools.public_intensity_rescaling import Abstain

COARSE_PRECISION="microseconds_only_original_ns_unavailable"
MAX_FILLS=100000
NS_TICKS_PER_MICROSECOND=1000


def microsecond_bucket_LL_gain_identification_set(
    observed_fill_rows, *,
    conditional_rate_per_second,
    constant_rate_per_second,
    fixed_integrated_M0_minus_M1,
    source_clock_precision=COARSE_PRECISION,
    whole_bucket_rate_constant=True,
):
    """Algebraically sharp set over 1..min(k,1000) unknown distinct ns ticks."""
    if type(observed_fill_rows) is not int or not 1<=observed_fill_rows<=MAX_FILLS:
        raise Abstain("INVALID_OR_UNBOUNDED_PUBLIC_MICROSECOND_BUCKET_FILL_COUNT")
    if type(source_clock_precision) is not str or source_clock_precision!=COARSE_PRECISION:
        raise Abstain("SOURCE_TIME_PRECISION_UNKNOWN_OR_NOT_LOSSY_MICROSECONDS")
    if type(whole_bucket_rate_constant) is not bool or not whole_bucket_rate_constant:
        raise Abstain("UNKNOWN_OR_CROSSING_L2_RATE_REGIME_WITHIN_MICROSECOND")
    if (type(conditional_rate_per_second) not in (int,float) or
        type(constant_rate_per_second) not in (int,float) or
        type(fixed_integrated_M0_minus_M1) not in (int,float)):
        raise Abstain("INVALID_PUBLIC_INTENSITY_OR_FULL_WINDOW_COMPENSATOR_TYPE")
    try:
        rate_a=float(conditional_rate_per_second)
        rate_b=float(constant_rate_per_second)
        offset=float(fixed_integrated_M0_minus_M1)
    except (OverflowError,ValueError,TypeError) as exc:
        raise Abstain("UNSAFE_OR_UNREPRESENTABLE_PUBLIC_RATE") from exc
    if (not all(isfinite(x) for x in (rate_a,rate_b,offset)) or
        rate_a<=0 or rate_b<=0):
        raise Abstain("NONFINITE_OR_NONPOSITIVE_PUBLIC_MODEL_RATE")
    log_ratio=log(rate_a)-log(rate_b)
    d_min,d_max=1,min(observed_fill_rows,NS_TICKS_PER_MICROSECOND)
    possible=(d_min*log_ratio+offset,d_max*log_ratio+offset)
    low,high=min(possible),max(possible)
    if not all(isfinite(x) for x in (log_ratio,low,high)):
        raise Abstain("UNREPRESENTABLE_PUBLIC_LL_GAIN_IDENTIFICATION_SET")
    return {
        "status":"SOURCE_FREE_MICROSECOND_CLOCK_LL_PARTIAL_IDENTIFICATION_ONLY",
        "source_clock_precision_assumption":COARSE_PRECISION,
        "coarse_bucket_public_execution_rows":observed_fill_rows,
        "possible_distinct_original_ns_clusters_min":d_min,
        "possible_distinct_original_ns_clusters_max":d_max,
        "lower_bound_conditional_minus_constant_LL":low,
        "upper_bound_conditional_minus_constant_LL":high,
        "identification_width_LL":high-low,
        "NOT_a_statistical_confidence_interval":True,
        "original_nanosecond_timestamp_sequence_known":False,
        "rate_constant_across_coarse_bucket_asserted":True,
        "independent_source_completeness_verified":False,
        "physical_owner_identity_known":False,
        "real_market_fdr_known":False,
        "original_source_runs_generated":0,
        "raw_market_source_rows_exported":False,
    }
