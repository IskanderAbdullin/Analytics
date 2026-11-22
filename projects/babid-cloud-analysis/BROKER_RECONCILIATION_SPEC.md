# P0: independent broker-execution reconciliation — public-source plan (2026-11-22)

**Not performed:** No broker login, tokens, live position changes or private data in public GitHub. This is a public-source procedure, not an independently reconciled result.

## Official T-Invest API time and history semantics
- `OrderTrade.date_time` represents UTC trade execution time; `OrderStage.execution_time` likewise represents a trade execution. `OrderTrades.created_at` is creation time of a broker message, which is distinct from execution and local log processing time.
- `GetOrderState` is not deep historical storage and may not return orders older than one day. `GetOrders` defaults to live orders and historical finished/cancelled filters are current-day only with up to 1-hour windows.
- `GetOperationsByCursor` provides paged history, but operations may appear after execution. Operation IDs can change and trade IDs may be different from the order-service namespace. Do not assume the same ID is available in both services.
- The broker's own report is a preferred historical source when mutable API/ID history cannot be reconciled.
- Sources: https://developer.tbank.ru/invest/services/orders/methods ; https://developer.tbank.ru/invest/services/orders/head-orders ; https://developer.tbank.ru/invest/services/operations/head-operations ; https://developer.tbank.ru/invest/services/operations/operations_problems

## Minimal PRIVATE local data contract (separately authorized only)
- Source name (broker report / operations cursor / order state / local ledger), account/instrument identity, order and trade IDs; these identifiers **never enter public GitHub**.
- Execution timestamp UTC, broker message creation timestamp if supplied, observed receipt/processing timestamp if measured, side, size with explicit units vs lots, and fees.
- Snapshot as-of timestamp, request-response timestamps, pagination cursor/provenance, source SHA-256 and completeness/gaps.

## Conservative reconciliation procedure
1. First freeze local source data, verify per-file SHA-256; do not imply atomic cross-file snapshot.
2. Acquire an independent authorized broker export or paginated operations from/to interval to exhaustion, documenting missing pages and delays.
3. Match within same account+instrument+order namespace. If trade IDs differ across API namespaces, use bounded candidates and mark ambiguity; never silently infer a unique match from one field.
4. Reconcile signed lots per source and per time domain; do not sort execution timestamps and local observation timestamps into a single causal clock.
5. Any unresolved two-lot residual must remain `unresolved`; do not claim it is an external trade, Prune or silent status credit without matching broker evidence.
6. A historic `GetOrderState` not found is not evidence of no trade: it may be beyond API retention.

## Future synthetic acceptance T24
A historical order query returns no data; an operations event appears late and carries a different trade ID namespace. The matcher must abstain from a unique link without stronger order/instrument/time/quantity evidence. No actual broker calls or live trading.
