# Public L2 archive completeness and anti-leakage gate

**2026-11-21 — conservative optional watermark, read-only.**

## Why this check was needed

The earlier [lagged L2 public flow study](L2_LAGGED_BIN.md) correctly uses quote state from the previous 30-second bin, never current or future quotes. However, a historical data *file* may end in the middle of its last trade bin, so an observed current-bin BUY share may not reflect the **completed** interval. A last-seen trade or quote timestamp is *not* by itself evidence that the source delivered all subsequent messages before bin close.

## New contract

`summarize_lagged_book(..., complete_through_ns=...)` takes an optional **caller-supplied exclusive completeness watermark** in simulator nanoseconds. If set, each trade bin with `(bin_ordinal + 1) * bin_width_ns > complete_through_ns` is explicitly marked `current_bin_not_closed_by_watermark`, excluded from the lagged correlation, and does not contribute an observation. A watermark exactly equal to a bin's end is sufficient **only if a reliable upstream source has attested completeness before that exclusive boundary**.

If omitted, previous research output semantics remain backward compatible, **but** the schema now makes the incompleteness explicit:

- `archive_completion_watermark_supplied=false`
- `terminal_bin_may_be_partial_without_watermark=true`
- `completion_watermark_independently_verified=false`

When supplied, its value is recorded as `complete_through_ns` and `archive_completion_watermark_supplied=true`, but `completion_watermark_independently_verified` stays **false**: the analytics function cannot validate that a provider's quote/trade feed or import truly had complete coverage. Supplying the last observed print timestamp as a fabricated watermark would defeat the safety of this gate and must be prohibited at integration boundaries.

The function still rejects invalid price, direction, quantity, negative/noninteger watermark and oversized source input. Clock gaps and absence of a prior completed valid book still result in abstention. This setting does **not** alter trade-by-trade private execution truth, source agent IDs, trading or brokerage account behavior.

## Tests

Six pure Python regression tests in `tests_l2/test_lagged_l2_watermark.py` assert:

1. Without a watermark, all observed bins remain descriptive but explicitly **unverified**.
2. A terminal unclosed interval abstains; advancing the exclusive watermark includes exactly that interval.
3. Appending new prints to an unclosed bin **never changes** previously eligible observations or existing coefficients.
4. A watermark before any eligible bin produces null correlation and complete abstention.
5. Negative, noninteger and bool watermarks fail closed.
6. A good preceding two-sided book cannot override an unclosed current trade bin.

The existing [isolated L2 CI](../../.github/workflows/robot-detector-l2-feasibility.yml) executes these tests on code changes and separately runs pinned ABIDES-NG matching scenarios. This stage changes **data completeness reporting**, **not** research thresholds or model classification.

## Scientific and operational limits

This is an optional protection for future archives. All previously published ABIDES experimental coefficients were computed from their documented exported tapes **without an independently attested external archive completeness watermark**. Do not reinterpret them as verified live or archival complete-bin estimates. ABIDES simulator session end times and broker real-world update sequencing/receipt differ. Any real ingestion code must supply source-specific, monotonically increasing watermarks from a trustworthy feed controller, explicitly distinguish quote and trade coverage and reject feed gaps or dropped messages.

**Research gate remains CLOSED.** No market accuracy, p-values, FDR, inferred physical owner identity, live alert or trading action follows from this feature.
