# Третья волна исследования: не только TWAP — котировки, известные агенты, мотивы и типы времени

**Проверено:** 2026-11-18. Это продолжение [RESEARCH.md](RESEARCH.md) и [первого расширения](RESEARCH_EXPANSION_2026-11-18.md). **Никакие новые алгоритмы не объявлены протестированными на MOEX или СПБ.** Для каждого метода отделяем: (1) что действительно сделано в источнике, (2) что мы планируем перенести, (3) какие данные нужны, (4) какой тест должен опровергать ложные выводы.

## 1. Самое прикладное новое научное направление: Quote Volatility (QV)

**Статья:** Dimitar Bogoev, Arzé Karam, *Detection of algorithmic trading*, Physica A 484 (2017), 168–181. [Официальная страница издателя](https://www.sciencedirect.com/science/article/pii/S0378437117304673), [университетский полнотекстовый PDF](https://durham-repository.worktribe.com/preview/1358833/21713.pdf), [карточка Университета Дарема](https://durham-repository.worktribe.com/output/1358815/).

**Реальное утверждение статьи:** предложены отношения для обнаружения коротких эпизодов частой осцилляции лучших bid/ask с малым суммарным смещением (quote-volatility ratio) и отдельный индикатор быстрого price momentum. Авторы используют анонимный top-of-book поток по AAPL, Bund futures, USO ETF. Это распознавание **типа поведения**, а не подсчёт подлинных владельцев/роботов. ANN у авторов — эксперимент по распознаванию таких паттернов, не общедоступный идеально размеченный классификатор.

### Математика, непосредственно полученная из §2.1 статьи

Пусть внутри короткого окна имеются последовательные best ask `A_1...A_n`, best bid `B_1...B_n`.

```text
CarryAsk = SUM_{i=2..n} ABS(A[i] - A[i-1])
CarryBid = SUM_{i=2..n} ABS(B[i] - B[i-1])
BigAsk   = ABS(A[n] - A[1])
BigBid   = ABS(B[n] - B[1])

OscAsk = CarryAsk / MAX(BigAsk, ask_tick_size)
OscBid = CarryBid / MAX(BigBid, bid_tick_size)
QV_ask_candidate = OscAsk / MAX(OscBid, eps_ratio)
QV_bid_candidate = OscBid / MAX(OscAsk, eps_ratio)
```

У авторов свои правила для нулевых знаменателей (например, 0.01 в их tick environment). **Наша запись выше — адаптация, а не буквальное переписывание оригинальных граничных правил.** Для MOEX/СПБ требуется использовать реальный price step инструмента и выбрать `eps_ratio` на development данных, не подставлять 0.01 при всех тикерах. Отдельно считать `spread`, `best level size`, `oscillation_count`, `reversal_lag`, `directionality`. На полностью неизменных best prices `QV=not_applicable`, не infinity.

**Мини-пример (SYNTHETIC):** ask = 101.00 → 101.01 → 101.00 → 101.01 → 101.00; `CarryAsk=0.04`, `BigAsk=0`. При тик 0.01 `OscAsk=4` — в окне происходила осцилляция при нулевом суммарном изменении. Это подтверждает **частые обратимые изменения котировки**, но **не** подтверждает отдельный робот и не доказывает манипуляцию.

**Границы применимости:** обычный T-Invest L2/Book поток может иметь throttle и пропускать обновления на микросекундных масштабах. `quote_oscillation` считывает только *наблюдённые* колебания; пропуски не реконструировать фиктивно. Если `book_interupdate_ms` больше времени обсуждаемого эффекта, результат `INSUFFICIENT_BOOK_SAMPLING`. НЕ публиковать ярлык `spoofing`, `quote stuffing`, `манипуляция`: для этого необходимы дополнительные юридически и технически значимые доказательства и MBO.

**Наша реализация:** `QuoteOscillationDetector` с режимами `ask_only`, `bid_only`, `both`; три скорости окон 1/2/10 секунд (инженерный эксперимент, не универсальные пороги); сравнение с `baseline quote churn per regime` и контроль скачков рынка; оценивать как отдельный `market_activity_signature`, а не `confirmed_pattern_count`.

## 2. Сильнейший способ проверять число «роботов»: ABIDES с известной скрытой разметкой

### Код и верифицированные исходные файлы

- [ABIDES — исходный репозиторий](https://github.com/abides-sim/abides), [RMSC03 walkthrough](https://github.com/abides-sim/abides/wiki/RMSC03), [научная статья платформы](https://arxiv.org/abs/1904.12066).
- [ABIDES-NG — более новая самостоятельная версия](https://github.com/GabrieleDiCorato/abides-ng), лицензия **BSD-3-Clause**, проверен [LICENSE](https://github.com/GabrieleDiCorato/abides-ng/blob/main/LICENSE). Для воспроизводимости зафиксировать upstream SHA при запуске.
- [TWAPExecutionAgent.py](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/twap_execution_agent.py), прочитан код, blob SHA `3439c708f78deb7924e0b3ea8b3da77a8c9453f3`.
- [VWAPExecutionAgent.py](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/vwap_execution_agent.py), SHA `e4be197edd8c3448118cd9ea70c193926b3f8377`.
- [POVExecutionAgent.py](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/pov_execution_agent.py), SHA `c6071944334ae72cac687e82fa17a06a8b80f64b`.
- [TWAP tests](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/tests/test_twap_execution_agent.py), [VWAP tests](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/tests/test_vwap_execution_agent.py).

### Что конкретно делает код

**TWAP** `total_slices = ceil((end-start)/freq)`; при каждом запуске `slice_qty = ceil(remaining_quantity/slices_remaining)`, последний срез получает остаток. Следовательно **даже TWAP может менять размер дочерней заявки** при неполных исполнениях; наш fixed-q detector не должен считать любую смену q отдельным роботом.

**VWAP** распределяет объём согласно профилю (по умолчанию U-образный, в исходнике `weight_i ∝ 1 + ((i-mid)/mid)^2`), корректирует оставшийся объём при underfill. Наличие U-shape в рынке само по себе не является идентификатором одной программы.

**POV** раз в `freq` опрашивает объём торгов за `lookback_period` и вычисляет очередную заявку как долю `pov` от этого объёма; конечная заявка проходит через логику агента и исполнение, поэтому объём принтов может отличаться от размера дочерней заявки.

Оригинальный [RMSC03 пример](https://github.com/abides-sim/abides/wiki/RMSC03) запускает POV агента, просыпающегося раз в секунду, и предлагает разные уровни `0.01,0.05,0.1,0.5` в идентичных сценариях. В сравнении с «базовым рынком без агента» видно влияние на цены и поток. **Это синтетическая модель** — её абсолютные частоты не переносятся на MOEX без оценки.

### ОПРЕДЕЛЁННЫЙ протокол нашего blinded evaluation

1. Создать `ABIDESScenarioManifest`: `scenario_id, upstream_sha, seed, session_utc, exchange_calendar, background_agents, execution_agent_types, agent_ids, config_hash, source_license`.
2. Запустить **контроль** (те же фоновые агенты/seed без injected execution) и **опыт** с 1–10 TWAP/VWAP/POV agents, включая одинаковые фазы и размеры, разные фазы, одну программу с несколькими независимыми подпотоками, недоисполнения, random jitter.
3. Записать **привилегированную истинную историю** `truth_internal`: действия агента, parent ID, child order IDs, fills, собственное время постановки и исполнения, start/end. Реализация agent logging может потребовать адаптера; не считать это готовой выгрузкой из ABIDES.
4. Создать независимую **публичную проекцию** `projection`: только информация, которую реально отдаёт T-Invest: принты/сайз/цена/направление при подтверждённой семантике; L2 агрегаты с заданной дискретизацией 100/250/500мс или измеренной реальной частотой; убрать agent/order IDs.
5. Запустить наш детектор без доступа к `truth_internal`, зафиксировав параметры ДО анализа. Затем на стороне evaluator сопоставить найденные event IDs с internal child fills, зафиксировать ошибки attribution и false bot count.
6. Повторить для downsampling book, timestamp rounding, partial fills, latency, missing trades, pro-rata-like vs price-time simulator (если поддерживает) как **синтетических альтернатив** без утверждений о конкретном matching rule СПБ.
7. Репорт `identifiable_pattern_count` отдельно от `true_agent_count`; для неразличимых одинаковых потоков метрика не должна награждать угадывание физического количества агентов.
8. Контрольные пары: `background-only` и `with_agent` на одинаковых seeds позволяют измерить разницу в сигнале; **не делать** наивное вычитание принтов — injected agent меняет поведение рынка эндогенно.

Качество: event-level precision/recall; matched pattern recall, leakage, false discoveries/hour; detected-versus-identifiable count; calibration; latency. Для каждого класса отдельные наборы unseen seeds/days.

## 3. STUMPY: обнаружение повторяющихся мотивов, даже без ровного времени

**Исходники:** [STUMPY](https://github.com/stumpy-dev/stumpy), [Incremental Matrix Profiles tutorial](https://stumpy.readthedocs.io/en/latest/Tutorial_Matrix_Profiles_For_Streaming_Data.html), [исходник stumpi.py](https://github.com/stumpy-dev/stumpy/blob/main/stumpy/stumpi.py), [научная статья JOSS](https://doi.org/10.21105/joss.01504).

**Реальная методика:** matrix profile — расстояния от каждого отрезка временного ряда до наиболее похожего отрезка, используется для поиска повторяющихся мотивов и необычных фрагментов. STUMPY поддерживает потоковое обновление `stumpi`. В источнике это общий инструмент анализа временных рядов, **не готовый идентификатор торговых алгоритмов**.

**Наше применение (эксперимент):** для каждого инструмента генерировать равномерный вектор признаков `[dBidTicks,dAskTicks,dBidQty,dAskQty,buyPrintCount,sellPrintCount]` в `dt=100/250/500ms`. Считать profile в одно- и многомерной проекции, обнаруживать повторяющиеся **последовательности** «переставил best price → обновился объём → прошёл print → возврат», не требуя фиксированного периода. Сравнить profile peak с простыми корреляциями/евклидовым nearest-neighbor и отрицательными синтетическими контролями.

**Нужно обязательно:** запрещать самосопоставление перекрывающихся subsequences (exclusion zone), учитывать нестабильные признаки и нормализацию только на прошлом, не фиксировать z-score для постоянного нулевого ряда. Обнаруженная закономерность = `behavioral_motif` с `overlap_adjusted_repeat_count`, `template_length`, `recurrence_distribution`, `null_score`; не гарантирует один и тот же владелец.

## 4. hftbacktest — эталон replay, latency и book sampling

**Проект:** [nkaz001/hftbacktest](https://github.com/nkaz001/hftbacktest), [документация](https://hft.readthedocs.io/en/latest/). Это прежде всего симулятор торговли/исполнения с учётом задержек feed и позиции в очереди, а не детектор роботов.

**Наш перенос:** dataset replay со сценариями разной задержки биржевого потока, synthetic fills, queue-uncertainty и отличием `order submission time` от `trade print time`. Проверять: можно ли действительно восстановить **ритм постановки**, если мы видим лишь исполнения? Ожидаемое поведение: в некоторых сценариях T идеально регулярен на стороне child orders и нерегулярен по prints; система не должна навязывать точное T исходному алгоритму.

**Важно:** данные hftbacktest могут включать детальный L2/L3 другой площадки; adapter должен явно *ограничить* доступ до возможностей российского провайдера для честной оценки.

## 5. Что говорят научные работы об идентификаторах и верхних границах вывода

- [Sato & Kanazawa, Physical Review Letters 131, 197401 (2023)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.131.197401), [arXiv:2301.13505](https://arxiv.org/abs/2301.13505): при определённых модельных предположениях параметры механизма order splitting могут оцениваться по наблюдаемой длительной корреляции знаков. Это **не** восстановление списка конкретных роботов.
- [Sato & Kanazawa, Physical Review Research 5, 043131 (2023)](https://journals.aps.org/prresearch/abstract/10.1103/PhysRevResearch.5.043131), [arXiv:2308.01112](https://arxiv.org/abs/2308.01112): девять лет данных на уровне **конкретных торговых счетов**, важный источник для понимания статистики child orders, но такая truth-подробность не присуща обычным публичным prints.
- [Bogoev & Karam 2017](https://www.sciencedirect.com/science/article/pii/S0378437117304673): короткие oscillation episodes top-of-book раскрывают **активность алгоритмических стратегий**, а не число владельцев.
- [Statistical Predictions of Trading Strategies in Electronic Markets, JFEC (2025)](https://academic.oup.com/jfec/article/23/2/nbae025/7826742): исследование использует уникальные метки участников и торговых алгоритмов в биржевых данных; **не** применить заявленную supervised классификацию на T-Invest без truth labels.
- [Gaussian process-based algorithmic trading strategy identification (2015)](https://doi.org/10.1080/14697688.2015.1011684): классификация аккаунтов/алгоритмов с использованием лимитных заявок и privileged audit trail E-mini; по обычному L2 аналогичная персональная классификация недоступна.
- [Angstmann & Gebbie (2026), Event-Time Order-Flow Memory, Operational-Time Impact](https://arxiv.org/abs/2609.13715): разделить event clock (индекс принтов), physical clock (UTC), operational time (ликвидность/активность), не смешивать выводы. Работа — препринт/теоретическая модель, не готовый детектор.
- [A machine learning attack on illegal trading (2023)](https://www.sciencedirect.com/science/article/pii/S0378426622003156): DTW+extreme-value theory в задаче рыночного надзора с broker-specific account data. У нас можно заимствовать только сравнение похожих форм, **не** юридическую классификацию подозрительной торговли или claims об обнаружении преступления.

## 6. Новые тесты для независимого ТЗ

| Код | Проверка | Ожидаемый вывод |
|---|---|---|
| Q01 | Best ask: 101 → 101.01 → 101 → 101.01 → 101; no trades | Quote oscillation observed; fixed-trade TWAP не видит событий |
| Q02 | Один back-and-forth quote при feed loss | `INSUFFICIENT_BOOK_SAMPLING`, не confirmed |
| Q03 | Ценовой тренд с большим CarryAsk и BigAsk | Не путать с быстрым возвратным осциллированием |
| Q04 | 2 независимых агента конкурируют за best bid | Общая oscillation signature, true agent count = unknown для публичных данных |
| A01 | ABIDES без injection vs с POV агентом, одинаковый seed | Измерять ложные детекции и прирост recall; нельзя вычитать разные tape print by print |
| A02 | ABIDES TWAP underfill меняет q срезов | Не объявлять новый робот на каждой смене q |
| A03 | ABIDES VWAP U-shape + рыночный U-shape | Нельзя подтвердить робота по общему профилю без выделяемых evidence events |
| A04 | 2 синтетических агента с идентичным observable stream | Вернуть indistinguishable behavior, не 2 confirmed physical robots |
| A05 | Скрыть internal order/agent IDs, отдать только L2/prints | Детектор не получает ground truth до scoring |
| M01 | Matrix profile повторяющихся 4-этапных реакций с переменным интервалом | `behavioral_motif` при заданном null, не fixed TWAP |
| M02 | Повторение из-за единого рыночного триггера на всех бумагах | Не записывать отдельного владельца на каждом инструменте |
| C01 | Perfect schedule child orders, irregular partial fills/queue | Нельзя приравнивать print interval к order submission interval |
| C02 | Одни и те же prints с q в штуках и в лотах | Нормализация lot size обязательна; detected q не меняется от единиц |
| C03 | 100ms L2 downsampling стирает 20ms quote oscillation | Нет сигнала; нельзя придумывать события между снимками |
| X01 | Event-time sign ACF vs clock-time FFT дают разные закономерности | Отдельные пояснения, разные временные шкалы и метрики |

## 7. Приоритет внедрения (рекомендация)

1. **Сейчас, без живых данных**: подключить ABIDES как внешний generator/ground-truth test fixture и реализовать отдельный projected/public data export; это самый сильный способ доказать, что мы не просто распознаём случайную ритмику.
2. **После stage-1 baseline**: при наличии достаточной частоты book — `QuoteOscillationDetector`, как принципиально иной сигнал для пассивных алгоритмов.
3. **В сравнительных исследованиях**: STUMPY matrix profile для поведенческих мотивов и hftbacktest для контрпримеров latency/partial fill.
4. **Отдельно, позднее**: исследование model-based оценок среднего числа active hidden parents. В UI никакого «physical bot count = N» без полноценной идентификации.

## 8. Повторяемая проверка пригодности каждого метода

Для каждого эксперимента: upstream repo + commit SHA, лицензия, scripts, seed, simulator truth schema, projection schema, source capabilities, interval, train/holdout split, score breakdown, evidence events, false-positive controls, computational cost и **отдельное решение ADOPT / EXPERIMENT / REJECT**. Перед портированием чужого кода проверять лицензию, не добавлять Python runtime в C# Core, не переносить private trader/account labels на публичную биржевую ленту.

**Результат этого документа: план с прямыми ссылками и формулами. Не утверждать, что эксперимент или live проверка уже осуществлены.**
