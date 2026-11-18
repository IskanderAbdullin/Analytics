# 09. Ревизия открытых реализаций GitHub: конкретные файлы, подходы и точки интеграции

**Проверено:** 2026-11-18 (код и структура репозиториев прочитаны через GitHub); статус — **обзор исходников, не выполненный runtime-аудит**. Предмет: что **уже реализовано**, что именно использовать для TInvest Trade Analytics, и что копировать **нельзя**. Составлено для этапов M0–M10.

## 0. Критерий достоверности

- **[CODE]** — файл исходников реально открыт и прочитан; имя функции/свойство подтверждены кодом.
- **[TEST]** — найден файл с тестовыми сценариями; это НЕ значит, что тесты выполнялись или прошли сейчас.
- **[DOC]** — функция заявлена документацией/README, но код здесь не верифицировался.
- **[PAPER]** — метод опубликован в исследовании, не равен готовой реализации.
- **[DESIGN]** — собственный рекомендуемый контракт/псевдокод, не заимствованный из проекта.
- **[GAP]** — отсутствует подтверждение корректности на T-Invest российских инструментах и реальных клиринговых операциях.

Ни один проект не признан «готовым для нашего P&L» только по README. Все алгоритмы, особенно вариационная маржа, FX, учёт внешних потоков и опционы, требуют независимых golden tests и сравнения с брокерскими отчётами.

## 1. Наиболее полезные реализации — ранжирование по задачам

| Приоритет | Проект, ссылка на исходный файл | Реально найденный механизм | Что внедрить в наш проект | Ограничения | Этап |
|---|---|---|---|---|---|
| **A** | [Relff: `Code/history.js`](https://github.com/Relff/t-invest-portfolio-tracker/blob/main/Code/history.js) | [CODE] `fetchOperationsPage_`: `GetOperationsByCursor`, `limit:1000`, `cursor`; сохранение `accountIdx` и курсора для продолжения после ограничений Apps Script | Resumable cursor backfill, durable checkpoint, per-account pagination, tests на повторные страницы | Apps Script (Google Sheets), API через прокси; пример обрабатывает ошибки возвратом пустого page, **так в нашем core делать нельзя**: ошибка не завершает историю | M1 |
| **A** | [eJournal: `FifoMatcher.kt`](https://github.com/earlisreal/eJournal/blob/main/shared/src/commonMain/kotlin/io/earlisreal/ejournal/domain/FifoMatcher.kt) | [CODE] FIFO `ArrayDeque<Lot>`, пропорциональное распределение комиссии открытия/закрытия, шорт, частичное закрытие, scale-in/out, flip, `TradeAccumulator` | Идеи для независимого matching engine и учёта `position episode`; пример последовательности частичных сделок | Kotlin `Double` вместо `decimal`; сделки группируются по `symbol`, у нас надо `account+instrument_uid+policy`; не покрывает биржевой клиринг | M2 |
| **A** | [eJournal: `FifoMatcherTest.kt`](https://github.com/earlisreal/eJournal/blob/main/shared/src/commonTest/kotlin/io/earlisreal/ejournal/domain/FifoMatcherTest.kt) | [TEST] Кейсы: buy→sell, 2 buy→1 sell, 1 buy→несколько sell, scale-in/out, short/cover и flip | Перенести **сценарии**, независимо вычислить ожидаемые суммы и реализовать в xUnit (без заимствования тестовых данных) | Найденные тесты не запускались здесь | M2 |
| **A** | [TTExtension: `src/js/calculate.js`](https://github.com/ya-erm/TTExtension/blob/master/src/js/calculate.js) | [CODE] `processFill(accumulated, fill)`: `currentQuantity`, `averagePrice`, `averagePriceCorrected`, `fixedPnL`, комиссия, переход позиции через 0 | Сверить нашу средневзвешенную бухгалтерию и тест flip с иной реализацией; не ограничиваться FIFO | Использует JS `Number` и `lotsExecuted`, ориентируется на собственную модель платежей; не переносить знаки/единицы без теста | M2 |
| **A** | [Relff: `Code/avgprice.js`](https://github.com/Relff/t-invest-portfolio-tracker/blob/main/Code/avgprice.js) | [CODE] сравнение восстановленного FIFO количества с брокерским `position.qty`; поле `mismatch`; P/L на основе стоимости оставшихся лотов | Самостоятельный invariant `reconstructed_qty vs broker_qty` и экран расхождения | Текущая цена и операции ограниченного периода могут давать ложный mismatch, если история неполна; отделить quality | M2/M4 |
| **A** | [cs224: `portfolio_performance_metrics/metrics.py`](https://github.com/cs224/portfolio-performance-metrics/blob/main/portfolio_performance_metrics/metrics.py) | [CODE] `compute_metrics`, обработка отсутствующих valuation на датах потоков, `lenient_missing_valuations`, Modified Dietz/TWR/MWR | Разделить точную и приближённую доходность: при отсутствии оценки в день пополнения TWR не объявлять точной | GitHub API не показывает стандартную лицензию; использовать только как reference до проверки LICENSE | M8 |
| **A** | [crollila: `executionlab/metrics.py`](https://github.com/crollila/execution-microstructure-lab/blob/main/src/executionlab/metrics.py) | [CODE] `tca(...)` / `fills_frame(...)`; implementation shortfall от arrival price, в том числе `unfilled` opportunity cost и fees; benchmark/counterfactual no-trade tape | TCA model и сценарии: исполненные/неисполненные qty + shortfall sign; объединение по parent order | Синтетическая симуляция, не расчёт живого российского стакана; не переносить модель очереди на pro-rata | M7 |
| **A** | [DaniyalMlk/slippage: `shortfall.py`](https://github.com/DaniyalMlk/slippage/blob/main/src/slippage/shortfall.py) | [CODE] `ShortfallBreakdown`: commission, fees, delay, trading, opportunity; `implementation_shortfall`; внутренняя проверка суммы компонентов | Контракт cost waterfall и conservation tests для заказов с неисполненным остатком | Соглашения delay и opportunity различаются по методике; версия определения обязательна | M7 |
| **A** | [DaniyalMlk/holdout: `splits.py`](https://github.com/DaniyalMlk/holdout/blob/main/src/holdout/splits.py) | [CODE] `purged_kfold`, `walk_forward`, `combinatorial_purged_cv`, `_purge`; входы `start/end` label overlap и embargo | Взять принцип purge при пересекающихся горизонтах fill/markout; split по времени, бот-run и торговому дню | Библиотека молодая; тестировать самостоятельно, случайный split запрещён | M9/M10 |
| **A** | [hftbacktest: README](https://github.com/nkaz001/hftbacktest/blob/master/README.rst) / [queue-fill docs](https://hft.readthedocs.io/en/latest/order_fill.html) | [CODE/DOC] Replay L2/L3, feed/order latency, probabilistic queue models, альтернативы fill assumptions | Дизайн offline-simulator c sensitivity по latency, queue estimate; отдельные test fixture для event gaps | Модели Market-By-Price предполагают queue approximation; **НЕ** тождественны pro-rata СПБ; FIFO matching из других площадок не применяем без смены policy | M7/M10 |
| **A** | [QuantStats: `quantstats/stats.py`](https://github.com/ranaroussi/quantstats/blob/main/quantstats/stats.py) | [CODE] `sharpe`, `sortino`, `max_drawdown` с параметрами годовой частоты/ставки | Benchmark наших risk metrics по заранее рассчитанной income/equity time series, а не по сырым исполнениям | Требует корректной return series и данных за период; не использовать для бухгалтерского P&L | M8 |
| **B** | [Relff: `Code/xirr.js`](https://github.com/Relff/t-invest-portfolio-tracker/blob/main/Code/xirr.js) | [CODE] встраивание XIRR в Sheets, период и вспомогательный sheet | UX идеи и тесты периодов | Не источник методологии accounting; зависимость от Google Apps Script | M8 |
| **B** | [Sid-OP: `src/ledger.py`](https://github.com/Sid-OP-collab/portfolio-analytics/blob/main/src/ledger.py) | [CODE] `build_ledger`, `_consume_fifo`, ежедневный ledger | Простой прототип lot matching и daily holdings | Использует Python `float`, ориентирован на акции, не на клиринговые инструменты | M2 |
| **B** | [Sid-OP: `src/returns.py`](https://github.com/Sid-OP-collab/portfolio-analytics/blob/main/src/returns.py) | [CODE] `compute_twr`, `compute_xirr` и `compute_external_cashflows` | Полезен **как антипример** неверной модели external flows для cash+securities account | **КРИТИЧНО:** BUY/SELL объявлены cash contributions/withdrawals; для реального брокерского счёта внутренние trades НЕ внешние потоки. Не копировать | M2/M8 |
| **B** | [eddipa: `utils/match_method.py`](https://github.com/eddipa/python_portfolio_tracker/blob/main/utils/match_method.py) | [CODE] enum FIFO/LIFO; компактный CSV tracker из README | Простой демонстрационный importer/test harness | В предоставленном match_method.py только имена методов; сам по себе не готовый engine | M2 |
| **B** | [Qlib: `test_high_freq_trading.py`](https://github.com/microsoft/qlib/blob/main/tests/backtest/test_high_freq_trading.py) | [TEST/DOC] nested executors с day→30min→1min, TWAP, `collect_data` и `track_data` для решений | Event-source и исследовательский `decision → execution` trace, контроль уровня разрешения данных | Исторический backtest на 1m свечах не доказывает порядок исполнения в реальном L2 | M9 |
| **B** | [Microsoft Qlib](https://github.com/microsoft/qlib) | [DOC] загрузка данных, модели, workflow/train/eval/reporting, ML pipeline | Концепция experiment recorder, dataset snapshot, artifact registry, compare pipelines | Большая зависимость на Python; НЕ встраивать в .NET финансовое ядро | M9/M10 |
| **B** | [Beancount](https://github.com/beancount/beancount) | [DOC/CODE] Double-entry accounting, commodities, cost lots, проверки согласованности | Дизайн audit trail и проводок, проверка денежных инвариантов | GPL-2.0: использовать **как справочную реализацию**, не переносить код без лицензионной оценки | M2 |
| **B** | [ABIDES](https://github.com/abides-sim/abides) | [DOC] agent-based discrete-event рынок | Исследовательская среда для проверки эффекта собственного ордера/сигнала | Модельная биржа, а не историческое доказательство исполнения; другой matching может кардинально менять вывод | M10 |
| **B** | [bt: `bt/backtest.py`](https://github.com/pmorissette/bt/blob/master/bt/backtest.py) | [CODE/DOC] стратегии, портфели, позиции, комиссии и performance statistics | Сравнение стратегий с одинаковым benchmark и затратами; inspirational API | Не P&L для T-Invest без broker reconciliation | M8/M10 |

## 2. Подробные примеры внедрения (новые, не скопированные из исходников)

### Рецепт R1: GetOperationsByCursor / безопасное продолжение [M1]

Источник: [Relff / Code/history.js, fetchOperationsPage_](https://github.com/Relff/t-invest-portfolio-tracker/blob/main/Code/history.js#L141-L171) и официальный [GetOperationsByCursor](https://developer.tbank.ru/invest/api/operations-service-get-operations-by-cursor). В исходном проекте прогресс сохраняется как `accountIdx + cursor` из-за лимита Apps Script, а `fetchOperationsPage_` получает одну страницу. Это удачный паттерн, но его ошибка-обработчик возвращает `hasNext=false` в случае исключения — **мы обязаны отличать ошибку от конца истории**.

**Наш контракт [DESIGN]:**

```csharp
public sealed record CursorCheckpoint(
    string AccountRef, DateTimeOffset FromUtc, DateTimeOffset ToUtc,
    string? Cursor, long LastPersistedPage, string QueryHash, string SchemaVersion);

public sealed record PageIngestionOutcome(
    string RawPayloadHash, string? NextCursor, bool HasNext,
    int RawItemCount, bool PersistedAtomically);
```

Pipeline: вызов страницы → запись immutable raw + уникального hash → транзакционное подтверждение checkpoint → новая страница. Ошибка HTTP/429, parser exception, invalid cursor, `hasNext=true` + пустой/повторный next cursor должны завершаться `failed/retryable`, **не** `complete`. Подтверждённый checkpoint возобновляется после crash без пропущенных операций и без повторных экономических проводок.

**Тест:** симулировать 3 страницы, сбой после записи второй, изменение ID одной операции и повторный sync; итоговая экономическая книга имеет исходное число фактов, а raw snapshot history содержит обе ревизии.

### Рецепт R2: FIFO + шорты + переворот [M2]

Источник: [eJournal / FifoMatcher.kt](https://github.com/earlisreal/eJournal/blob/main/shared/src/commonMain/kotlin/io/earlisreal/ejournal/domain/FifoMatcher.kt#L55-L125), [готовые тесты](https://github.com/earlisreal/eJournal/blob/main/shared/src/commonTest/kotlin/io/earlisreal/ejournal/domain/FifoMatcherTest.kt). В исходном коде очереди FIFO включают долю opening fee, пропорционально matched shares; `TradeAccumulator` объединяет выходы одной позиции; при flip остаток покупки/продажи становится началом противоположной позиции.

**Наш вариант [DESIGN]:** использовать C# `decimal` для `Fill.Qty`, `Fill.Price`, `Fee.Amount`, строгую `InstrumentUid`+account, стабильный порядковый ключ исполнения. Одна операция закрытия может сформировать несколько `LotMatches`, а при flip — новую партию противоположной стороны. Комиссия разносится пропорционально, итог до округления сохраняется с высокой точностью, остаточные копейки по документированной политике распределяются на последнюю matched часть.

**Контроль на синтетике:** куплено 100×10 с комиссией 20, продано 40×13 с комиссией 8 → gross=120; opening fee allocated=8; closing fee=8; realized net=104; остаток 60 с неизрасходованной opening fee=12. Дополнительная продажа 80×12 создаёт закрытие remaining 60 и новый short 20, а не отрицательный long.

**Граница:** equity/ETF FIFO matching не является алгоритмом расчёта уже клиринговой вариационной маржи futures.

### Рецепт R3: сверка количества бумаги с брокером [M4]

Источник: [Relff / avgprice.js](https://github.com/Relff/t-invest-portfolio-tracker/blob/main/Code/avgprice.js#L30-L44). Там вычисляется `fifoQty`, сравнивается с брокерским `qty` и выводится `mismatch`.

Улучшение: `QtyRecon(account, UID, timestamp, settlementBasis)` сравнивает qty **при одинаковом as_of и convention**, выявляет missing backfill, split, transfer, unposted fill. Не делать вывод «история неверна», когда historical window не содержит открывающую покупку. Coverage может объяснять расхождение.

### Рецепт R4: классификация денежных потоков при расчёте доходности [M8]

Источник: [Sid-OP / returns.py](https://github.com/Sid-OP-collab/portfolio-analytics/blob/main/src/returns.py#L36-L75). В этой учебной модели BUY/SELL трактуются как external cashflows, что допустимо только при специфической модели `stock portfolio without cash`, но **неверно для полного брокерского счёта с cash и assets**.

**Контрпример:** на счёте 100 000 ₽ cash; купить акций на 60 000 ₽. Equity не меняется (ignoring fee), внешнего пополнения/вывода нет. При наивном BUY→deposit будет ложная доходность. Поэтому `CASH_TRANSFER_EXTERNAL` / `SECURITIES_TRANSFER_EXTERNAL` — отдельные типы операций; BUY/SELL — внутреннее перемещение cash ↔ asset. Должен быть golden test `pure trade with constant marks => P&L=0` (за вычетом платы за сделку).

Сравнить подход к valuation gaps: [cs224 metrics.py](https://github.com/cs224/portfolio-performance-metrics/blob/main/portfolio_performance_metrics/metrics.py#L105-L160). При пропуске valuation на дату cashflow отложить точный TWR или выдать явно помеченный proxy/Modified Dietz. Не делать скрытую интерполяцию без статуса.

### Рецепт R5: implementation shortfall — полная сумма и состав [M7]

Источники: [crollila / metrics.py](https://github.com/crollila/execution-microstructure-lab/blob/main/src/executionlab/metrics.py) и [DaniyalMlk / shortfall.py](https://github.com/DaniyalMlk/slippage/blob/main/src/slippage/shortfall.py).

Оригинальная математическая схема cost относительно decision/arrival benchmark (для одинаковой валюты цены):

```text
SideSign       = +1 (buy), -1 (sell)
TargetQty      = Q = ExecutedQty + UnfilledQty
PriceReference = P0 at defined decision/arrival timestamp
EndPrice       = PT
TradingCost    = SideSign * Σ(filled_i * (exec_price_i - P0))
Opportunity    = SideSign * UnfilledQty * (PT - P0)
TotalShortfall = TradingCost + Opportunity + ExplicitFees
ShortfallBps   = TotalShortfall / (Q * P0) * 10_000   (when Q*P0 > 0)
```

Вариации delay/spread/impact attribution должны сохранять тождество `total = sum(parts)`. Для контрактов, где цена в пунктах, все компоненты надо переводить в деньги по исторической стоимости шага/контрактной спецификации **до** расчёта bps. Для продажи с другой sign expected sign changes. Не использовать прибыль по стратегии как замену execution cost. При отсутствии benchmark quote помечать unavailable.

**Golden:** buy 10 @ 101, decision mid=100, end=102, executed 6, unfilled 4, fee=2. TradingCost = 6; Opportunity = 8; TotalShortfall = 16 условных единиц; 160 bps относительно `10*100` (исключительно иллюстративные данные). Реальная latency и price alignment являются отдельными требованиями.

### Рецепт R6: ML без look-ahead [M9/M10]

Источник: [DaniyalMlk/holdout / splits.py](https://github.com/DaniyalMlk/holdout/blob/main/src/holdout/splits.py#L153-L213).

Если у решения в 10:00 label `filled_within_30m` или `net_pnl_next_hour`, будущие данные до 10:30/11:00 являются **label span**; train and test нельзя разбивать так, чтобы train label пересекал test interval. Использовать chronological walk-forward / purged split и embargo. Сохранять interval `[decision_time, label_maturity_time]`, `available_at` для признаков, `train_periods` и `test_periods`.

Проверка: inject future midprice в один признак и убедиться, что PIT dataset validator и leakage audit отбрасывают строку/фейлят dataset, а не дают модели нереальную точность.

### Рецепт R7: очередь и проскальзывание при pro-rata [M7/M10]

Источник: [hftbacktest order-fill docs](https://hft.readthedocs.io/en/latest/order_fill.html) и [проект](https://github.com/nkaz001/hftbacktest).

HftBacktest учитывает Market-By-Price, очередь и latency при replay; он полезен для дизайна слоя `FillModel`, но его вероятностная FIFO queue model не описывает автоматически pro-rata исполнение конкретной площадки СПБ.

Наш интерфейс:
```text
IFillModel(venue, matching_rule_version, book_snapshot, own_order, market_events, latency_model)
    -> { simulated_fills, assumption_version, uncertainty, coverage }
```

Обязательные реализации: `ObservedOnly` (только подтверждённые исполненные сделки); `FIFOQueueApprox` (только если биржа/режим подтверждают FIFO); `ProRataApprox` (отдельный экспериментальный); `ConservativeNoFill`. В live отчёте **ObservedOnly**, симулятор лишь для offline counterfactual. Проверить размерные единицы и не заявлять, что L2 позволяет увидеть чужие индивидуальные места в очереди.

## 3. Конкретные переиспользуемые тестовые темы

| Тест | Открытый пример | Наше дополнительное требование |
|---|---|---|
| scale-in, scale-out, flat & flip | [eJournal FIFO tests](https://github.com/earlisreal/eJournal/blob/main/shared/src/commonTest/kotlin/io/earlisreal/ejournal/domain/FifoMatcherTest.kt) | decimal, UID/account, комиссия и совпадение с брокером |
| пересоздание позиции при reversal | [TTExtension processFill](https://github.com/ya-erm/TTExtension/blob/master/src/js/calculate.js#L123-L188) | deterministic tied timestamps, комиссия за закрываемую и новую часть |
| cursor resume с ограничением времени | [Relff history](https://github.com/Relff/t-invest-portfolio-tracker/blob/main/Code/history.js) | каждая страница durable, crash recovery, 429 не превращать в end-of-history |
| фактическая vs отсутствующая valuation | [cs224 metrics](https://github.com/cs224/portfolio-performance-metrics/blob/main/portfolio_performance_metrics/metrics.py) | no silent imputation; coverage on flow date |
| partial/remaining qty в TCA | [crollila metrics](https://github.com/crollila/execution-microstructure-lab/blob/main/src/executionlab/metrics.py) | ratio conservation, side sign, fx/contract multiplier |
| leakage при пересечении labels | [holdout splits](https://github.com/DaniyalMlk/holdout/blob/main/src/holdout/splits.py) | train/test grouped by day/run, strict available_at |
| HFT fill simulation / queue gaps | [hftbacktest docs](https://hft.readthedocs.io/en/latest/order_fill.html) | L2 ≠ L3, FIFO ≠ pro-rata, uncertainty |
| OHLC vs event replay | [Qlib high-frequency tests](https://github.com/microsoft/qlib/blob/main/tests/backtest/test_high_freq_trading.py) | no historical exact match from 1-min candles |
| risk Sharpe / Sortino / maxDD | [QuantStats](https://github.com/ranaroussi/quantstats/blob/main/quantstats/stats.py) | only on flow-adjusted returns, sample count and periods disclosed |

## 4. Лицензионная и технологическая оценка (snapshot 2026-11-18)

По GitHub repository metadata на указанную дату: `ya-erm/TTExtension`, `earlisreal/eJournal`, `crollila/execution-microstructure-lab`, `DaniyalMlk/slippage`, `DaniyalMlk/holdout`, `nkaz001/hftbacktest`, `microsoft/qlib` показывают **MIT**; `ranaroussi/quantstats` — **Apache-2.0**; `beancount/beancount` — **GPL-2.0**. `Relff/t-invest-portfolio-tracker` возвращает `NOASSERTION`, `Sid-OP-collab/portfolio-analytics`, `cs224/portfolio-performance-metrics`, `Invest-SDK/invest-csharp` — нет установленного стандартного SPDX ID в metadata. Это **не вывод** о реальных правах на код — перед любым переносом изучить сам LICENSE, файлы NOTICE, transitive dependencies и условия распространения.

**Приоритет:** не копировать исходные реализации в C# ledger. Создать собственный код по математическим требованиям и независимым тестовым случаям. Даже при MIT нужно соблюдать copyright/license notice, если код действительно переносится. Для GPL — не переносить без осознанной юридической оценки.

## 5. На что открытые исходники не дают готового ответа

- Ни один прочитанный здесь portfolio/trade journal не доказал корректность полного post-clearing P&L по T-Invest perpetual futures, особенно при aggregate VM + funding.
- Получить `strategy_id` исторических сделок только из брокерских операций нельзя гарантированно: нужна телеметрия OsEngine / correlation.
- Результаты share-based TWR/average не годятся для cash+securities total equity без строгой классификации пополнений и переводов.
- PDF/CSV брокерский отчёт — независимый source; сверка не должна использовать тот же преобразованный ledger как «внешний эталон».
- Большая доля количественных научных результатов относится к NASDAQ/FX/FI-2010/crypto; переносимость на MOEX/SPB и конкретные matching правила требует локальных измерений.
- Для microstructure невалидно выводить точные fill probabilities из неполных candle records, а для ML — недопустимы `future` features.

## 6. Задания разработчику по результатам аудита

- [ ] **OSS-01 M0:** зафиксировать commit SHA каждого исходного файла и license/NOTICE в machine-readable `reference_manifest.json`; тогда дальнейшие обновления сторонних репозиториев не меняют основу спецификации.
- [ ] **OSS-02 M1:** воспроизвести резюмируемый cursor pipeline, но ошибки конца истории разделить; test resume/crash.
- [ ] **OSS-03 M2:** независимо реализовать eJournal test matrix, добавить decimal, cross-account and futures exclusions.
- [ ] **OSS-04 M4:** отдельный `reconstructed vs GetPositions` quantity audit с as-of и quality.
- [ ] **OSS-05 M8:** сравнить наши TWR/XIRR/Modified Dietz с независимыми вычислениями; forbid trade-as-external-flow.
- [ ] **OSS-06 M7:** реализовать TCA waterfall и test `sum(cost components)==total shortfall`, отдельно mark unrealized fills unavailable.
- [ ] **OSS-07 M7:** создать `IFillModel` с явной `matching_rule`; в SPB pro-rata не использовать FIFO без предупреждения.
- [ ] **OSS-08 M9:** PIT manifest и interval-aware test splitting.
- [ ] **OSS-09 M10:** интеграционный comparison holdout/QuantStats vs our risk engine на синтетике.
- [ ] **OSS-10:** CI проверяет наличие benchmark fixtures, license policy, тестов на двойной учёт комиссий и VM.

## 7. Как пользоваться этой ревизией

Работать по стадиям [07-roadmap-and-acceptance.md](07-roadmap-and-acceptance.md). Для каждой `OSS-` задачи создать тест, ADR и commit. Относиться к ссылкам как к воспроизводимым точкам входа, а не к рекомендации собирать чужие проекты и подключать к реальному торговому счёту.

Научные основания и дополнительные исследования вынесены в [10-academic-research-and-experiments.md](10-academic-research-and-experiments.md).
