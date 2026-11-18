# 04. Финансовый учёт, P&L и методологии

**Приоритет:** M2–M4, P0. Этот документ определяет формулы, ограничения и приёмку расчётного ядра, которое обязано быть детерминированным.

## 1. Различные P&L нельзя смешивать

- `realized_trade_pnl`: результат закрытой части позиции (по FIFO / weighted-average), без расходов и иных потоков.
- `unrealized_mark_pnl`: нереализованная переоценка ещё открытой части относительно базы данного метода.
- `gross_economic_pnl`: реализованный + нереализованный + инвестиционные доходы, без торговых издержек (предусмотреть разную классификацию доходов).
- `net_trading_pnl`: gross минус комиссии/биржевые расходы, финансирование и прочие торговые издержки по выбранной политике.
- `after_tax_pnl`: net после реально списанных налогов и удержаний, явно не считать налоговые расходы идентичными расчётным обязательствам.
- `account_equity_change`: изменение NAV всего счёта, очищенное от внешних потоков и с учётом валютной переоценки.
- `cash_pnl`: денежные поступления/списания вследствие торговых операций; может не совпадать с экономической прибылью из-за купли активов и margin collateral.
- `futures_realized_settlement_pnl`: денежная вариационная маржа, отнесённая к инструменту за период.
- `futures_open_mark_pnl`: переоценка открытого срочного риска после последней расчётной базы и в выбранное as-of время.

Пользователь выбирает: profit basis, gross/net, include/exclude taxes, as-of, day basis, currency, aggregation scope. UI обязан объяснить, что именно суммируется.

## 2. Бухгалтерская модель (двойная запись)

Ввести ledger accounts: CASH_{currency}, SECURITIES_COST_{instrument}, DERIVATIVE_VM_{instrument}, ACCRUED_FUNDING, FEES, TAXES, DIVIDENDS, COUPONS, FX_REVALUATION, TRANSFERS_IN/OUT, SUSPENSE_UNMATCHED. Для каждого канонического события генератор создаёт balanced postings с currency-aware book. Разные валюты не должны балансироваться смешанным сложением без FX conversion book. Формат `event_uid -> postings[]`, идентичность вычисления защищена версионированной политикой.

Имеется три времени: `trade_time`, `settlement_time` и `accounting_booking_time`. Брокерские cash changes могут быть записаны позже исполнения, что необходимо учитывать в reconcile (T+1/clearing). Unsettled commitments и settled cash различаются.

## 3. Cash-flow-adjusted NAV

Для всего счёта при согласованных оценках `V0, V1`, внешних внесениях `D` и выводах `W` в общей валюте, при отсутствии неторговых переводов и при корректной оценке потоков:

```text
Absolute P&L over period = V1 - V0 - Deposits + Withdrawals
```

Для нескольких потоков конвертация каждого на его дату/время обязательна; внутренние переводы между собственными счетами при консолидации взаимно уничтожаются (если переводы бумаг — учитывать их рыночную стоимость при передаче и преемственность cost basis). Это не определяет процентную доходность: TWR и XIRR считать отдельно. Внутридневной NAV возможен только при наличии согласованных цен as-of и cash/position snapshots.

### TWR

Для каждого подинтервала между внешними денежными потоками вычислить доходность на пред-потоковой стоимости, затем геометрически связать: `TWR = product_i (1+r_i) - 1`. При отсутствии pre-flow valuations сообщать приближение и его допущения (например, Modified Dietz); не выдавать точную TWR.

### XIRR / MWR

Решить NPV cashflow equation на датах: `sum_i CF_i / (1+r)^((t_i-t_0)/365)=0`, включая финальную стоимость как closing flow, с честной обработкой нескольких/отсутствующих корней. Нельзя представлять XIRR как недельный P&L в рублях. При неединственном корне дать предупреждение и не присваивать произвольную ставку. Дата и convention day count версионируются.

## 4. Акции/ETF/облигации: matched lots

Вход: fills в штуках, side, цена/денежное возмещение, комиссия; исторический lot size и corporate actions.

**FIFO:** для close match самые ранние открытые лоты данного account/instrument/cost pool (параметры стратегии, если реализован subledger); при short sell создаётся short liability lot; flip делится на close старой стороны + open новой.

**Weighted-average:** после покупок по одной стороне обновлять `cost_per_unit = (old_qty*old_cost + new_qty*new_price)/new_total_qty`; частичный close сохраняет прежнюю среднюю оставшейся части. При шорте зеркально с учётом signed inventory. Разделить trade gross price и allocated fee.

```text
Long realized gross  = sum(close_qty * sell_price) - matched_open_cost
Short realized gross = matched_short_open_proceeds - sum(cover_qty * buy_price)
Realized net          = realized gross - allocated fees and charges (by policy)
Open P&L             = market_value(open_quantity, mark_time) - remaining_cost_basis
```

При split, consolidation, redemption, cash-in-lieu — сохранить total cost и пересчитать количество/цену согласно действию, trace transformations. При конвертации облигаций учитывать clean/dirty price, НКД и купоны раздельно. Дивиденды и купоны не являются ценовым P&L сделки и должны иметь собственный component, но могут входить в total return. Доходы по фондам денежного рынка — NAV change, а не искусственные «купоны».

**Валютные инструменты:** P&L instrument-native, затем FX translation. Для согласованного отчёта в RUB можно отдельно разложить change into local-market-return / currency-return / interaction, указав выбранный метод decomposition. Не смешивать FX от самого инструмента с FX конвертацией денег.

## 5. Фьючерсы: обязательная отдельная книга

Фьючерсные операции имеют расчётную базу и variation-margin settlements, а не обычное «заплатил полную стоимость бумаги». Нельзя автоматически суммировать **и** trade-price difference, **и** всю уже начисленную/списанную вариационную маржу, так как возникнет двойной P&L.

Для контракта хранить per-effective-date:
- price quoted points и валюту котировки;
- `min_price_increment` и `min_price_increment_amount` / денежную стоимость пункта;
- lot/contract multiplier, settlement currency;
- contract/underlying UID, expiration/date, settlement calendar;
- funding methodology, если бессрочный контракт;
- историю valuation anchor после каждого клиринга/переоценки.

Пример расчёта для **одного интервала при постоянной стоимости шага**:

```text
MoneyPnL = position_contracts * (price_end - price_start)
           / min_price_increment * min_price_increment_amount
```

Это **условная** формула: при меняющейся стоимости шага, переменном контрактном коэффициенте, смене расчётной базы или особенностях settlement нужно использовать спецификацию на каждом временном сегменте и фактические брокерские postings. Источник маржи и теоретический mark должны быть отдельными величинами; для разных типов инструмента mapping подтверждается fixture.

**Futures daily fact:**
1. Начало торгового/клирингового периода: qty, anchor, cash VM balance.
2. Внутри: signed fills; комиссия каждой сделки; изменение qty; ограничение рисков; intraday mark.
3. Клиринг: фактически зачисленная и удержанная VM с link to settlement time.
4. Фандинг: если отдельное `OPERATION_TYPE_FUNDING` или включено в маржу по правилам конкретного контракта — пометить `funding_booked_via` и не прибавлять повторно.
5. После клиринга: новая settlement anchor; delta-VM от anchor отдельно от уже booked margin.
6. За день: realized settled VM + unsettled change in futures equity (если валидно) - комиссии - financing, согласно выбранному accounting policy.
7. Экспирация: закрытие/поставка/перенос позиции не скрывать; новое поколение контрактов создаёт новую series.

**Инварианты:** variation margin postings по инструментам плюс explicit unmatched/aggregate должны совпадать с cash movements; суммирование инструментальных и агрегированного события запрещено. При отсутствии цены клиринга помечать open-mark как provisional, а не моделировать точный результат.

**Бессрочные фьючерсы:** хранить фактические операции funding отдельно от model-estimated funding; тип и смысл T-Invest operation приоритетнее упрощённой биржевой формулы, избежать triple accounting (VM + funding + open mark). Контрактно-специфические корректировки только через instrument policy version.

## 6. Опционы

Готовить интерфейсы при M2; полноценная поддержка P1/P2 после futures:
- premium-style vs futures-style, clearing-specific rules, option type/style, underlying, strike, expiry, multiplier;
- buy/sell premium and opening/closing position, exercise/assignment, cash vs physical delivery;
- exercise creates underlying position at correct basis; expiry can realize 0 or settlement cash; charges independently;
- greeks and implied volatility только при валидном источнике котировок/model parameters;
- покрытие истории опционов обязательно через `GetOperationsByCursor`, а не deprecated operations endpoint.

## 7. Комиссии, налоги, заём, корпоративные действия

Развести по component codes:
`BROKER_FEE`, `EXCHANGE_FEE`, `OTHER_ORDER_FEE`, `MARGIN_INTEREST`, `OVERNIGHT`, `FUNDING`, `TAX_WITHHELD`, `TAX_REFUND`, `DIVIDEND`, `COUPON`, `BOND_ACCRUED_INTEREST`, `SERVICE_FEE`, `TRANSFER_COST`, `OTHER`, `UNKNOWN`.

Нельзя механически считать все списания как комиссию, все поступления как прибыль. Fee allocation policy: exact order match if feasible, proportional fill notional otherwise, unmatched account overhead in separate bucket. Если fee приходит и в embedded operation и как отдельный cash event, подписать идентичность, создать ОДИН fee component и второй link как свидетельство, не два postings. Налоги — отдельно paid/withheld/estimated, tax-year and account.

## 8. Внешние потоки

Deposits, withdrawals, internal transfers, securities transfers, margin collateral, FX conversion and cash-settlement are separate classes. Перевод между собственными счетами должен иметь transfer_pair, согласованные даты/валюту/стоимость. Не раздувать доходность за счёт пополнения и не нарушать total P&L при переводе актива без продажи.

## 9. Временные зоны и границы дня

Каждое событие имеет:
- UTC timestamp (event time);
- exchange time zone/calendar (например, Europe/Moscow по инструменту);
- trade date по календарю площадки;
- clearing/settlement date по спецификации;
- recorded/observed/available time для данных.

Группировки допускают разные day basis: `UTC_CALENDAR`, `MOSCOW_CALENDAR`, `EXCHANGE_SESSION`, `CLEARING_DAY`. Не выбирать один без передачи в API. Для выбранного периода использовать полуоткрытый интервал [from,to) во избежание двойного счёта событий на границах.

## 10. Reconciliation formulas / reconciliation ladder

1. `QtyClosing = QtyOpening + Buys - Sells + CorporateActions + Transfers + Expiration` отдельно для каждого account/instrument.
2. `CashClosing(ccy) = CashOpening(ccy) + sum(SettledCashEvents(ccy))`.
3. `Equity = Cash + market_value_assets + recognized_futures_open_component + other_claims - liabilities` с оговоркой о broker valuation convention.
4. `PnlByInstrument + PnlUnattributed + PnlUnallocatedFees + PnlFX = PnlAccount` **только** если совпадают basis, currency, as-of и coverage.
5. `TotalPnL(day1..dayN) == TotalPnL(combined interval)` для абсолютного результата при общей методологии периодов и coherent valuations. Исключение отдельного дня показывает сумму оставшихся daily facts, а не пересчитанный edge-to-edge NAV через временной разрыв.
6. Для каждой строки P&L есть `pnl_component`, `quality_status`, `source_trace`, `policy_hash`, `run_id`.

Tolerance policy: округление по minor currency unit, спецификации и брокерскому отчёту; порог для каждого check указан отдельно, не один универсальный допуск «1 рубль». Не достигший контрольного порога reconciliation должен быть виден как ошибка качества данных.

## 11. Набор обязательных golden fixtures (минимум)

| ID | Сценарий | Ожидаемый контроль |
|---|---|---|
| G01 | buy 100×100, buy 100×110, sell 100×120 | FIFO 2000, AVG 1500 до комиссий |
| G02 | buy 10, partial sell 3, sell 7 | нулевой остаток; net сумма matches |
| G03 | short 10×120, buy 15×100 | 10 закрыли + short profit 200, 5 new long |
| G04 | order 100 units filled 20+30+50 | 3 fills, 1 parent order, no lost fee |
| G05 | 1 комиссионное событие в stream и cursor | одно ledger fee posting |
| G06 | changed operation.id on re-import | no duplicate economic event; revision audit |
| G07 | VM + aggregate VM event | one economic cash VM total |
| G08 | changing tick value midcontract | segmented calculation, correct money |
| G09 | perpetual future with funding in VM | no second posting |
| G10 | FX conversion USD→RUB, mixed cash | no false P&L without mark moves |
| G11 | deposit midperiod + mark move | correct absolute pnl, time weighted return |
| G12 | split 2:1, then sell | quantity doubled, original total cost held |
| G13 | inter-account securities transfer | consolidated pnl invariant |
| G14 | coupon+accrued interest+bond sale | income separated from price pnl |
| G15 | missing price for open position | provisional and never zero default |
| G16 | trade at midnight / clearing after 00:00 | deterministic date attribution |
| G17 | broker fee assigned only to account | unmatched fee visible, no forced allocation |
| G18 | option expiry without trade close | recognized event and no phantom open position |
| G19 | 14.11 excluded from 09–15.11 daily report | sum of selected independent daily facts |
| G20 | tiny decimal amounts + precision boundary | result exact after documented rounding |

Golden input fixtures должны быть анонимными и храниться в репозитории; численные expected outputs независимо вычислены контрольными таблицами/ручными доказательствами. Property-based: qty conservation, FX conversion roundtrip within tolerance, idempotency, no negative residual for long lot, sign symmetry in linear-contract fixture, no future information in historical as-of.

## 12. Открытые вопросы для первых live-tests

- Какие конкретно строки broker report сопоставляются with API VM и funding для NVDAperpA?
- Какие timestamps действительно использует broker for daily realized margin?
- Содержит ли broker API историческую стоимость шага на каждую дату или потребуются archived instrument specs?
- Как отражаются комиссии за заём, смешанные с другими движениями на том же счёте?
- Обрабатывается ли переход между этапами экспирации/rollover без смены экономического risk?
- Можно ли восстановить совершённые сделки старого периода с trade_id / order_id точно, или нужен дополнительный отчёт?
- Какие правила цены и FX применяет брокер к показателю его собственной `expected_yield`?

До ответы на эти вопросы отдельные метрики могут быть `provisional`; ошибка лучше искусственной точности.

## 13. Ссылки

- [OperationsService / типы операций](https://developer.tbank.ru/invest/services/operations/methods)
- [Проблемы операций и IDs](https://developer.tbank.ru/invest/services/operations/operations_problems)
- [FAQ: вариационная маржа и отчёт](https://developer.tbank.ru/invest/services/operations/faq_operations)
- [Instruments FAQ: стоимость шага фьючерса](https://developer.tbank.ru/invest/services/instruments/faq_instruments)
- [Сервис данных и дневные свечи фьючерсов](https://developer.tbank.ru/invest/services/quotes/head-marketdata)
