# Prospective public execution/book projection: LOBSTER event types != trades (2026-11-22)

**SOURCE-FREE PREIMPLEMENTATION / PRETEST FREEZE.** After the real historical AMZN 2012 sample clock audit and exact nanosecond M1-v3 source-free implementation, this stage prevents a critical event-process mismatch. The original LOBSTER paired message/post-event BBO stream includes submissions, cancels, deletes and hidden executions, not only trades. Previous reported 110818 distinct timestamps lost by integer-ms flooring were over **all message types**, NOT measured on the type-4 visible trade-only sequence. The trade-only collision rate and true market actor labels remain UNKNOWN. Do not reinterpret the all-message 42.4% fraction as a trade-only fraction.

## Exact internal synthetic public fixture contract
Input is an already validated, *synthetic source-free* chronological sequence of records with EXACT public fields:
  timestamp_ns (exact integer ns since exchange-local midnight), event_type (exact integer 1..7),
  resting_side (exact integer -1 or +1), bid_price, ask_price (finite positive),
  complete (exact boolean True).
The only output eligible for research model use is an in-memory typed projection with:
- visible_type4_trade_cluster_times_ns: unique **exact source nanosecond** timestamps of event_type=4 only, collapsing same timestamp fills regardless of intervening other event types;
- post_event_bbo_snapshots: last validated POST-event top BBO at every exact original source timestamp, derived from ALL message types, for *subsequent* M1-v3 lagged usage. The snapshot of event i may influence ONLY times >=timestamp_i+1second, never event i itself;
- safe_aggregate: only event counts, exact tied group counts, visible trade execution counts, distinct type4 timestamps, type5 hidden execution count, type4 aggressor BUY/SELL counts, and explicit UNKNOWN owner/source/FDR flags. No event timestamps/quotes/orders/vendor raw rows in public aggregate.

LOBSTER event_type 4 is an execution of resting **visible limit order**. Resting side=-1 SELL means the aggressor was BUY, and resting side=+1 BUY means aggressor SELL. Hidden type5 executions are reported separately, not assigned aggressive direction without further documented source semantics. Events of types 1/2/3/6/7 do not enter visible type4 trade-intensity clusters, but their post-event BBOs may form a future lagged public quote state. Do NOT treat 269748 source message rows as 269748 executed trades.

## Strict safety/engineering/source gates
- Exact source_time_unit string = nanoseconds_since_exchange_local_midnight, source_precision_ns exact 1, interval_complete exactly True; these are EXTERNAL ASSERTIONS, not proof of licensed real source completeness. Reject malformed/unknown unit, ms integer values, missing source precision, missing source continuity.
- Bound length 1..100000 source-free message/book records (larger original 269748-row vendor source requires separate independently reviewed streaming method; **NO re-download** in this stage), exact ns within historical session, ascending/nondecreasing original message timestamps. Same-time rows may remain ordered, and only the last post-event BBO of a tied group is used for future model exposure.
- Reject private/oracle/vendor order ID/agent ID, extra keys, unaligned public message/book states, incomplete/invalid/crossed/nonfinite/10^500 price, bool/float/unsorted or out-of-session timestamps.
- If no visible type4 executions, return typed empty visible cluster tuple with zero visible count; this does NOT prove no robot, no eligible complete market trade process or actual all-execution source.
- No owner, real-market FDR, calibration, new source seeds, broker trades, or oracle joins.

## Frozen adversarial cases
1. Five-message source-free toy: type1 then two type4 at EXACT same timestamp, type5 hidden, type2 delete; only 1 distinct visible trade timestamp but 2 visible executions. Quote snapshots retained at original message times, last tied post-event BBO used, never current-time pre-event.
2. Two type4 original timestamps 1ns apart retain distinct trade clusters even though same floor-ms, unlike a split fill exactly tied. No timestamp rounding or false parent count.
3. Resting SELL(-1) is aggressive BUY, +1 is aggressive SELL; type5 hidden never added to reported type4 direction counts. Source event types 1/2/3/6/7 excluded from trade event rate.
4. Projector's public BBO can only change M1-v3 prediction after frozen 1s lag and if externally declared full source-quality passes. Future quote appended inside evaluation but not yet effective must not change earlier prediction.
5. Malformed event codes, bool direction, invalid/missing fields/private order IDs, unsorted clock, wrong/missing unit/coverage, zero/NaN/huge BBO, source rows >100000 reject. No per-source-event export.
6. All results source-free, deterministic CI, no real vendor ZIP rerun. Explicit negative report that trade-only ms collision fraction is NOT measured by prior all-message aggregate.

**NEXT_ACTION:** source-free projector and test/negative controls on exact public Python CI; audit compatibility with M1-v3 and provenance, then decide if additional legal original source observation is really needed before independent data holdout.
