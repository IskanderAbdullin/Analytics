# Public L2 and executed-print temporal context (development-only)

**Goal:** Determine what can be established from an anonymous order-book snapshot stream and an anonymous exchange execution stream **without** leaking maker/taker identity. This is a reproducible market-microstructure *data quality and descriptive compatibility* experiment, not a VWAP/POV parent order or physical-bot detector.

## Why this stage exists

Prior [ABIDES execution-level baseline](ABIDES_GENUINE_REPLAY.md) showed fixed-q synthetic controlled-print recall: TWAP 98/183, VWAP 6/191 and POV 0/66. The variable-size periodic screen recovered none. A public directional regime-shift detector's initial result **failed** independent pre-registered replication against an agent-free null. This motivates checking **additional public observables** rather than claiming that correlation or public change windows identify agents.

## Strictly prior as-of join — with abstention

`tools/l2_trade_context.py` uses actual ABIDES `ResultProfile.L2_SERIES | ResultProfile.TRADE_ATTRIBUTION | ResultProfile.SUMMARY` with `ExchangeConfig(book_capture='l2',book_log_depth=5)`. The simulator's attribution class holds agent IDs; `public_projection()` copies only timestamp, executed price, quantity and the public aggressive side (the inverse of ABIDES' passive-side `side`). **No owner ID is ever read by the join, stored in results or used as a feature.** T-Invest real-world direction conventions may differ.

For a trade at time `t`, only a quote snapshot at time `s < t` can be used, never a snapshot at `s >= t`. All original L2 updates remain in source order. The latest *strictly* previous quote is found with binary search over monotonically ordered L2 timestamps. A fill with any L2 mutation at **exactly** the same timestamp is deliberately marked `same_timestamp_ambiguous`, not joined by arbitrary CSV row order: 434 additional L2 events shared timestamps in the first ABIDES feasibility run, so true ordering cannot be established by time alone.

Default maximum quote age is **2 seconds**. On each anonymous trade, exactly one mutually exclusive category is recorded:

- `same_timestamp_ambiguous`: book and trade timestamp equal; within-time causal order unknown
- `no_prior_quote`: no strictly older snapshot
- `stale_quote`: previous snapshot older than the configured age limit
- `one_sided_or_empty_quote`: at least one side absent in the prior book
- `crossed_or_locked_quote`: previous best bid at or beyond ask
- `at_or_through_prior_opposite_best`: SELL price at/below previous best bid, or BUY price at/above previous best ask
- `not_at_prior_opposite_best`: eligible two-sided fresh prior book, execution price not aligned with the relevant previous best

Event counts and lots are conserved exactly. `descriptive_prior_quote_alignment_fraction` is **only** the last two categories' eligible denominator. It is **not** a real execution-side correctness score, order-queue position, trading edge, conditional probability of a robot, or any statistical market FDR.

Even the prior quote could be stale because of ingestion differences, exchange snapshot sampling, hidden liquidity and asynchronous market events. Real broker quote/event feed coverage is **not verified** by this synthetic demonstration.

## Conditional negatives and controls

1. An actual **agent-free ABIDES** mode `null` is run as a market-background control. This does not mean that all other agents are non-algorithmic; it means the *named controlled execution-category* agent was absent from that simulation.
2. POV and VWAP simulations use the same documented public field projection, time join and cutoff without any agent ID.
3. A **rotated public-print bundle placebo** preserves all execution timestamps and the multiset of public (price, quantity, reported direction) bundles, while deliberately disrupting their contemporaneous alignment with the book. It is an explicit *sensitivity control*, **not** a market-preserving null: it may violate crossing-spread constraints or alter event-time association and cannot justify a p-value.
4. Six unit tests cover exact-timestamp abstention, duplicate L2 snapshot retention, no-future-leak from appended later snapshots, stale/no-prior/one-sided/crossed distinctions, public lot/marginal conservation, strict malformed-input rejection and exclusion of private maker/taker fields.

**No new live detector or user broker API was built.** The experiment uses one **development-only** seed 1501 in three ABIDES matching-engine modes; it does not access the previously evaluated seed cohorts 41–44, 61–63, 71–73, 901–904, 1101–1104, 1301–1304 and 1401. After this demonstration, seed 1501 is *spent*. No threshold can be fit using it and then claimed independently validated.

## Execute on isolated simulator runner

```bash
python -m unittest discover -s tests_l2 -p 'test_*.py' -v
python tools/l2_trade_context.py --seed 1501 \
  --output /tmp/abides-public-l2-trade-context.json
```

The separate [L2 feasibility workflow](../../.github/workflows/robot-detector-l2-feasibility.yml) installs the pinned ABIDES source, runs the actual exchange matching engine, checks count/lot conservation and public attribution isolation, and uploads a 14-day **aggregate-only** artifact. Raw L2 tapes, execution-level records and private simulator truth are intentionally never committed nor published.

## Next genuine scientific gate

Any stronger inference needs **public book and trade clocks with verified sequencing/coverage**, a model specified before evaluation and multiple source-conditional nulls preserving realistic market-book/execution constraints (market-wide shocks, timestamps, missing quotes, correlated volume, heterogeneous producers). A price/side rotation is **not** one of those strong nulls. Only after development on new seeds should a **new** seed cohort be frozen and tested blind, then independent real market sessions if obtainable.

Real historical T-Invest L2 is not established by the [historical trade/candle archive](L2_FEASIBILITY.md). No physical agent identification, market accuracy or real-world false discovery probability should be reported. Research release gate remains CLOSED; no order placement or GUI use.
