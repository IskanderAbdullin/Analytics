# Prospective paired post-event L2 → causally lagged BBO projector (2026-11-22)

**FROZEN SOURCE-FREE IMPLEMENTATION SPECIFICATION BEFORE CODE/TESTS.**
This is NOT permission to download or publish LOBSTER vendor raw files. It only defines a safe structural **synthetic fixture** adapter consistent with the *official* LOBSTER output statement that message row k changes book row k−1 into **post-event book k** (https://php.lobsterdata.com/info/DataStructure.php). No new source/seed experiments or inferred market FDR.

## Why this matters

A naive adapter feeding post-event `orderbook[i]` to the predictor of `message[i]` leaks the event's own reaction into `lambda(t_i-)`, generating a false apparently predictable pattern. The existing M1-v2 uses a fixed **1000ms lag** for BBO and requires externally asserted source continuity. This adapter must preserve that independent model rule without changing it. 

## Exact finite input and output contract

Input `paired_post_event_rows`: 1..100000 chronological *synthetic* public-only records, each **exact fields** `timestamp_ms, bid_price, ask_price, complete`; timestamp exact int in [0,2^53−1]; BBO prices finite positive int/float, bid<=ask; complete exactly Python bool. Same-time records are permitted only contiguous (timestamps nondecreasing). All rows are **POST-event** after their corresponding public message. The declared unit `source_precision_ms` must be exact int=1 and `interval_complete` exactly True (externally asserted, never proven by parser). Reject malformed, empty, unsorted, missing/extra/oracle/vendor order ID, coarse/unknown precision, incomplete or crossed book, and pathological huge numeric fields, never silently sanitize. Inputs containing private `agent_id`, `order_id`, `private_truth` or source metadata fail closed.

Group *same timestamp* POST-event rows: choose only **last post-event BBO** in that timestamp group (because it reflects all events of the grouped public millisecond); this is **not** a claim those fills have one parent/owner. Output for use as in-memory M1-v2 `snapshots`: one strictly increasing timestamp and public bid/ask/complete per grouped timestamp, no raw order references. A book effective at time t in this internal representation is **not eligible for the current event at t**: frozen M1-v2 `predict_m1_dynamic_exposure` applies raw timestamp+1000ms lag, and only after that may the last post-event state affect future public-event intensity. **Never** interpret projector output alone as a pre-event feature.

Return internal projection + separate safe aggregate `{source_rows, unique_timestamp_groups, tied_post_event_rows, source_completeness_independently_verified:false, real_market_fdr_known:false}`; printing/exporting vendor source rows, individual timestamps or identities prohibited. The projector's in-memory return may contain model input public rows, but user-facing CI prints only aggregate counts. Continuous L2/book capture is a caller assertion; cannot be inferred from row alignment or a vendor sample alone. If actual feed timestamps have finer-than-ms precision or source clock is unverified, the adapter must ABSTAIN until a separately validated normalization step.

## Prespecified test and falsification cases

1. Three exact source-free rows at (1000,2000,3000) with distinct BBOs yield 3 strictly increasing snapshots and no current-row pre-event feature.
2. Two post-event rows tied at 2000 and one at 3000 yield 2 snapshots, final tied book selected, count=one duplicate; effective-change tests demonstrate last 2000 quote can affect *only after 3000* in M1-v2 (not earlier).
3. Appending future post-event source row at 4000 must never change M1-v2 prediction for earlier [2500,3500) interval (it is not effective until 5000).
4. A duplicate same-timestamp row must not create more unique timestamp clusters or an extra independent source run; no physical owner claim.
5. Out-of-order/unbalanced/missing rows, non-bool completeness, crossed/NaN/zero/extreme BBO, coarse clock, unknown coverage, nonintegral timestamps and agent/private/order ID fields ABSTAIN.
6. No source vendor download, new ABIDES seed or market FDR; exact public Python CI required.

**NEXT_ACTION:** code an in-memory fail-closed post-event projector and source-free negative tests; then verify full published LOBSTER timing/rights before any real file-specific method run.