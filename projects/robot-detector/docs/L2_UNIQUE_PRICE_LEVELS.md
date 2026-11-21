# Strict unique-price ordering for public aggregated L2 depth

**2026-11-21 — public order-book structural validation, not a trading detector.**

A true aggregated L2 book represents the **total displayed quantity at each unique price**. It is not an order-by-order L3 feed. Therefore each side's levels must be in **strict** best-to-worst order:
- Bids: price at level `i+1` must be **less** than price at level `i`.
- Asks: price at level `i+1` must be **greater** than price at level `i`.

Earlier code checked only non-strict ordering and silently permitted duplicate prices on one side. For example, the purported bid levels `[(100,7),(100,12)]` are **two entries at the same price**, not two distinct levels; including them as separate levels would inflate or distort the displayed-side liquidity and the previous-bin book imbalance in a public quote/trade correlation.

## Fix and regression

`l2_probe.audit_l2_public` now rejects equal adjacent levels and any reversal rather than assuming duplicates can be counted. Combined with the earlier strict integer scalar checks, price/quantity positivity and bounded depth, this prevents ambiguous L2 structural observations from entering the previous-completed-bin L2 statistic or the strict quote/print join. Quotes with the same **timestamp** but *different snapshots* remain distinct: price-level uniqueness within a snapshot is **not** time-based deduplication.

Six new no-ABIDES Python tests in `tests_l2/test_l2_level_uniqueness.py` verify duplicate bid/ask prices, nonadjacent repeats, strict valid five-level books, duplicate-timestamp preservation and end-to-end rejection of duplicate-price snapshots by downstream quote/trade statistics.

The existing L2 CI runs the full `tests_l2` set and its pinned genuine ABIDES matching-engine smoke. No additional private actor truth or historical real broker account data is introduced.

## Limits

This validator assumes provider/source semantics match *aggregated L2 price levels*. It must **not** be applied unchanged to a raw per-order L3 stream, where multiple resting orders may genuinely share a price. It cannot authenticate an exchange provider or detect incomplete feed delivery. The research remains read-only, with no bot identity, real-market FDR or trading orders. Stage-2 release gate CLOSED.
