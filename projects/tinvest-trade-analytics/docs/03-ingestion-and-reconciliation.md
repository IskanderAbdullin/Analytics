# 03. Источники, импорт, идентификация, покрытие и сверка

**Приоритет:** M0–M4, P0. Этот документ определяет, откуда берутся факты и когда мы имеем право назвать их подтверждёнными.

## 1. Матрица источников (первый провайдер T-Invest)

| Источник | Основной метод/канал | Данные | Сильная сторона | Ограничение / стратегия |
|---|---|---|---|---|
| Accounts | `GetAccounts` | брокерские счета | Discovery | хранить тип/статус и историю изменений |
| История операций | `GetOperationsByCursor` | торговые и неторговые операции | core для денежных движений | меняющиеся IDs, возможные задержки |
| Портфель | `GetPortfolio` | текущая стоимость и P&L broker-side | контроль состояния | не источник полной исторической детализации |
| Остатки | `GetPositions` | текущие деньги / бумаги / фьючерсы и т.д. | контроль количества и денежных сумм | settlement timing / ограничения |
| Брокерский отчёт | `GetBrokerReport` | отчётные записи | независимая сверка | асинхронный task_id, пагинация и ограничения |
| Стрим позиций | `PortfolioStream`, `PositionsStream` | near-live snapshot | live view | snapshot stream, не гарантированная история |
| Стрим операций | `OperationsStream` | уведомления о части неторговых событий | триггер повторного sync | НЕ основа полного торгового ledger; возможны дубликаты комиссий и агрегаты VM |
| Orders | `GetOrders`, `GetOrderState`, `OrdersStream` / состояния заявок (по доступности) | состояние заявок / fills / execution attribution | связывание с решениями робота | разные идентификаторы, неполная историчность, задержки |
| Instruments | `GetInstrumentBy`, `GetFutureBy`, справочники | contract size, min increment, venue | оценка деривативов и символы | исторические изменения спецификаций |
| Market data | `GetCandles`, `GetLastPrices`, streams / исторические файлы | цены, best bid/ask, свечи/стакан | оценка и TCA | глубина/ретенция/лицензия, нет гарантии полного replay |
| OsEngine и собственные боты | локальный structured event log | decision/order/fill/cancel/reject + version | точное отнесение к боту | нет данных задним числом, если лог не вёлся |
| Ручные документы | брокерские XLSX/PDF/CSV | backfill и спорные случаи | контроль | парсинг может быть неполным, всё только с audit |

**Важно:** `GetOperations` старой версии возвращает только последние 1000 операций и не должен использоваться для полного бэкфилла. В `GetOperationsByCursor` `quantity` — единицы инструмента, не торговые лоты. Методы API надо сверять с текущим protobuf и тестировать ответы в реальном read-only контуре.

## 2. Начальная инвентаризация / preflight

1. Проверка конфигурации, мест хранения секретов, free space, времени ПК/UTC, прав DB.
2. С токеном read-only вызов `GetAccounts` и `GetUserTariff`; определить собственника квоты и типы счетов.
3. Включить только нужные источники, тестовый пробный период 1–3 дня; проверить количество операций, семантику денежных знаков, валюты, комиссии, поля trade[] и инструменты.
4. Зафиксировать `provider_contract_version`, перечень известных `OperationType`, поддерживаемые account/instrument types, nullability каждого поля.
5. Для каждого счёта получить текущие `GetPortfolio` и `GetPositions`, сохранить timestamp и единицы измерения; проверить, нет ли недоступных классов счетов.
6. Без хранения полного токена вывести таблицу capabilities, покрытие истории, квоты, открытые вопросы, блокирующие P0.

## 3. Historical backfill: надёжный алгоритм

Рекомендуемый пошаговый pipeline:

1. Для каждого счёта разделить всю историю на временные окна (например, месяц; адаптивно сокращать до недели/дня при большой активности). Все даты в запросах UTC.
2. `GetOperationsByCursor` запрашивать с `limit` > 2 (практически 100–1000, с backoff и контролем размера), `withoutCommissions=false`, `withoutTrades=false`. Остальные флаги — осознанно с сохранением query manifest.
3. Записывать каждый полученный page в immutable raw store **до** изменения checkpoint. Создать page hash, `cursor_in`, `cursor_out`, `window_id`, `captured_at`, `operation_count`.
4. По каждому raw page в транзакции извлекать source records; сохранять original external ID, raw order/trade fields, status, money, time, origin.
5. Продолжать по `cursor`, пока больше нет элементов/следующей страницы по контракту. Не считать два одинаковых курса выдачи доказательством конца, а детектировать цикл cursor как ошибку.
6. Если data window изменён или повторная загрузка нашла отличия — новый snapshot/revision, diff старого и нового, пересборка только затронутых partition.
7. По завершении окна: `sync_window_complete` и coverage assessment; при потере связи / 429 / 5xx продолжить позже с последней подтверждённой страницы.
8. Rolling recrawl: часто повторять последние 2–7 дней; раз в неделю — более глубокую проверку 30–90 дней; отдельно сканировать исторические периоды при обнаружении drift; параметры настраиваемые, без лишней нагрузки.
9. Периодический import брокерского отчёта после задержки расчётов, compare settled events vs provisional.
10. Создать отчёт `ingest_manifest`: какие счета, окна, страницы, source versions, coverage gaps, errors, budget used.

**Ключевой запрет:** использовать broker `operation.id` как единственный долговременный бизнес-ключ. Официальная документация предупреждает, что IDs могут изменяться. Сохранять версии и match-confidence.

## 4. Идентичность операций и устранение дубликатов

Классы сущностей: `source_record` (первичный сырой), `semantic_event` (экономический факт), `ledger_posting` (бухгалтерское движение), `broker_report_row` (отчётная запись). Один факт может иметь несколько сырьевых представлений.

**Правило дедупликации:**
- A) Полный совпадающий payload hash в том же source/window = одна наблюдаемая версия.
- B) Совпавшие IDs + side + instrument + time + amount + money currency позволяют связать, но при коллизии событие переходит в `needs_review`.
- C) Изменившийся external operation.id при тех же существенных полях — probable rename, только через confirmed alias relation.
- D) Различающиеся значения — либо revision, либо новое экономическое событие, решение на основании sequence/context/broker report.
- E) Два частичных исполнения одной заявки не должны превращаться в один fill.
- F) Дубликаты комиссии между `OperationsStream` и `GetOperationsByCursor` — один экономический факт; aggregate VM не прибавлять к уже распределённой по инструментам VM.
- G) Операции отменённые или в статусе in-progress сохранять, но исключать из settled cash/P&L до подтверждения по статусу.

**Correlating orders:** официальный источник предупреждает, что trade_id операций может отличаться от trade_id сервиса заявок. Возможна дополнительная корреляция через `GetOrderState` по доступному `order_id` и information from operation, но обязательно верифицировать на реальном наборе, сохранять `confidence`, и не объявлять всё 100% exact.

### Conflict-resolution UI

Экран «неопознанные события»: сырьё, кандидаты, времена, количество, цена, суммы, diff; действия classify/link/unlink/split/mark exception; каждое исправление с audit trail + запрет стирания входных данных.

## 5. Инкрементальное live обновление

- Event sources (stream) лишь создают сигнал пересинхронизировать affected account/window; нельзя рассчитывать окончательный P&L непосредственно из недоставленных/неполных stream updates.
- 1–3 configurable tiers: (i) near-live positions (ii) latest operations (iii) settled/backfilled.
- Debounce, backpressure, limits; reconnect exponential backoff + resubscription, gap detection and backfill.
- UI показывает `live_estimate` отдельно от `reconciled_settled`; при потере связи состояние `stale_since`.
- Логи робота фиксируются источником времени (UTC системное, monotonic clock, broker event time), offset и latency correction. Нельзя вычислять микросекунды из несинхронизированных часов.

## 6. Rate limiting и совместимость с роботом

Официальные лимиты динамические. На дату проектирования документация указывает сервис операций 200 unary/min, котировок 600/min, отчёты 5/min, а суммарный рекомендуемый трафик с одного IP до 50 req/sec; лимитная политика распространяется на все счета пользователя. Цифры **не hardcode**, считывать `GetUserTariff` и динамические ограничения при ответах, учитывать резерв под live robots.

- Client-side token bucket отдельно на сервисы + global budget + reserved capacity под работу торговых систем.
- Backfill имеет самый низкий приоритет и прекращается при повышении 429 / обнаружении торговой нагрузки.
- Не использовать агрессивное дублирование запросов и квази-параллельный backfill нескольких счетов.
- Записывать `rate_limit_source`, `budget_snapshot`, метрики 429 и p95 latency.
- Квота в приложении для read-only sync отделена от максимально допустимой — безопасный запас.

## 7. Data quality / coverage

Выполнять контроль:
- `freshness`: lag API-source-to-ingest, as-of snapshots.
- `completeness`: закрыты ли окна и все страницы; посчитаны ли cash statements, market price and fee records.
- `consistency`: количество позиций, баланс cash, суммы settled VM, знак операции, единицы.
- `uniqueness`: collision / duplication / renumbering.
- `timeliness`: comparison event vs observed vs available time.
- `provenance`: payload hash / source / revision / current contract.
- `outliers`: необычные комиссии, отрицательные количества, валютные несостыковки.
- `attribution`: доля исполнения с надёжно привязанной стратегией.
- `market data depth`: секунды пропущенного orderbook/event gaps, как доля времени торговли.

Статусы: `verified` (сошёлся отчёт/остаток в пределах известного tolerance), `reconciled` (сверен по допустимому набору), `provisional` (задержка внешних данных), `partial` (дыры), `unreconciled` (расхождение), `unsupported` (методология не реализована). Все отчёты несут статус по своим компонентам, не общий «зелёный» при критичной дыре.

## 8. Broker report: независимый контроль

Асинхронный `GetBrokerReport`: generate -> task ID -> poll с backoff -> список страниц -> immutable store -> mapping. Проверить лимиты периода, страниц и состав полей. Независимый reconciliation:
1. Cash balance по каждой валюте на T0/T1 и cumulative movement.
2. Quantity по каждому UID и account.
3. Trades: side/qty/price/gross consideration/fees/settlement.
4. Accrued/paid variation margin и funding без агрегатного дубля.
5. Поступления/списания, margin charges, taxes и corporate actions.
6. Стоимость портфеля по выбранному price timestamp, валюте и rounding policy.
7. Gap report: `source_missing`, `order_without_execution`, `fee_unmatched`, `unknown_asset`, `fx_unknown`, `settlement_timing`, `source_revision`, `potential_double_count`.

Нормативный критерий: денежные settled итоги по валюте совпадают с брокерским документом до погрешности, определённой форматом/округлением документа; при несходимости релиз P&L помечается fail/provisional. `GetPortfolio` с floating-price valuation может отличаться от EOD по времени — не сравнивать несоответствующие as-of как ошибку.

## 9. Реконструкция истории и audit trails

Команды:
```text
tia doctor --account ...
tia sync --account ... --from ... --to ... --mode full|incremental|verify
tia list-gaps --account ... --period ...
tia report-fetch --account ... --from ... --to ...
tia reconcile --account ... --as-of ... --policy default
tia explain --run-id ... --scope ... --component ...
tia rebuild --from-raw --snapshot-id ... --policy ...
```

`rebuild` не обращается к брокеру и даёт побитово эквивалентные JSON facts для той же версии алгоритма и данных (порядок сортировки определён). Проверить crash посреди page, повторный импорт, изменённый ID, разные timestamps, отсутствие instrument UID, remote timeout, 429.

## 10. Конкретные источники

- [T-Invest Operations methods](https://developer.tbank.ru/invest/services/operations/methods)
- [GetOperationsByCursor](https://developer.tbank.ru/invest/api/operations-service-get-operations-by-cursor)
- [Особенности методов операций: меняющиеся ID, trade_id, cursor](https://developer.tbank.ru/invest/services/operations/operations_problems)
- [OperationsStream: только неторговые события, дубликаты комиссий и variation margin](https://developer.tbank.ru/invest/services/operations/operations_stream)
- [FAQ операций и отчёты](https://developer.tbank.ru/invest/services/operations/faq_operations)
- [Официальные лимиты](https://developer.tbank.ru/invest/intro/intro/limits)
- [Сервис операций](https://developer.tbank.ru/invest/services/operations/head-operations)
