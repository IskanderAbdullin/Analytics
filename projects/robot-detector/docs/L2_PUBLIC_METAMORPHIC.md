# Public-only feed metamorphic tests: past-invariant behavior under source changes

**2026-11-21 — software and data-contract stress tests, not an empirical market study.**

The source-integrity research now has three additive gates: separate caller-declared L2 and executed-trade coverage windows, strict integer-only public timestamps/prices/lots, and unique price levels in aggregated L2. Individual deterministic examples are necessary but do not alone exercise all interactions between incomplete source coverage, future append and prior-bin statistics.

## Metamorphic properties

`tools/public_feed_metamorphic.py` creates bounded generated public fixtures, using no ABIDES engine, hidden maker/taker owner IDs, real broker accounts or external market connections. Each fixture has time-ordered source L2 snapshots and separate anonymous BUY/SELL executions in later bins. These are **software fixtures**; the labels used by Python's deterministic pseudo-random generator are **not fresh scientific evaluation seeds or physical market participants**.

For each fixture the tool evaluates the same strictly previous-completed-bin algorithm under six controlled changes:

1. **Closed-prefix append invariance:** new book snapshots and executions whose timestamps are after the accepted exclusive completion watermark cannot alter any previously eligible book/flow observations or historical Spearman coefficient.
2. **Book-coverage monotonicity:** adding a documented gap to the *prior L2 stream* cannot make more trade bins eligible.
3. **Trade-coverage monotonicity:** adding a distinct gap to the *current executed-print stream* cannot make more trade bins eligible.
4. **Combined-gap monotonicity:** union of independently documented book and trade feed gaps cannot restore any excluded bin.
5. **Watermark tightening:** moving the exclusive completion watermark earlier can only remove a tail of formerly observed bins; it must not rewrite the remaining closed prefix.
6. **Conservation and disclosure:** every populated trade bin remains either eligible or accounted for by an explicit abstention; no output ever claims independent provider completeness, physical bot identity, calibrated false-discovery probability or trading ability.

Strict source integer formats and unique aggregated L2 prices are used in every generated fixture. The independent dual-stream metadata is still **caller-declared, never provider-verified**.

## Running locally or on GitHub CI

From `projects/robot-detector` with Python 3.12:

```bash
python -m unittest discover -s tests_research -p 'test_public_feed_metamorphic.py' -v
python tools/public_feed_metamorphic.py \
  --trials 64 --output /tmp/public-feed-metamorphic.json
```

The five tests verify deterministic fixture generation, 24 repeated append comparisons, gap monotonicity, source-independent and no-identification flags, and rejection of malformed/oversized trial counts. The standalone [public-feed metamorphic CI](../../.github/workflows/robot-detector-feed-metamorphic.yml) runs 64 deterministic generated fixtures at the source-controlled code version and stores only seven-day summary evidence. It does **not** launch costly ABIDES matching simulations or trade real instruments.

## Release and scientific limits

The invariants are **functional correctness properties**. Passing 64 synthetic trials cannot validate how frequently complete, gap-free, correctly timestamped public data are delivered by a live venue. It cannot estimate real-market signal accuracy, p-values, quote causality, physical parent-order identity or strategy profitability. Those require a separate independent real source provenance and scientific evaluation protocol. Scientific/trading release gate CLOSED.
