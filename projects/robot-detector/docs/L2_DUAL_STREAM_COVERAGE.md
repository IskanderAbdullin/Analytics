# Dual-source public coverage gate (metadata claims, not provider proof)

**2026-11-21 — experimental read-only integrity layer.** This component does not access T-Invest, a broker account, an exchange or a real order. No live trading or bot identity result is produced.

## Problem

The previous-book/public-next-trades analysis already abstains when a current trade interval extends beyond an optionally supplied exclusive completion watermark. That is necessary but insufficient for two independent streams: L2 quotes and executed prints may have **different holes, source identifiers, session boundaries and final complete-through positions**. A trade archive may be complete while the book history is silently missing, or vice versa. A single scalar supplied by the caller does not detect that difference.

The analysis also has no independently verified instrument or session identifiers in the raw ABIDES `L2Snapshots` / `PublicExecution` projection. Merely declaring matching IDs is **not source verification**.

## Added contract

`tools/public_stream_coverage.py` defines immutable `PublicStreamClaim` metadata for each of two feeds:

- `stream_kind`: `book` or `trades`
- `venue`, `instrument`, `session`, and `source`: nonempty caller-supplied identifiers
- `starts_ns` and **exclusive** `complete_through_ns` as nonnegative integer timestamps
- `gaps`: ordered disjoint half-open intervals `(start_ns,end_ns)`

`DualPublicStreamClaim(book, trades)` rejects missing/wrong stream kinds and discrepancies in the *declared* venue, instrument and session. This is an input-consistency check, **not** a cryptographic attestation against the raw tape.

The optional `source_coverage=` parameter to `summarize_lagged_book(...)` then independently checks the **entire previous book clock bin** and the **entire next observed trade clock bin**. A trade bin is eligible only if all conditions hold: preceding book coverage is claimed, current trade coverage is claimed, the book has a valid recent two-sided best bid/ask, and any existing optional explicit completion watermark allows it.

Abstention reasons are mutually exclusive and include `declared_previous_book_stream_uncovered` and `declared_current_trade_stream_uncovered` alongside existing missing, stale, crossed, incomplete-bin and one-sided book categories. One missing stream is **never** filled by the other's timestamp or last observed message. Half-open gap boundaries do not accidentally swallow neighboring fully covered bins. No interpolation of book states or unknown trades occurs.

With no dual claim the old descriptive behavior remains available for backwards compatibility. In all cases output states:

- `stream_coverage_independently_verified=false`
- `raw_stream_source_identity_verified=false`
- `real_l2_feed_coverage_proven=false`

Even when a caller supplies complete-through positions, the tool **cannot independently prove upstream message continuity**, exchange timestamp correctness or raw record provenance. The audit report includes separate declared source IDs and gap counts rather than raw book/trade values. Integrators must never convert these declarations into claims of real source completeness.

## Executed tests

`tests_l2/test_public_stream_coverage.py` covers separate book and trades gaps, boundary-aligned complete-through positions, interaction with the prior completion watermark, sorted nonoverlapping gap validation, instrument/session mismatch rejection, absence of metadata, refusal of arbitrary dictionary "proof", and explicit non-verification flags.

The cheap Python-only [dual-stream workflow](../../.github/workflows/robot-detector-dual-feed-coverage.yml) also runs the previous six archive-watermark tests; the expensive genuine ABIDES simulator does not need to be invoked to establish these deterministic data-contract invariants.

## Limits and next integration gate

A *real* dual-feed collector would need a provider-verified raw event sequence, authenticated source identity, continuity checks after reconnection, independent book/trade delivery progress, clock drift monitoring and a source-specific trusted completeness policy. The present immutable `PublicStreamClaim` objects are **untrusted declarations** and cannot replace these requirements.

No physical parent-order, single robot, real market false-discovery rate, p-value or price prediction can be obtained from this gate. The scientific release gate remains CLOSED.
