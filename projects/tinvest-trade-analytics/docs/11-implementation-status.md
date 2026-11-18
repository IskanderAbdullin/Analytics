# 11. Реализация и журнал проверки — v0.5

Дата начала: 18.11.2026. Цель документа — отделить **реализовано**, **протестировано** и **планируется**. Здесь нет утверждений, что real T-Invest live sync прошёл.

## Что реализовано (M0 и часть M1/M2/M4)

- `src/TInvestAnalytics.Cli/`: .NET 10 CLI, официальный T-Invest REST POST read-only allowlist. Токен только из env `TINVEST_TOKEN`, не сохраняется в Git или SQLite.
- `doctor`, `accounts`, `sync` по выбранному счёту и диапазону, `sync --refresh` для повторного сканирования и ревизий, `import-json` для офлайн page, `report` и `daily-report` с необязательным `--asset-map`, `stats`.
- HTTP bounded retries for 429/408/502/503/504, conservative per-process pacing. Внешняя/межпроцессная координация квот ещё не реализована.
- Immutable `raw_pages`, `operation_revisions`, latest `current_operations`, local `sync_windows` cursors/checkpoint, SQLite WAL; transactionally commit page+checkpoint. Semantically identical multiple ID records flagged but **not silently de-duplicated**.
- `import-bot --file *.jsonl` принимает проверенные события `bot-event/v1`, сохраняет в SQLite атомарно и не перезаписывает конфликтующий `event_id`; `bot-stats --bot ... --from ... --to ...` считает диагностические события/переустановки/объёмы. Связь с брокерскими trades пока отсутствует и статистика помечается `unreconciled`.
- `daily-report` сохраняет исторические FIFO lots до начала выбранного периода и позволяет `--exclude-days YYYY-MM-DD` (непрерывная доходность портфеля при исключении дней не подменяется суммой дневных прибылей).
- Money precision via decimal (T-Invest units + nano), operation parser with optional fills, FIFO for explicitly classified stock/fund/currency; long/short/partial closure and reversal.
- Cash classification for settled VM, fees, borrow/overnight, distributions, taxes, deposits, separate funding status. Market-to-market, futures tick value/clearing reconstruction, broker verification **NOT** implemented; reported subtotal isn't total equity performance.
- Read-only broker report workflow `broker-report-request` (асинхронная задача, период до 31 дня), `broker-report-fetch` (страницы с независимым raw evidence), `broker-report-summary` (broker/exchange/clearing комиссии по валютам). Получение суммы брокерских комиссий **не означает** полного reconciliation с операциями.
- Локальные исторические снимки `GetPortfolio` + `GetPositions` с полной сохранённой исходной парой ответов. Команды `snapshot`, `snapshots`, `equity-pnl`; изменение общей стоимости счёта между двумя сохранёнными оценками с учётом пополнений/выводов.
- `equity-pnl` требует интервала полноты операций; если его нет, результат `partial`. При наличии — всё равно `provisional`: разные as-of брокерских котировок и несверенные документы.
- Offline synthetic smoke tests for FIFO, flips, VM/funding exclusion, deposit vs P&L, stale IDs, SQLite idempotency, read-only fake HTTP adapter.
- Dedicated GitHub Actions `tinvest-analytics-ci.yml` (build and deterministic tests).
- The domain model, CLI + SQLite are provisional architecture, not final validated securities/tax accounting.

## Остановленные / невалидные кейсы

- Unknown instrument type: exclude security P&L rather than applying share formula to futures.
- Bond trading: quotation percent of nominal / accrued interest not yet handled, therefore excluded from FIFO.
- Funding: deliberately excluded from net subtotal if potential double count with VM is unverified.
- Multiple accounts/instrument metadata and contract valuation: only one account per report and manual asset classes.
- Broker reports, historical marks, FX conversion, reconciliation, robust near-live and bot attribution not implemented.
- Operation types with unknown enum and unresolved fee relationships remain `partial`; don't mark `verified`.
- When operation IDs change, current view may temporarily contain multiple semantic records and report flags duplicate. Proper manual alias reconciliation remains an M1/M4 task.

## Как запустить (на компьютере с .NET 10 SDK)

```powershell
cd projects/tinvest-trade-analytics
dotnet run --project src/TInvestAnalytics.Cli -- doctor
dotnet run --project tests/TInvestAnalytics.SmokeTests
$env:TINVEST_TOKEN = "your-read-only-token"
dotnet run --project src/TInvestAnalytics.Cli -- accounts
dotnet run --project src/TInvestAnalytics.Cli -- sync --account-index 0 --from 2026-11-01 --to 2026-11-18
dotnet run --project src/TInvestAnalytics.Cli -- report --account YOUR_ACCOUNT_ID --from 2026-11-01 --to 2026-11-18
dotnet run --project src/TInvestAnalytics.Cli -- snapshot --account-index 0
dotnet run --project src/TInvestAnalytics.Cli -- snapshots --account YOUR_ACCOUNT_ID
dotnet run --project src/TInvestAnalytics.Cli -- equity-pnl --account YOUR_ACCOUNT_ID --start-id 1 --end-id 2
dotnet run --project src/TInvestAnalytics.Cli -- daily-report --account YOUR_ACCOUNT_ID --from 2026-11-09 --to 2026-11-16 --exclude-days 2026-11-14
dotnet run --project src/TInvestAnalytics.Cli -- import-bot --file bot-events.jsonl
dotnet run --project src/TInvestAnalytics.Cli -- bot-stats --bot BabidDemo --from 2026-11-09 --to 2026-11-16
dotnet run --project src/TInvestAnalytics.Cli -- broker-report-request --account-index 0 --from 2026-11-01 --to 2026-11-18
dotnet run --project src/TInvestAnalytics.Cli -- broker-report-fetch --task YOUR_TASK_ID
```

**Защита:** не коммитить токен или реальные raw operations. БД по умолчанию в `%LOCALAPPDATA%/TInvestAnalytics/analytics.db`. Не передавать брокерские данные в CI. Команда sync не должна использоваться на живом аккаунте до ручного проверки прав токена/лимитов; роботы и API могут делить квоты.

### Локальное сопоставление instrument type

Создать локальный файл (не коммитить с приватными UID при нежелании):
```json
{"UID_OF_STOCK":"stock","UID_OF_FUND":"fund","UID_OF_CURRENCY":"currency"}
```
Передать `--asset-map path/to/map.json` в `report`. **Это временная мера**: ID инструмента и свойства должны в дальнейшем подтягиваться через InstrumentsService, а ручная классификация не делает историческую торговую сумму достоверной.

## Ближайший следующий этап (M1/M2/M4)

1. Ввести synchronizer rolling rescan / refresh window и semantic identity aliases без ложной дедупликации.
2. Загружать broker report и независимые snapshots portfolio/positions; сопоставлять по UTC и settlement day.
3. Добавить instrument metadata registry с историческими спецификациями и quote conversions.
4. Отдельно проверить операции по реальным фьючерсам/VM/funding через mock+masked read-only sample, не включать futures в share FIFO.
5. Перенести core в библиотеки `Domain`, `Application`, `Ingest`, `Accounting` после первой сборки и tests; CLI thin.
6. Ускорить SQLite reports через канонические индексированные таблицы вместо parsing full `current_operations`; добавить приватное snapshot backup/restore.
7. Поддержать portfolio snapshots/equity change, fee dedupe and FX with independent broker reconciliation.
8. При появлении данных роботов — precise event telemetry, attribution, orderbook and ML features по основному ТЗ.

## Уровни подтверждения

- **DESIGNED:** ТЗ/архитектура, нет кода.
- **CODED:** исходники и synthetic test harness созданы.
- **CI_PASS:** GitHub Actions выполнил сборку и тесты на чистом runner.
- **BROKER_VALIDATED:** воспроизведены реальные операции на read-only аккаунте, сверено с брокерским отчётом.
- **PRODUCTION_READY:** проверены recovery, безопасность, performance, полные специальные случаи.

Начальная версия v0.1 прошла GitHub Actions CI на коммите `cf45482fc300205fda1ef1ed37ef35d3684a6783`. Изменения v0.2 со снимками и v0.3 с дневным отчётом прошли GitHub Actions CI; модуль bot telemetry v0.4 прошёл GitHub Actions; модуль broker report v0.5 требует нового прогона. Ни `BROKER_VALIDATED`, ни `PRODUCTION_READY` не подтверждены.


### Актуальные первоисточники для отчётов

- [Официальный GetBrokerReport, async generate/fetch](https://developer.tbank.ru/invest/api/operations-service-get-broker-report)
- [Официальный подробный контракт broker report](https://developer.tbank.ru/invest/services/operations/methods)
- Документация допускает разные интерпретации нумерации страниц `page/pagesCount`; поэтому импорт не заявляет completion без сверки `itemsCount`, а реальный отчёт требует отдельного контрактного теста.
