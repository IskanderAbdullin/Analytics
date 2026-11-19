# Stage 3 foundation — bounded event-time replay (read-only)

**Status:** implemented 2026-11-19; offline source only until genuine stream integration and coverage checks are completed.

## Goal and non-goals

`BoundedEventReplay.Analyse(TradeImportResult, ReplayAuditConfig)` provides deterministic event-time aggregation with a *bounded pending priority queue*, preserving all anonymous trade prints and observed lots even when messages arrive out of order. The module **never** claims that a print belongs to a specific account, order, parent order or robot. It cannot place trades.

It is a **replay prototype, not a T-Invest live stream connector**. The input archive is already loaded by the current CSV/GZip/ZIP importer, and the replay sorts that in-memory batch by the source's `ArrivalSequence`. The bounded-queue guarantee applies to pending event ordering only, **not** to the current CSV importer or the retained aggregate-window collection. Real-time receipts, genuine network latency, session gaps and feed completeness remain unmeasured.

## CLI

Run from `projects/robot-detector/`:

```powershell
dotnet run --project src/RobotDetector.Cli -- replay-audit `
  --input fixtures/synthetic_twap_5s.csv `
  --lateness-ms 500 --max-pending 10000 --window-minutes 5 `
  --receipt-order archive_row --output data/results/replay.json

# Сравнение с идеализированным порядком по биржевому времени (это НЕ задержка сети!)
dotnet run --project src/RobotDetector.Cli -- replay-audit `
  --input fixtures/synthetic_twap_5s.csv `
  --receipt-order exchange_time_ideal --output data/results/replay-ideal.json
```

The optional `--receipt-order archive_row|exchange_time_ideal` parameter explicitly distinguishes original archive record ordering from a sorted-by-exchange-time ideal reference. The ideal reference **must not be read as observed network latency or feed reliability**. The JSON report includes input/replayed print count, lots, out-of-order source record count, late-after-watermark count, forced early queue flushes, maximum buffered count and full per-instrument/source/mode/session/window aggregates. Default tolerance is 500 milliseconds; queue cap is 10,000 pending prints; source window width 5 minutes.

A public archive may have been pre-sorted or vendor-batched before download: `ArrivalSequence` in such a file is **not actual gRPC receive order**. Consequently, a small out-of-order count in archived data is *not evidence that the real stream has zero latency or perfect delivery*.

## Algorithm

1. Iterate original records by `ArrivalSequence`, not by exchange time. Distinguish the two in the report.
2. Track the maximum exchange timestamp received so far. Watermark = `maxSeenExchangeTime - allowedLateness`.
3. Buffer public prints in a stable event-time priority queue. Flush all prints at or before watermark into commutative aggregate windows.
4. If the queue exceeds `MaximumPendingEvents`, **force early emission of oldest event-time prints**, increment `ForcedQueueFlushCount` and emit a data-quality warning. No silent dropping; weakened order guarantee must be visible.
5. A print arriving earlier than the prior watermark increments `LateAfterWatermarkCount`. It is **still fully included** in the correct event-time aggregate window; don't report it as an absent order.
6. After the end of archive, flush all remaining records. Require exact reconciliation of original row count and lots with per-window aggregates.
7. Partition by instrument UID, `TradeSource`, `TradingMode`, `SessionId`, UTC window. Do not combine EXCHANGE/DEALER or different sessions. Preserve reported BUY, SELL and UNKNOWN volumes separately.
8. Output `AnyPrintsDropped=false`, `ActualBotCountKnown=false`, `HasActualNetworkReceiveTimestamps=false` and original `SourceCoverageVerified` flag (unverified for isolated archives).

No assumption is made about unique parent-order identity, and repeated timestamp/price records are not deduplicated.

## Tests / acceptance

- Complete synthetic fixture: 7 original prints, 640 lots, 7 replayed prints, 640 lots; no missing or double-attributed windows.
- Arrival order `0ms, 300ms, 100ms` within a 500ms allowance: one out-of-order event but no late-after-watermark flag, with exact final aggregates.
- Arrival order `0ms, 1000ms, 100ms` and 100ms allowance: one late-after-watermark flag; all volumes retained.
- Forty same-time prints, pending cap 16: 24 forced flushes, at most 16 pending, 40 original prints in final window.
- Sessions and sources isolated, empty input safe, arrival-order permutation gives identical final aggregates, invalid size/config rejected.
- GitHub Actions runs all offline regressions, replay CLI smoke and existing no-order-API sentinel. An additional read-only SBER public archive smoke verifies the new code against real data.

## Critical gaps before live T-Invest

1. **Incremental ingestion**: expose an async source interface and an incremental accumulator that does not preload an entire historical archive. This v0.1 only bounds pending ordering, not the source tape.
2. Confirm latest official [T-Invest MarketDataStream gRPC schema](https://developer.tbank.ru/invest/services/quotes/marketdata) or [JSON WebSocket streaming protocol](https://developer.tbank.ru/invest/intro/developer/protocols/ws). Do **not** confuse older `invest-openapi` WebSocket protocol with the current API. Official historic C# SDK repositories may be archived; choose a current schema and regression test serialized subscribe responses/status.
3. Token must stay in a locally configured environment variable or secret store; **never** commit or include in logs. Use only anonymous market data subscriptions, not private account/order methods.
4. Feed health: true receive timestamps, reconnect/backoff, subscription ACK state, token expiry, missing-data gaps, heartbeat and watermark-based revision tracking. A healthy TCP/WebSocket does not prove complete exchange data.
5. Incremental `window revision` if late prints arrive after a window was published; exact source ID only when the venue provides it, otherwise never claim dedup/exactly-once.
6. Read-only local API/OsEngine adapter must gate real-time alerts behind successful independent Stage-2 validation. Historical fixed-size forecasts have **not** shown an out-of-sample advantage over placebo.

The current replay stage is valuable for unit testing and architectural preparation but is **not** a completed online robot detector.
