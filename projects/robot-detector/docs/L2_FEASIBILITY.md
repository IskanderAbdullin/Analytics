# Feasibility: public L2 order-book data for research (not robot identification)

Date: 2026-11-21. This is a **read-only data availability/quality test**, not a new execution strategy, a validated VWAP/POV classifier or a trading signal.

## What the public provider actually documents

The official [T-Invest historical instrument archives](https://developer.tbank.ru/invest/services/history-md/head-history-md) list **anonymous executed trades** (by day and instrument) and **minute candles** (by year). They do **not document historical L2 depth snapshots as a downloadable archive in that service**. A historical trade tape and minute candles cannot reconstruct historical L2 book depth, queue membership or the identities of passive resting orders.

Separately, [GetOrderBook](https://developer.tbank.ru/invest/api/market-data-service-get-order-book) provides a **current snapshot** for an instrument and [MarketDataStream](https://developer.tbank.ru/invest/api/market-data-stream-service-market-data-stream) supports **ongoing order-book subscriptions**, including exchange/dealer book type; these are *not* evidence that complete L2 history is retrospectively retrievable. The documented quote FAQ specifies quantity values in lots and the quote service provides an exchange book timestamp. Future real-world L2 collection would need separately designed persistent feed coverage, explicit source-clock and rate-limit validation and authenticated access, **not an inferred archive**.

No T-Invest token, account, live quote subscription or trading API was used for this feasibility step.

## Simulated ABIDES-NG L2 source

The pinned [ABIDES-NG source](https://github.com/GabrieleDiCorato/abides-ng/tree/ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242) supports `ResultProfile.QUANT` (L1/L2 time series and fill attribution), while `ExchangeConfig(book_capture='l2', book_log_depth=5)` requests full depth-5 snapshots on book mutations. Its typed `MarketSummary.l2_series` uses timestamped lists of best-to-worst price/quantity levels; timestamps are in simulator nanoseconds. This is genuine simulator data, not T-Invest historical book output.

The optional `tools/l2_probe.py` runs a bounded **five-minute** simulation at seed `1401` with 40 synthetic noise agents. It audits only the public book projection, preserving multiple distinct snapshots even when their exchange timestamps coincide, and verifies:
- number of L2 update events and unique timestamps;
- each snapshot's bid/ask level counts up to depth five;
- positive prices and quantities and best-to-worst ordering on each side;
- empty and one-sided markets are represented, not silently dropped;
- no private maker/taker identifiers, broker accounts or external orders enter the output.

The artifact contains only aggregated counts, not raw book-level events, agent IDs or inferred ownership. Unit tests in `tests_l2` validate repeat-timestamp preservation, level ordering, field integrity, bounds and rejection of malformed data. The dedicated [`robot-detector-l2-feasibility.yml`](../../.github/workflows/robot-detector-l2-feasibility.yml) installs the exact upstream revision and runs the actual matching simulation, not a hand-made print generator.

### Reproduce on an isolated Python 3.12 research runner

```bash
git clone https://github.com/GabrieleDiCorato/abides-ng.git /tmp/abides-ng
git -C /tmp/abides-ng checkout --detach ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242
python -m pip install -e /tmp/abides-ng/abides-core -e /tmp/abides-ng/abides-markets
python -m unittest discover -s tests_l2 -p 'test_*.py' -v
python tools/l2_probe.py --seed 1401 --output /tmp/abides-l2-feasibility.json
```

The tool refuses to overwrite prior evidence.

## Verified simulated L2 result (2026-11-21)

The dedicated [successful pinned ABIDES L2 CI #44894589485](https://github.com/IskanderAbdullin/Analytics/actions/runs/44894589485) ran all three data-contract tests and a genuine 5-minute exchange simulation (seed 1401, 40 background noise agents, depth limit five). Results:

| Observable in ABIDES simulated L2 | Value |
|---|---:|
| Public order-book update snapshots | **1,152** |
| Unique exchange timestamps | **718** |
| Additional snapshots sharing timestamps | **434** |
| Two-sided snapshots | **661** |
| One-sided snapshots | **457** |
| Fully empty snapshots | **34** |
| Maximum captured depth on each side | **5 levels** |
| Actual simulated exchange trade prints | **709** |

All 661 two-sided snapshots had a strictly positive best-bid/best-ask spread. Input snapshot ordering was monotone, but **434 additional snapshots shared a timestamp with another book mutation**; timestamp-based deduplication would destroy exchange-state transitions and potential quote/trade causality. Quote snapshots must be preserved in simulator order (and in any real provider feed using an independently verified sequence field), not naively merged by timestamp.

This **confirms genuine ABIDES source availability and extraction feasibility**, not that T-Invest provides historical L2 files or guarantees a complete real-time L2 stream. The aggregate-only CI artifact `abides-public-l2-feasibility` expires after 14 days. No user account or actual broker market data was queried.

## Scientific interpretation

A simulated order book allows model studies of spread, imbalance, market-wide liquidity shocks and **public** quote/trade interactions, but public L2 levels still do **not** carry order owner IDs. Even a perfectly timestamped L2 tape cannot uniquely reconstruct hidden parent orders if many participants place observationally equivalent orders. A high correlation between prints and depth changes may arise from market makers and volatility; it is not proof of one robot.

The previous [frozen 16-case ABIDES execution comparison](ABIDES_GENUINE_REPLAY.md) found fixed-q TWAP synthetic recall 53.55%, VWAP 3.14%, POV 0%, with no observable detection by variable-q; the [public directional-share replication](DIRECTIONAL_REGIME_SHIFT.md) failed to discriminate controls from agent-free background. **Do not deploy a new L2-triggered bot classifier without conditional null families and independent future blind evaluation.**

The next authorized work is only a **new synthetic public-book experiment** with market-wide conditional nulls and completely fresh frozen seeds. Real L2 historical capture requires explicit separate consent/data access and a durable timestamp/coverage specification. No GUI, OsEngine runtime changes or real trading are involved. Research release gate CLOSED.

References: [T-Invest history service](https://developer.tbank.ru/invest/services/history-md/head-history-md), [GetOrderBook](https://developer.tbank.ru/invest/api/market-data-service-get-order-book), [MarketDataStream](https://developer.tbank.ru/invest/api/market-data-stream-service-market-data-stream), [pinned ABIDES-NG typed data extraction](https://github.com/GabrieleDiCorato/abides-ng/blob/ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242/docs/reference/data-extraction.md).
