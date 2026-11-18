# 02. Архитектура, контракты и модель данных

## 1. Контекст

Система **read-only**. Отдельное приложение рядом с OsEngine, независимый процесс и локальная БД. Нельзя смешивать аналитический ingestion с исполнением заявок/критическим latency path торговых роботов. В том числе при использовании одного T-Invest токена с нескольких процессов требуется общий консервативный budget квот.

```text
T-Invest APIs ──┐       ┌──────────┐
Broker reports ─┼─> [Source adapters] -> [Raw immutable ingest] -> [Canonical event log]
OsEngine logs ──┤                                              │
Market history ─┘                                             v
                                                [Identity + Mapping + Ledger]
                                                           │
                              ┌────────────────────────────┼────────────────────────────┐
                              v                            v                            v
                       [P&L engine]                 [Robot attribution]        [Data quality audit]
                              └────────────────────────────┼────────────────────────────┘
                                                           v
                                               [Analytics semantic layer]
                                                /        |         \
                                             UI/CLI   read-only API   Parquet/DuckDB -> Python ML
```

## 2. Проекты .NET solution (предлагаемые)

```text
projects/tinvest-trade-analytics/
  README.md
  docs/
  contracts/
  src/
    TInvestAnalytics.Domain/           // Money, Quantity, Portfolio, Fill, CashFlow; broker agnostic
    TInvestAnalytics.Application/      // use-cases, orchestrator, computation runs
    TInvestAnalytics.Broker.TInvest/   // API adapter, protobuf mapping, quotas
    TInvestAnalytics.Ingest/           // raw snapshots, backfill, idempotency
    TInvestAnalytics.Persistence/      // SQLite, migrations, repositories
    TInvestAnalytics.Accounting/       // security lots, futures, FX, cash, reconciliation
    TInvestAnalytics.BotTelemetry/     // OsEngine event adapter, bot attribution
    TInvestAnalytics.Analytics/        // KPI, views, query services
    TInvestAnalytics.Api/              // loopback HTTP read-only endpoints
    TInvestAnalytics.Cli/              // init/sync/reconcile/report/export
    TInvestAnalytics.Desktop/          // Avalonia/WPF, isolated from core
  tests/
    Unit/ Integration/ Contract/ Golden/ Property/ Perf/
  research/
    python/ notebooks/ model_registry/
```

На этапе M0/М1 создавать только реально необходимые проекты; дерево выше — целевая организационная схема, не требование создать пустые DLL. Module boundaries enforce через зависимости проектов.

## 3. Доменные типы

- `Money { decimal Amount, ISO4217 Currency, ValueKind, SourcePrecision }`; не складывать разные валюты без FX.
- `Quantity { decimal Units, UnitKind }`, отдельно lots vs pieces vs contracts; conversion с учётом исторического lot size.
- `InstrumentKey { Broker, Uid, ValidAt }` + aliases FIGI/ticker/class_code/ISIN; идентифицировать при изменении кода/тикера.
- `TimePoint { UtcInstant, BrokerEventTime, ExchangeTimeZone, TradeDate, SettlementDate, ObservedAt, AvailableAt }`.
- `SourceRef { provider, account_ref, endpoint, request_hash, payload_hash, captured_at, schema_version, source_revision }`.
- `AccountingPolicy { lot_method, fee_allocation, pnl_semantics, fx_source, fx_fixing_time, rounding, calendar, base_currency, tax_policy }`.
- `ComputationRun { run_id, policy_hash, git_sha, schema_version, data_cutoff, data_snapshot_id, started_at, completed_at, result_status }`.

**Точность:** сериализованный decimal как строка либо фиксированный scale, денежная арифметика decimal, функции округления документированы. Флоат допустим лишь в аналитической статистике/ML после нормализации, не в учётной книге.

## 4. Нормализованная модель (logical schema)

Минимальные обязательные поля и связи; физические имена можно уточнять только ADR.

### Реестр / provenance
- `sources(id, kind, endpoint, provider, capture_version, licence, credentials_scope)`.
- `ingest_runs(id, source_id, account_id, window_start_utc, window_end_utc, checkpoint_cursor, attempts, status, error_code, started_at, finished_at, fetched_count, schema_version)`.
- `raw_payloads(id, ingest_run_id, source_id, request_fingerprint, captured_utc, event_time_hint_utc, payload_sha256, encoding, payload_bytes_ref, api_schema_version)`. Unique source/request/sha; никогда не обновлять payload.
- `source_coverage(id, account_id, instrument_id nullable, dataset_type, start_utc, end_utc, completeness, detection_method, assessed_at, evidence)`.
- `canonical_event_revisions(event_uid, revision_no, source_payload_id, event_kind, valid_from, superseded_at, content_sha256, reconciliation_status)`.
- `event_source_links(canonical_event_uid, raw_payload_id, source_record_path, confidence, link_reason)`.

### Счета и инструменты
- `broker_accounts(account_pk, broker_code, external_account_ref_encrypted, account_type, base_currency, opened_at, closed_at, active)`.
- `instruments(instrument_pk, provider, uid, asset_class, underlying_pk, venue, tick_size, lot_size, quote_currency, settle_currency, validity)`.
- `instrument_aliases(instrument_pk, alias_type, alias_value, valid_from, valid_to, evidence)`.
- `instrument_spec_history(instrument_pk, effective_from, effective_to, min_price_increment, min_price_increment_amount, contract_multiplier, expiry, collateral_rules, funding_rules, source_ref)`.
- `exchange_calendars(calendar_id, timezone, sessions, clearing_boundaries, holidays, version)`.
- `fx_rates(base_ccy, quote_ccy, rate, rate_time_utc, observed_at, source, quality_flag)`.

### Канонические события
- `cash_events(event_uid, account_pk, event_time, posting_time, currency, amount_signed, event_type, instrument_pk nullable, order_ref nullable, fee_component, settlement_id, origin_ref)`.
- `executions(exec_uid, account_pk, instrument_pk, order_ref, broker_trade_ref nullable, fill_time_utc, side, units, price_points, price_currency, settlement_currency, value_currency, raw_total, source_confidence)`.
- `order_events(order_event_uid, account_pk, client_order_ref, broker_order_ref nullable, instrument_pk, state, requested_qty, remaining_qty, event_time, source)`.
- `corporate_actions(action_uid, instrument_pk, effective_at, type, ratio, cash_amount, evidence)`.
- `market_ticks(tick_uid, instrument_pk, event_time, observed_at, available_at, bid, ask, last, source, quality)`.
- `order_book_events(book_uid, instrument_pk, event_time, received_at, sequence_no nullable, bids_asks_ref, depth, source, gap_flag)`.

### Бухгалтерские производные
- `lots(lot_uid, account_pk, instrument_pk, strategy_id nullable, open_exec_uid, qty_initial, qty_remaining, unit_cost, policy_hash)`.
- `lot_matches(id, open_lot_uid, closing_exec_uid, closed_qty, open_value, close_value, matching_method, fx_policy, run_id)`.
- `ledger_postings(posting_uid, computation_run_id, event_uid, book, account_pk, instrument_pk nullable, currency, amount_signed, component_code, pending_status)`.
- `position_snapshots(account_pk, instrument_pk, as_of_utc, units, mark_price, market_value, cost_basis, vm_anchor, quality, source_ref)`.
- `portfolio_snapshots(account_pk, as_of_utc, cash_by_ccy, assets_by_ccy, margin_state, nav_base_ccy, source_ref)`.
- `pnl_facts(run_id, scope_type, scope_id, period_start, period_end, pnl_component, currency, amount, precision, quality)`.
- `reconciliation_checks(check_id, run_id, account_pk, as_of, check_type, expected, actual, difference, tolerance, severity, source_refs, status)`.
- `manual_overrides(id, actor, created_at, target_uid, operation, justification, evidence, supersedes_id, approved)`.

### Роботы
- `bots(bot_id, name, repository_url, strategy_family)`, `bot_versions(bot_id, version_id, git_sha, config_hash)`, `bot_runs(run_id, bot_id, version_id, account_pk, start_time, end_time, host, broker, mode)`.
- `strategy_decisions(decision_id, run_id, instrument_pk, decision_time, observed_at, signal_kind, target_level, target_qty, reason_code, order_book_ref, config_hash)`.
- `robot_order_links(order_ref, bot_run_id, decision_id nullable, attribution_method, confidence, evidence)`.
- `execution_attribution(exec_uid, strategy_id nullable, bot_run_id nullable, confidence, method, assigned_qty, approved, evidence, policy_version)`. Sum assigned_qty <= fill qty, unmatched remainder explicitly retained.
- `bot_telemetry(event_id, run_id, kind, mono_timestamp nullable, utc_timestamp, payload_ref, source_version)`.
- `experiment_runs(experiment_id, dataset_hash, strategy_version, execution_model_version, params_hash, metric_pack_version, seed, results_ref)`.
- `ml_datasets(dataset_id, raw_snapshot_ids, feature_spec_hash, label_spec_hash, cutoff_policy, split_spec, lineage_json)`, `model_runs(model_run_id, dataset_id, code_sha, params_hash, metrics, artifact_ref, created_at)`.

## 5. Инварианты БД / ограничения

1. У каждого факта расчёта есть ссылка на исходные события и calculation_run.
2. Тот же ответ API при повторной загрузке не создаёт новую экономическую операцию; меняющийся operation ID **не** равен экономическому identity.
3. Важно различать exact semantic identity, probabilistic match и no match; fingerprint не объявлять безусловно уникальным.
4. На уровне БД uniqueness для `(event_uid, revision_no)`, `(run_id, posting_uid)` и надёжных внешних ключей.
5. Нельзя переписывать raw events и historical instrument specification; новый источник -> новое revision.
6. Любое исправление manual mapping хранит actor, время, основание и исходное состояние.
7. Coverage должен вычисляться на том же временном интервале и уровне детализации, что отчёт.
8. Никаких смешанных единиц: contracts, shares, lots, quote-points, money, NAV, margin guarantee.

## 6. Алгоритмические границы

- **Adapter** изолирует sdk/protobuf и переводит raw в typed canonical data, но не решает, прибыльная ли операция.
- **Ingest** управляет транспортом, rate limit, retries, checkpoint и immutable writes.
- **Normalizer** классифицирует операции и строит event graph.
- **Accounting engine** строит snapshots + postings чистыми детерминированными функциями от данных и политики.
- **Reconciliation engine** независимо сравнивает результат с broker reports / portfolio snapshots / signed cash balances.
- **Analytics engine** использует только accepted/reconciled либо явно маркированные preliminary факты.
- **Research engine** читает frozen Parquet snapshots; не хранит ключей торговли.
- **UI** читает через query layer/API, не выполняет расчёты локально внутри view models.

## 7. Версионированные read-only API (пример будущего контракта)

```text
GET /v1/accounts
GET /v1/coverage?account=&dataset=&from=&to=
POST /v1/sync-jobs            (локально запускает импорт; только read-only broker)
GET /v1/sync-jobs/{id}
POST /v1/reconciliation-runs
GET /v1/pnl?account=&instrument=&bot_run=&from=&to=&day_basis=&currency=&policy=&as_of=
GET /v1/pnl/{calculation_run_id}/explain
GET /v1/executions?account=&instrument=&from=&to=
GET /v1/robots/{bot_id}/runs
GET /v1/reports/{id}/export?format=json|csv|parquet|xlsx
GET /v1/health
```

Каждый аналитический ответ: `value`, `currency`, `metric_definition_id`, `data_cutoff`, `quality_status`, `coverage_percent`, `calculation_run_id`, `source_refs`, `timezone`, `policy_hash`. Поддержка cursor pagination, result caps и request IDs. По умолчанию loopback-only, авторизация на локальном API при включении. PII redacted.

## 8. Технология хранения / миграция

Старт: SQLite WAL, single-writer queue, отдельные read connections, индексы `account+time`, `instrument+time`, `order_ref`, `run_id`. Долгий стакан и тики писать с chunking/compression в Parquet, а метаданные и manifests — в SQLite. Никаких неоправданных гигабайт стаканов в Git. Аналитические запросы допускают DuckDB для колоночных сканов, через отдельный query provider. Когда объёмы и конкуренция потребуют — миграция PostgreSQL со snapshot-checked ETL. Восстановление: versioned migrations + consistent backup + import replay.

## 9. Наблюдаемость и безопасность

Логи структурированные, уровни, correlation IDs; метрики длительности и полноты sync, 429, parsing errors, current backlog, unresolved ops, reconciliation deltas, latency/size of analytics query, backup age. Не логировать токены/полные номера счетов. В репозиторий попадут только обезличенные фикстуры. Никакой секрет в GitHub Actions artifact. Error handling fail-closed; неизвестный operation enum — quarantine + предупреждение, а не `0`.

## 10. ADR, которые необходимо зафиксировать до реализации

- ADR-001: `C#/.NET 10` + выбор официального SDK по актуальности, альтернатива прямым gRPC контрактам.
- ADR-002: `SQLite` как operational store, Parquet/DuckDB как аналитический слой.
- ADR-003: выбор UI (WPF vs Avalonia) по реальным требованиям Windows/cross-platform.
- ADR-004: ledger/event-sourced revisions, схема дедупликации при меняющихся ID.
- ADR-005: методология P&L и семантика вариационной маржи.
- ADR-006: single-account vs multi-account attribution, consolidated transfers.
- ADR-007: политика внешнего API и локального MCP: только read-only, redaction и approvals.
