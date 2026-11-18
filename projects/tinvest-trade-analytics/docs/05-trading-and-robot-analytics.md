# 05. Аналитика торговли, роботов, исполнения, стакана и рисков

**Приоритет:** M5–M8. Сначала достоверные операции, затем роботы/исполнение: performance не должен вычисляться по несверенным событиям без явной маркировки.

## 1. Семантический слой аналитики

Каждый отчёт содержит:
- `scope`: account / consolidated accounts / instrument / asset class / broker / bot / strategy / bot_run / decision / order / position / calendar period.
- `metric`: уникальный metric ID, версия определения, units/currency, gross/net, TWR/absolute, метод учёта, as-of, confidence.
- `filters`: direction, session, trade date, clearing date, venue, fee class, source, strategy version, signal reason, market regime.
- `coverage`: count of matched / total executions, quote coverage, bot attribution coverage, errors.
- `drilldown`: p&l component → position/lot/VM → fills → raw evidence.

Разрешены ad hoc группировки и сохранённые пресеты. Любой агрегат пересчитывается из версионированных facts, а не из округлённых UI values.

## 2. Таблицы и графики

### 2.1 Главное dashboard
Фильтры: даты (включительно в пользовательском UI, интервал [from,to) внутри), счёт, инструмент, робот, версия, метод себестоимости, currency, налоги/комиссии, выходные, торговая сессия, статус данных. KPI:
- gross/net absolute P&L, realized/unrealized/settled VM/funding, P&L equity change;
- daily P&L heatmap, cumulative equity, underwater/drawdown, percent of days positive;
- commissions, borrow fee, brokerage cost, realized slippage cost;
- turnover, traded notional, fills count, order count, average holding time;
- total return / TWR / XIRR as separate tabs;
- risk exposures (long/short per asset, currency, gross/net, margin);
- percent of trades with reliably known strategy, percent reconciled cash movements.

### 2.2 Экран «Инструмент»
Таймлайн цены, стакана (если сохранён), собственных заявок/fills/VM/funding. Таблица дат, количество контрактов/бумаг и средняя цена, реализованный/нереализованный P&L, cash charges. Показывать до/после различных методологий и сравнение с брокерскими данными. Для futures — отдельная шкала clearing sessions и settlement anchors.

### 2.3 Экран «Роботы»
Фильтры bot/repo/commit/config hash/run, сравнение версии A и B, chart equity, inventory, transitions, health, incident reports. Локальный import OsEngine + возможность standalone bot telemetry via file/pipe; не модифицировать OsEngine без необходимости.

### 2.4 Экран «Качество данных»
Coverage heatmap по датам и инструментам, график источников и lag, unresolved mapping, mismatched cash balances, последняя выгрузка брокерского отчёта, ссылка на исходные данные и объяснение каждого расхождения.

## 3. Привязка сделки к роботу: строгая модель

**Проблема:** брокер видит счёт и заявку, но не обязан знать, какой экземпляр OsEngine/стратегии сделал сделку. На одном инструменте могут торговать несколько роботов и пользователь вручную. Один тикер не является ключом attribution.

### 3.1 Контракт событий робота

Пример JSON Lines (без реальных account numbers и токенов):

```json
{"schema":"bot-event/v1","event_id":"uuid","kind":"order_submit","observed_utc":"2026-11-18T07:00:00.123Z","monotonic_ns":120034567,"bot_id":"BabidDemo","bot_version":"git:abcdef0","run_id":"uuid","strategy_id":"spread_depth_100","account_ref":"opaque","instrument_uid":"opaque","client_order_id":"uuid","broker_order_id":null,"decision_id":"uuid","side":"BUY","qty_units":"5","limit_price":"100.12","level_target":"100","mode":"paper|live"}
```

События: `run_start`, `run_stop`, `market_observation`, `strategy_decision`, `order_submit`, `order_ack`, `order_modify_requested`, `order_cancel_requested`, `order_cancel_ack`, `partial_fill`, `full_fill`, `order_reject`, `order_expired`, `position_update`, `risk_limit`, `error`, `heartbeat`. Поля `observed_utc`, `exchange_event_utc` (if available), `monotonic_timestamp`, `source_version`, `config_hash`, `strategy_id`, `run_id`. Для ставок стакана дополнительно `best_bid`, `best_ask`, `target_large_order_qty`, `depth_level`, `book_sequence`, `book_source`.

### 3.2 Matching priority

1. Exact: `client_order_id` / `broker_order_id` / execution ID связь проверена обеими сторонами.
2. Strong inferred: account + instrument UID + side + price + volume + narrow time + state transition, **только** без конкурирующих кандидатов, with confidence and evidence.
3. Weak inferred: однонаправленный match по интервалу; не использовать по умолчанию в точном отчёте.
4. Manual: пользователь подтверждает связь + сохраняет причины.
5. Unknown: остаётся неназначенным. В отчёте показывать `Unattributed` и его P&L.

Matching algorithm обязан поддерживать partial order fills, replacement (новый order ID / same logical intent), cancel races, multi-strategy overlap, broker relabeling, ambiguous same-price fills. При неоднозначности — не угадывать.

**Virtual portfolio of strategies:** стратегия имеет внутренний виртуальный cash/inventory ledger независимо от общего реального счёта. При конфликте shared inventory (один робот продаёт то, что другой купил) нужен policy explicit: fill-based attribution + account-level balancing, или capital allocation per strategy. Нельзя назначить прибыль на робота лишь по логике «последний покупал».

## 4. Метрики торговых стратегий

### 4.1 P&L и качество
- net/gross P&L; realised/unrealised; daily/weekly/monthly, per order, per decision.
- Profit factor = gross positive realized trades / abs(gross negative realized trades); undefined if no losses.
- Win rate = wins / closed round trips; с явным определением partial closes.
- Mean win / loss; payoff; expectancy (average net P&L per independent round trip); distribution and CI.
- Turnover, fees / traded notional, net profit per 1 mln turnover; spread capture / 1 mln notional.
- Profit/day, per active trading hour, per contract × day and per unit margin exposure; benchmark risks.
- Break-even fee sensitivity and breakeven adverse selection rate.
- Holding time distribution, maximum inventory/position, long/short asymmetry and overtrading.

### 4.2 Риск
- max drawdown / duration / recovery time; risk of ruin — только как модельное допущение.
- gross/net exposure and factor/currency concentration; estimated beta/correlation to benchmark.
- historical/conditional VaR or Expected Shortfall с явными параметрами и caveats на хвостах.
- rolling realized volatility, Sharpe/Sortino, Calmar — с разумным time basis, risk-free choice and confidence/observations.
- peak margin guarantee utilization, liquidation buffer (на основании фактических broker margin data), funding drag, worst single-instrument/day.
- time-in-position, exposure in illiquid auctions, overnight/weekend positions, trading halts.
- rolling regime instability and change-point alerts, but no unsolicited trading decisions.

### 4.3 Тесты статистической значимости
- Confidence intervals via block bootstrap by trading day (not IID fills when fills correlated).
- Cohort splits by instrument/day/market regime, no cherry-picking.
- Comparative analytics against equal capital/time/traded volume and out-of-sample periods.
- Multiple testing adjustment for parameter sweeps: false discoveries/Deflated Sharpe Ratio/SPA as optional research methodology, not absolute proof.

## 5. Transaction Cost Analysis (TCA)

**Required raw timestamps:** decision time, local send, gateway ack, exchange/broker execution, book observation; различать network latency и exchange latency. Метрики:
- `ArrivalPrice` = mid/quote when decision/order sent by defined benchmark, not post-fill;
- `ImplementationShortfall` = signed (execution_value − benchmark_value) + all fees, normalized by notional; side-aware;
- `SpreadPaid/Captured`: execution vs concurrent mid, per share/contract and bps, adjusted for stale-book status;
- `VWAP/TWAP`: against contemporaneous market trades within bounded interval where data available;
- `AdverseSelection`: side-adjusted future mid after 1s/5s/30s/1m/5m, multiple horizons with look-ahead **only for ex-post quality assessment**;
- `FillRatio`, `TimeToFirstFill`, `OrderLifetime`, `CancelLatency`, `CancelFailReason`, `AmendCount`, `QueueOpportunity`;
- `MarketImpactEstimate`: ex-post association, not causal impact unless design justifies it;
- fee schedule and exchange routing cost when known.

**Important:** historical candle OHLC is not an adequate substitute for event-level quote at decision time. If precision insufficient mark `approximate` and include sampling uncertainty.

## 6. Стакан, pro-rata, рыночная микроструктура

Особый акцент для роботов вроде Babid / BabidDemo / BestAskSeller / MarketMakerStakan3:

- Setup analytics: решение искать крупную «плиту», target depth 50/100, target price, own quote level, min other volume, current opposing liquidity, replenishment.
- For each decision: pre-snapshot book, chosen target, alternative quote price, actual broker ACK, movement of large order, fill/cancel, target disappearing/reappearing.
- `DecisionToAckMs`, `AckToFillMs`, `QuoteAgeMs`, `TargetPersistenceSec`, `BookGapFlag`.
- `CancelToNewOrderMs` separate from quote-change decision latency; highlight order already filled when cancel response errors.
- `QuoteThrashRate`: repetitive move/cancel near own level; `RequoteLoopCount`.
- `FilledVolumePerQuotedSec`, `SpreadCaptureAfterSelection`, inventory path; `LevelExpectedProfit` after fee.
- For pro-rata venues: show fill allocation conditional on visible quoted size/order pressure; acknowledge actual matching priority and hidden liquidity cannot be reconstructed from public L2 alone. No invented queue position.
- For simultaneous levels: attribute profit/fee/filled quantity by `strategy_order_level` (100 vs 50 vs other), instrument, session and robot configuration.
- Analyze depth event gaps, partial snapshots, L2 vs L3 limits; market data layer must preserve origin and temporal granularity.

Offline simulation of hypothetical quote levels needs a conservative fill model with explicit parameters and confidence bands. Cannot assert fills based solely on `mid touched target`. Reconstruct market trade prints and exchange matching conditions where possible, label unknown.

## 7. Position / round-trip lifecycle

A round-trip definition versioned:
- position episode opens when net position goes from zero to nonzero and ends on zero or flip; for simultaneous strategy holdings use strategy subledgers, not aggregate net account;
- partial profits allocate to episode; open and close timestamps and fee allocation defined;
- scale-in/out; reverse directly closes old then opens new; overnight and transfer breaks tracked;
- realized close trade is not the same as whole position episode profit; report both.
- unrealized open exposure present even without close, reporting only closed trade performance has survivor bias.

## 8. Аналитика ошибок роботов

- `CancelOnFilled` expected benign race vs true reject; group by connector error code and post-state.
- `UnexpectedPosition`, `StaleOrderBook`, `MissingBrokerAck`, `DuplicateSubmit`, `SelfInducedRequote`, `RiskHalt`.
- Классифицировать инцидент и связать с финансовым эффектом; сценарии, где лог Error не означает реальной потери (например, отмена уже исполненного ордера), не завышают downtime.
- Alerts strictly advisory; no unapproved changes to live robot settings.

## 9. Сравнение ботов и AB эксперименты

- Comparative cohorts matching on date/instrument/session and liquidity; normalize by exposure, turnover, quote time, not only headline ₽.
- Explicit `bot_version_git_sha`, config hash, broker, matching algorithm, latency constraints and market regime.
- Report `sample_size`, `time_at_risk`, `coverage`, confidence intervals; separate development, out-of-sample, shadow/paper/live.
- A/B strategy when shared market environment non-stationary: same-day paired evaluation with cautions about interference; no assumption of independent fills.
- Goal metrics: expected net P&L per unit risk, costs, robustness and operational incident rate, not only peak backtest P&L.

## 10. Отчёты и экспорт

Report pack:
- `DailyPnLReport`: instrument × day × bot × component, includes no-data statuses.
- `InstrumentAttributionReport`: P&L waterfall and source trace.
- `BotPerformanceReport`: versions, sessions, drawdown, fill metrics, errors, capital.
- `ExecutionQualityReport`: arrival/mid/slippage/latency and binning.
- `RiskExposureReport`: margin, concentration, worst cases.
- `DataTrustReport`: coverage, reconciliation, unresolved.
- `ComparisonReport`: A vs B, confidence, matched market conditions.
- `ResearchSnapshotManifest`: Parquet, lineage, legal/access restrictions.

## 11. Тесты и определение готовности

1. Two bots same instrument with overlapping orders -> no unverified robot claim.
2. 100/50 targeted levels -> separate per-level fills, P&L and cancellation diagnostics.
3. Cancel on already-filled returns Error -> error KPI distinguishes benign race from true reject.
4. Orderbook gaps -> spread capture confidence lowered or metric unavailable.
5. Asynchronous matching and out-of-order fill -> identical result under reordered ingestion.
6. Repeat import and reprocess -> no change in exact attribution for stable IDs.
7. Instrument ticker rename -> historical reports grouped by UID and validity.
8. Robot restarts mid-session -> run IDs unique, open inventory continuity defined.
9. Multiple users/manual trades -> uncertainty not hidden.
10. Counterfactual slippage => simulation clearly labeled hypothetical, not recorded P&L.
