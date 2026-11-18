# 07. Пошаговый план, backlog, тесты и приёмка

Версия 1.0. **Цель:** реализуемое ТЗ, а не расплывчатый wishlist. Все этапы допускают сдачу отдельным PR/коммитами, но не должны скрывать ошибки core P&L.

## 1. Условия старта

- Отдельная папка/solution в Analytics, не вмешиваться в `src/ipo_forecast` и `projects/robot-detector`.
- Каждый этап: `README`/ADR, explicit inputs/outputs, C# code, mock/golden tests, report on limitations, commit SHA.
- Основная ветка `main` защищена от force push; коммиты атомарные, CI; нет секретов и реальной истории счёта.
- Финансовые операции только чтение: никакого `PostOrder`, `CancelOrder`, `ReplaceOrder` или побочных операций.
- Не считать live интеграцию пройденной только по mock-тестам.
- Стандарты: UTC time, decimal money, typed quantity, source provenance, quality flags, versioned policies.

## 2. Карта зависимостей

```text
M0 Contracts/ADR
 └── M1 Source adapter + immutable storage + backfill
       ├── M2 Equity/cash accounting ── M3 Futures/VM/funding
       │                                 └── M4 Reconciliation + trust
       │                                      ├── M5 User UI and reports
       │                                      ├── M6 Bot event ingestion/attribution
       │                                      │    └── M7 Execution/book analytics
       │                                      └── M8 Risk and portfolio analytics
       └── M9 Research warehouse/point-in-time datasets
                 └── M10 Offline ML and experimentation
                         └── M11 More brokers and plug-ins
```

Некоторые задачи M6 могут начинаться параллельно с M3, но **релиз аналитики роботов** зависит от проверенного исходного ledger/attribution.

## 3. Milestone M0 — Discovery, freeze API contracts, executable skeleton [P0]

**Задачи:**
- M0.01 Зафиксировать цели/non-goals, словарь P&L и data quality.
- M0.02 Сверить актуальные T-Invest proto и SDK версии, code-generated DTO, доступность методов по типам счетов.
- M0.03 Записать ADR-001..007, выбрать UI только на M5, но core исключительно headless.
- M0.04 Создать solution, csproj с nullable, analyzers, global.json, Directory.Build.props, StyleCop/EditorConfig, xUnit project, minimal CLI.
- M0.05 Подготовить schema migrations и инструмент `doctor` без live token.
- M0.06 Threat model: токены, локальные файлы, API, экспорт и Git.
- M0.07 Добавить CI (build/test/format/static analysis/secrets scan), baseline benchmark.

**Критерии:** чистая сборка на Windows и CI; unit tests; ADR и список неизвестного; запрет trading methods на boundary; пример CLI `tia doctor`; секреты нигде не зафиксированы.

## 4. M1 — T-Invest ingestion и source-of-truth [P0]

**Задачи:**
- M1.01 Настроить read-only token in OS vault/env import, без логирования.
- M1.02 Discovery accounts + quotas/user tariff + instrument metadata.
- M1.03 Cursor-paginated backfill с `limit>2`, checkpoints и чанками дат.
- M1.04 Raw JSON/protobuf payload store с content hash, request fingerprint и source version.
- M1.05 Normalize currencies / money / quantity / time into canonical types; unknown ops -> quarantine.
- M1.06 Idempotent re-import + changed operation IDs + revisions.
- M1.07 Current GetPositions/GetPortfolio snapshots и scheduler refresh.
- M1.08 Streaming positions as low-priority enhancement; stream ops never complete trade source.
- M1.09 Исторические данные market / instrument calendar manifests (доступность/лицензия).
- M1.10 CLI: sync, status, inspect-event, export raw anonymized, retry; local source coverage report.

**Критерии:** 10k+ synthetic events across accounts, 429/timeout/resume, repeat import no duplicates, all operation enum covered or explicitly unknown, 100% raw provenance for normalized events. Live acceptance separately with read-only token and masked evidence; не запускать без согласия.

## 5. M2 — Core ledger, stocks/ETF/cash, fees/FX [P0]

**Задачи:**
- M2.01 Deterministic event ordering, decimal math & Money/Quantity types.
- M2.02 Transactional postings + opening/closing position calculations.
- M2.03 FIFO, weighted average, long/short, partial fill, flip, split and cost basis policy.
- M2.04 Separate market cash and investment cashflows, deposits/withdrawals/transfers.
- M2.05 Fee matching, embedded vs separate fee dedupe, allocation to fills or unallocated cost bucket.
- M2.06 Historical FX conversion with timestamp/source and missing-rate handling.
- M2.07 Dividend, coupon, taxes, margin financing basic classifications.
- M2.08 Absolute P&L, realized/unrealized, gross/net, cash/equity; as-of consistent.
- M2.09 Explain mode: exact source event list per component; golden numeric fixtures.

**Критерии:** G01..G06,G10..G14,G17,G20; no negative inventory except signed short, equal sum of lot matches and realized P&L, no double counted fee, transfer-neutral consolidated P&L, math independent of ingestion order except documented tie-breaker.

## 6. M3 — Futures, perpetual, clearing, options groundwork [P0]

**Задачи:**
- M3.01 Contract metadata history and money-value-of-tick, quote units vs settlement money.
- M3.02 VM postings, settlement anchor, closing/opening risk per session.
- M3.03 Funding and perpetual futures treatment (double-count guard).
- M3.04 Expiry/settlement/dealer session/time-zone semantics, contract roll link.
- M3.05 Options interface and special operation types, unsupported-case flags.
- M3.06 Broker operation ↔ VM events mapping with test corpus.
- M3.07 `NVDAperpA` fixture: daily results, last full week, exclusion of 14.11 with independent check.
- M3.08 Test changing tick value and missing settlement price/FX; open mark provisional.

**Критерии:** G07–G09, G15–G16, G18–G19; 100% VM operations classified in fixture, no double count, total cash VM matches chosen broker report up to policy tolerance; past unobservable values flagged. Нельзя считать готовым, если «формула вроде совпадает» на одной сделке.

## 7. M4 — Reconciliation: verification and trust dashboard [P0]

**Задачи:**
- M4.01 Asynchronous broker report fetching with task id, pagination, rate-limit budget.
- M4.02 Independent parsing and mapping to broker-report facts, not from same normalized calculation.
- M4.03 Checks: cash by currency, units by UID/account, fees/VM/funding, actual vs expected snapshots.
- M4.04 Breakdown reconciliation difference with explicit source links and severity.
- M4.05 UI/CLI unresolved cases and manual overrides with audit trail.
- M4.06 Historical replay from immutable payload snapshots.
- M4.07 Controlled failure injection for delayed ops, IDs changed, unknown instrument, missing quote.

**Критерии:** independent golden broker-report fixtures + masked live samples. No `verified` label when abs difference > source-specific tolerance. All discrepancy cases report which event/valuation/FX to inspect. Offline rebuild repeatability.

## 8. M5 — Desktop / headless reports [P1]

**Задачи:**
- M5.01 Select WPF vs Avalonia via ADR; desktop remains optional.
- M5.02 Dashboard with period/instrument/robot/account, currency, day basis, P&L mode.
- M5.03 Daily calendar table, equity curve, instrument and expense waterfall.
- M5.04 Drilldown from figure to raw events/lot matching/VM and confidence.
- M5.05 Sync panel progress, logs and status; separate stale/live vs settled values.
- M5.06 CSV/JSON/Parquet/XLSX export with manifest and privacy presets.
- M5.07 Local read-only HTTP API and ergonomic CLI.
- M5.08 UX tests, large-table virtualisation, keyboard filters.

**Критерии:** any user-filtered P&L can be exported + explained; no hidden source gap; query under benchmark target on 1m events; UI cannot edit ledger source directly.

## 9. M6 — OsEngine / bots attribution [P1]

**Задачи:**
- M6.01 JSON Lines event contract v1 + schema validator + forward compatible versioning.
- M6.02 Minimal bot emitter library safe for latency-sensitive trading; async bounded queue + crash durability and drop metrics.
- M6.03 OsEngine log importer (historic parsing when feasible) and new structured telemetry adapter.
- M6.04 Entity mapping: repository, bot, version SHA, config hash, instance/run, strategy, signal, target level.
- M6.05 Robust order/exec correlation (exact/inferred/manual/unknown) with partial fills and cancel race.
- M6.06 Strategy virtual inventory ledger; cross-strategy conflicts explicit, own-account reconcile.
- M6.07 Screens: bot sessions, attributed P&L, ambiguous fills, version-to-version comparison.
- M6.08 Test representative BestAskSeller, Babid/BabidDemo, MarketMakerStakan3 cases with synthetic fixtures.

**Критерии:** two bots simultaneously on same instrument never auto-attribute ambiguous fills as exact. Explicit unmatched P&L; complete run logs correlate to exact orders where reliable. No speed/latency deterioration in live robot event loop due to analytics logger.

## 10. M7 — Execution / L2 analytics and microstructure [P1]

**Задачи:**
- M7.01 timestamp sync/latency uncertainty measurement.
- M7.02 quote/last/orderbook collector with retention and gap detection + Parquet partitions.
- M7.03 TCA benchmarks arrival/mid, VWAP/TWAP, spread capture, shortfall, fee normalization.
- M7.04 Cancel/fill/requote/partial execution and quote lifetime analysis.
- M7.05 Multi-depth target level attribution (50/100), target persistence and own-quote feedback.
- M7.06 Pro-rata-aware exploratory fill opportunity model; mark assumptions/uncertainty, avoid treating L2 as full queue priority.
- M7.07 ExecutionQualityReport and incident summary.
- M7.08 Performance tests for high-frequency telemetry ingestion / data gap recovery.

**Критерии:** TCA metrics unavailable when timestamp/quote insufficient, not silently estimated; synthetic cancel-on-fill classified benign; book gaps labelled; simulation explicitly distinguish hypothetical vs observed fills.

## 11. M8 — Advanced risk/portfolio intelligence [P1]

**Задачи:**
- M8.01 TWR/XIRR/Modified Dietz with explicit accuracy levels.
- M8.02 Drawdown, return distribution, Sharpe/Sortino, risk per capital and trading time, leverage/margin usage.
- M8.03 Concentration and correlation by instruments, strategies, venue, currency, sector and time.
- M8.04 Multiple-account consolidated performance, transfer pairing, account-aware taxation.
- M8.05 Portfolio stress scenarios/alternative FX rates/fee sensitivity (advisory).
- M8.06 Strategy comparison with paired-period controls and confidence intervals.

**Критерии:** risk metric definitions + day basis + sample size; no false annualization from tiny samples; consolidated P&L invariant to internal transfers; XIRR fails informatively when unsolvable.

## 12. M9 — Research warehouse / historical PIT datasets [P2]

**Задачи:**
- M9.01 Parquet/Arrow exports + frozen dataset manifests and snapshot IDs.
- M9.02 Feature store / label store separation, `available_at` and embargo.
- M9.03 Notebook samples and Python package with no broker tokens.
- M9.04 Reproducible backtesting from immutable source snapshots, market data gap analysis.
- M9.05 Dataset validation (schema, missingness, leakage, splits).
- M9.06 Research catalog (experiments, feature definitions and metric versions).

**Критерии:** time-travel query returns only data available at cutoff; deterministic dataset checksum; no proprietary data committed.

## 13. M10 — ML experimentation [P2]

**Задачи:**
- M10.01 Baselines no ML (simple bins, rolling means, rule filters).
- M10.02 Anomaly detection for execution/funding/fees; human-inspectable source trace.
- M10.03 Execution fill probability, survival/censoring if cancel before target.
- M10.04 Adverse selection / slippage predictive model with calibrated risk and uncertainty.
- M10.05 Walk-forward / grouped split / embargo / multiple tests/CI.
- M10.06 Model registry, model card, checkpoint, drift reporting.
- M10.07 Shadow-mode evaluations and promotion workflow (no order placement).
- M10.08 Experimental comparison against trivial baselines net of realistic costs.

**Критерии:** held-out metrics, leakage checks, calibration and honest negative results. No blanket claims of improved profitability from in-sample fit.

## 14. M11 — Multi-broker/plugins/optional MCP [P2]

**Задачи:**
- M11.01 Finalize `IBrokerAdapter` for additional broker API (e.g. Alfa/Finam); each adapter declares coverage and unsupported fields.
- M11.02 Cross-broker transfer pairing and consolidated equity/FX.
- M11.03 Plugin manifest + signed version + capability restrictions.
- M11.04 Local read-only MCP that answers financial questions with calculation run ID/source trace.
- M11.05 Data export to Analytics/robot-detector as anonymized, versioned and licensed manifest.
- M11.06 Encrypted backup/restore, schema migration compatibility, long-retention policy.

**Критерии:** new broker fake adapter passes contract suite, no changes to core P&L engine; no secrets in published data; cross broker metrics contain coverage exclusions; MCP can't call any trading endpoint.

## 15. Deterministic test plan / матрица качества

### Unit / property
- fixed-point decimal, Money currency mismatch throws;
- cash ledger balanced, no negative unit mismatch;
- FIFO/AVG/short/flip conservation;
- VM settlement boundary and funding double-count prevention;
- time/calendar and half-open [from,to);
- fees allocation & tax neutral display changes;
- FX/source resolution and missingness.
**Gate:** M2/M3 100% critical accounting functions covered by golden fixtures; property tests in CI with seeds.

### Integration
- mock gRPC service: 429, 503, duplicated pages, cursor stall, empty response, unknown operation type, pagination near 1000, clock skew;
- SQLite interruption in transaction and resume; migration across versions; replay.
- report generation async task status, pages, matching with API operations.
**Gate:** consistent normalized tables after interruptions and retries.

### End-to-end
- clean install / token import / accounts / historical sync / reconcile / P&L view / export / offline rebuild;
- robot JSONL logger replay and ambiguous matching;
- import full month including corporate action and perpetual futures.
**Gate:** no silent unknown, no false verified, no unbounded memory growth.

### Performance
- generator 100k / 1m fills and 10m quote events under configurable local resources;
- p50/p95 query and sync throughput; SSD and RAM use; Parquet partition sizes;
- degrade gracefully when machine shares resources with live trading software.
**Gate:** performance budget recorded, not asserted until benchmark.

### Security
- static check: no production write trading client instantiated.
- secret scan, logs redaction, export anonymization, loopback API unauthorized cannot access.
- audit errors / inputs, 3rd-party license manifest.
**Gate:** no credentials/account PII in repo or CI artifacts.

## 16. Definition of Done (for every milestone)

- [ ] Requirements traced to code/tests, no empty placeholders presented as finished.
- [ ] Compiles; unit & integration tests pass on CI.
- [ ] Source coverage, errors, uncertainty and unsupported types reflected in outputs.
- [ ] Migration and rollback/backup instructions present.
- [ ] Commit SHA, changed files, version of API contract and regression notes reported.
- [ ] No user secrets, account IDs, private portfolio values, or proprietary data committed.
- [ ] No trading/Computer Use actions without explicit permission.
- [ ] At least one reproducible example report / fixture, with expected values.
- [ ] Next milestone prerequisites and open blockers documented.

## 17. First implementation order (smallest sensible commits)

1. `chore: create TInvestAnalytics solution, CI, threat model`.
2. `feat: add canonical Money/Quantity/Time/Event source contracts`.
3. `feat: implement T-Invest operations cursor adapter with raw capture`.
4. `test: add pagination/ID-change/retry idempotency fixtures`.
5. `feat: implement SQLite migration and event revision log`.
6. `feat: implement cash ledger and security FIFO/AVG accounting`.
7. `test: add golden P&L and cash reconciliation fixtures`.
8. `feat: implement futures VM/funding subledger`.
9. `feat: implement async broker report reconciliation`.
10. `feat: add explain/report CLI and UI thin layer`.

Each commit small enough for review. Main branch push permitted only after local tests and branch head check. No force push.

## 18. Priority by immediate practical value

**Release A / Minimum trustworthy result:** M0–M4 with CLI daily per-instrument P&L including futures and broker reconciliation. Highest priority before any ML.

**Release B / Useful personal trading product:** M5–M8, robot attribution and execution quality dashboard.

**Release C / Research laboratory:** M9–M11, PIT data, model experiments, plugins.

Первый live validation corpus должен включать 09–15 ноября 2026 по конкретному срочному инструменту с вариационной маржой и независимым расчётом по каждому дню; настоящее имя инструмента, счёт и суммы не сохраняются в GitHub.


## 19. Проверенные открытые реализации и научные эксперименты (дополнение v1.1)

Обязательные дополнительные входы при реализации:
- [Ревизия GitHub-исходников, конкретные функции, тесты, контрольные примеры](09-open-source-implementation-audit.md): `OSS-01..OSS-10`. Каждый перенос идеи требует самостоятельной unit-test реализации на C#; лицензионные ограничения соблюдаются.
- [Научные исследования, научная обоснованность, экспериментальные задачи](10-academic-research-and-experiments.md): `SCI-01..SCI-10` и `EXP-01..EXP-06`. Research only after verified ledger and point-in-time data.

### Усиленные контрольные точки:

- **M1:** сравнить resume-on-cursor из Relff и наше атомарное checkpoint; error response не допускает `complete`.
- **M2:** тесты еJournal FIFO и TTExtension average/reversal как независимые test inspirations, добавить decimal, account/UID, cash movement invariants; `BUY/SELL` не являются внешним cashflow брокерского счёта.
- **M4:** quantity reconciliation по каждому счёту, инструменту и as-of, с первоисточником и coverage.
- **M7:** implementation shortfall с явным unfilled opportunity component, cost waterfall и venue-specific `IFillModel`; SPB pro-rata не равен FIFO.
- **M8:** проверки доходности против альтернативных implementation approaches (TWR/XIRR/Modified Dietz), quality-aware valuation on cashflow dates.
- **M9/M10:** point-in-time feature availability, survival/right-censoring, purged walk-forward, DSR/PBO и непредвзятые baseline; научный источник не считается подтверждённым на MOEX/SPB без локального OOS.

**DoD:** номер GitHub commit в проекте, зафиксированные версии сторонних источников и licenses, trace code↔tests↔requirements, отдельный `not-validated` статус для непроверенных деривативов и fill models.
