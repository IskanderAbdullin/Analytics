# Проверки до и в ходе реализации: что ещё НЕ доказано

Все пункты являются верифицируемыми **открытыми вопросами**, а не препятствием для написания synthetic baseline. Статус первоначально `UNVERIFIED`.

| ID | Вопрос | Как доказать | Этап / статус |
|---|---|---|---|
| D01 | Реальные границы доступа к daily trade-history, формат ZIP/CSV и ограничения по каждому инструменту | Официальная документация + только read-only smoke по 1 дню + source SHA | 1 / UNVERIFIED |
| D02 | Какая точность `TRADE_TS` в реальных архивах MOEX/СПБ; не округляет ли provider | Distribution fractional milliseconds / exact repeats per source | 1 / UNVERIFIED |
| D03 | Значение `DIRECTION`: сторона агрессора, покупателя либо специфичное биржевое поле | Официальная схема + сравнение с orderbook near trade; при сомнении UNKNOWN | 1 / UNVERIFIED |
| D04 | Есть ли вообще достаточно полные трейды СПБ и по каким NEO/режимам | 3–5 UID и даты, coverage matrix, `TRADE_SOURCE` | 1 / UNVERIFIED |
| D05 | Возможны ли множественные executions одного order с одинаковой отметкой времени | Тест с видимыми print bursts, статистика timestamps/price/size; trade ID если существует | 1 / UNVERIFIED |
| D06 | Можно ли восстановить stream gap из GetLastTrades / history-trades и в какие сроки | Документация, эксперименты с искусственным disconnect, контроль дубликатов | 3 / UNVERIFIED |
| D07 | Актуальные квоты market-data stream, число UID на connection, book frequency, drop policy | Официальные limits + timestamps instrumented stream | 3 / UNVERIFIED |
| D08 | Платформа/торговый режим/аукционы: календарь и локальное время | Официальные торговые расписания/брокерские схемы; тест смены сессий | 1–3 / UNVERIFIED |
| D09 | Реально доступный MBO с order ID (скорее всего НЕ предполагать) | Только первичная спецификация источника и подтверждение live данных | 4 / UNVERIFIED |
| D10 | Лицензия на сохранение/распространение архивов и производных результатов | Договорные правила брокера/биржи, проверка перед публикацией | все / UNVERIFIED |
| D11 | Доступны ли провайдерские data для конкретного UID после листинга/остановки/перевода на другой режим | Instrument catalog + история в нескольких режимах | 1 / UNVERIFIED |
| D12 | Насколько часто события по обеим сторонам синхронизированы целыми секундами на MOEX | Null stats across >=10 sessions; контроль metaorder artifact | 2 / UNVERIFIED |
| D13 | Действительно ли модель лучше rule-based baseline при переменных объёмах | Held-out tests с известной truth + null и PR-AUC | 4 / UNVERIFIED |
| D14 | Какие пределы производительности на Windows / OsEngine в реальном workload | Изолированный .NET benchmark, UI off/on, отставание и GC | 3 / UNVERIFIED |

## Стандарт протокола исследования

Каждый пункт закрывается записью: `checked_at_utc`, `source_url`, `instrument_uid` (если применимо), `session_date`, `observed_behavior`, `dataset_hash`, `method`, `version`, `status`, `remaining_uncertainty`. История результатов append-only, при изменении провайдера проводить повторный тест.

## Приоритет первых проверок

1. Доказать, что именно история обезличенных **сделок**, а не годовые свечные архивы, доступна для выбранного UID (MOEX, затем СПБ).
2. Доказать точность времени и значение стороны. Без этого можно проверить математику, но нельзя уверенно классифицировать покупателей/продавцов.
3. Измерить абсолютную/относительную периодичность на нулевой модели, прежде чем выдавать «количество роботов».
4. Только затем включить live, book и ML.

Нельзя подменять `UNVERIFIED` правдоподобным предположением. Если требуется секрет, оператор задаёт его локально, не передавая ни через UI, ни через git.


## Новые проверки из open-source исследований (18.11.2026)

- D15 / UNVERIFIED — может ли timestamp resolution реального T-Invest позволить 100/250/500ms time bins? Проверить распределение подмс меток, aliasing и частоту пропусков.
- D16 / UNVERIFIED — как по MOEX/СПБ соотносятся пики в начале секунды и минуты (Chen/Chan/Chang 2022, Muravyev 2022)? Оценить `phase modulo 1s/60s` по инструментам/режимам и random-shift null.
- D17 / UNVERIFIED — превосходит ли `FFT+phase matcher` обычный fixed-volume detector на нескольких реальных режимах ликвидности? Полноценный blinded stage-2 test.
- D18 / UNVERIFIED — насколько плох аггрегированный L2 для детекции пополнения на отдельных тиках при реальном уровне quote sampling T-Invest? Синтетический high-frequency L3→downsample→L2 test.
- D19 / UNVERIFIED — сможет ли BOCPD отличить начало нового направленного режима от краткого общего биржевого всплеска лучше EWMA/CUSUM? False positives per instrument-day.
- D20 / UNVERIFIED — право повторно использовать код сторонних репозиториев (MIT/BSD GPL/absent), notebook outputs, licenses datasets? File-level license audit и version pin.

Новый [разбор исходного кода и статей](RESEARCH_EXPANSION_2026-11-18.md); все пункты остаются UNVERIFIED до отдельного эксперимента.

## Новые неопределённости (третья волна, 18.11.2026)

- D21 / UNVERIFIED — можно ли на L2 T-Invest увидеть достаточное количество перестановок best bid/ask для подхода Bogoev–Karam? Нужна частота 10ms–100ms и измерение пропусков; при book throttle часть эффекта принципиально необозрима.
- D22 / UNVERIFIED — доступны ли в ABIDES-NG срезы privileged parent/child orders/fills для создания blinded labels без модификации симулятора? Задокументировать, что требуется логировать отдельно.
- D23 / UNVERIFIED — насколько хорошо ABIDES book dynamics калибруется к акциям MOEX / СПБ / NEO? Даже высокий recall в ABIDES не есть проверка на реальном рынке.
- D24 / UNVERIFIED — каков timestamp gap между появлением child order и print при конкретных режимах ликвидности и правилах matching; что может делать наш детектор при разных queue model?
- D25 / UNVERIFIED — Matrix Profile/DTW поверх L2 не распознаёт ли общерыночные реакции и системные новости вместо отдельных ботов? Controlled common-trigger scenarios.
- D26 / UNVERIFIED — есть ли информационный прирост `QuoteOscillationDetector` относительно простого `best bid/ask update count` и `spread volatility` на слепой выборке?
- D27 / UNVERIFIED — какие свойства замены MBO→L2→throttled L2 теряются и насколько быстро, при ценах/лотах неликвидных инструментов; проверить на синтетической source-of-truth.
- D28 / UNVERIFIED — есть ли независимые labels реальных алгоритмов MOEX/СПБ, законно доступные для benchmark? Пока нет; реальное физическое количество считать `unknown`.

Источник и подробный experimental protocol: [RESEARCH_EXPANSION_2026-11-18_PART2.md](RESEARCH_EXPANSION_2026-11-18_PART2.md).
