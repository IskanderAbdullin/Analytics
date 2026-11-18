# Этап 4 — расширенные классы алгоритмов, стакан, ML и metaorders

**Предусловие:** этапы 1–3 с воспроизводимой статистикой и healthy online/replay. **Главное правило:** расширять только то, что наблюдаемо, и не выдавать агрегированные L2-изменения за точную историю индивидуальных биржевых заявок.

## 1. Набор независимых детекторов

| Детектор | Вход | Вывод | Ограничение |
|---|---|---|---|
| Variable-size TWAP | Prints | Ритм с изменяющимся объёмом | Ровный ритм ≠ уникальный робот |
| POV / volume participation | Prints + рыночный объём | Связь объёма потока с оборотом рынка | Причинность не доказана |
| VWAP-like | Prints + профиль активности | Сходство с целевым intraday volume profile | Не доказывает конкретную VWAP стратегию |
| Iceberg-like replenishment | Trades + L2 | Повторное пополнение на цене | В L2 нет ID ордеров; native iceberg не доказать |
| Ladder / grid | L2 | Серии объёмов на ценовых ступенях | Это могут быть независимые участники |
| MM-like quoting | L2 + trades | Стабилизация двухсторонних котировок | Нет участника / инвентаря |
| Reactive | L2 + prints | Повторяющаяся реакция на наблюдаемый стимул | Общий внешний фактор искажения |
| Metaorder-like | Prints + quotes | Вероятные серии одного направления и их impact | Скрытое родительское поручение не наблюдается |

Каждый детектор имеет `evidence_kind`, `attribution_level`, `limitations`, `min_data_quality`, `config_version`, `null_model`; confidence только после валидации своей модели.

## 2. Variable-size TWAP

Найти равномерный временной ритм **без фильтра по одинаковому q**. Сначала определять `T,phase` по weighted impulses событий и фазовой концентрации; далее проверять, что условная последовательность объёмов статистически отличается от случайных принтов на такой же фазе и частоте. Модели размеров: `q_i = q0 + noise`, `q_i ~ categorical({q_a,q_b,...})`, `q_i ~ lognormal truncated`. Отдельно учитывать дробление одной сделки на исполнения, чтобы не превращать пачку принтов в «много циклов».

Контроль: вероятный общий метроном рынка от Muravyev et al. (2022) и Spectral Volume Models (2025) должен объясняться **market-wide component**; индивидуальный алгоритм регистрируется только с выделяемым и подтверждённым подмножеством событий и превышением условного null.

## 3. POV/VWAP-кандидаты

**POV-признак:** в фиксированных или скользящих окнах `V_candidate(w) ≈ beta * V_market(w)`. Требования: оценить `beta` только на прошлом, проверить стабильность и отдельную прогнозную точность на новых окнах; baseline `beta=const` сравнить с независимым trend/seasonality estimator. На окнах с low volume — интервалы неопределённости/отказ.

**VWAP-like:** сравнить `candidate volume intensity` с заранее рассчитанным историческим U-shaped профилем рынка с point-in-time ограничением. Распознаватель не видит цель алгоритма, поэтому выдаёт «совместимо с распределением по профилю», а не точный тип реализации VWAP.

**Режим:** не смешивать собственное исполнение алгоритма с фоновым `V_market` без leave-one-out корректировки — иначе механическая корреляция. Результаты без устойчивого out-of-sample преимущества над простыми baseline не включать в online.

## 4. Айсбергоподобное поведение по L2

Источники: T-Invest агрегированный OrderBook Stream, синхронизированный с prints. Контроль точности времени и редкой дискретизации стакана; у T-Invest действует отдельное ограничение обновлений book (сверить документацию на дату внедрения).

Кандидат `replenishment`, если (a) у уровня `p` наблюдался resting volume `Q_before`; (b) подтверждены сделки на этом уровне; (c) вскоре появляется/сохраняется объём `Q_after` на том же `p`; (d) эпизод повторяется с более высокой частотой, чем обычное обновление стакана в сходных условиях. На L2 это **видимое повторное пополнение**, а не доказанное native iceberg.

Литература: Zotikov & Antonov, *CME Iceberg Order Detection and Prediction* (2019) https://arxiv.org/abs/1909.09495 . Авторы различают native и synthetic icebergs, используют сведения о trade-summary и изменениях конкретных ордеров и модель Kaplan–Meier для цензурированных объёмов. Наш план: перенести **структуру проверки гипотезы + survival/censoring**, **не переносить** CME-specific признаки order ID/MBO на T-Invest L2.

Модель: `replenishment_event`, `price_level`, `post_trade_refill_time`, `observed_executed_lots`, `visible_lots_before/after`, `book_sampling_gap`; результат `iceberg_like` c `not_identifiable_as_native`. Объём скрытой части не выдавать точным; по умолчанию null, при калибровке диапазон.

## 5. Сетка/маркет-мейкер/реактивное поведение

**Grid-like:** обнаруживать несколько параллельных уровней `p0 + k * step` с повторной синхронной коррекцией объёмов; признаки: расстояния в тиках, длительность поддержки, повторяемость появлений и исчезновений после сделки, относительная симметрия. Контрпример — статический стакан с независимыми заявками на круглых ценах.

**MM-like:** score по симметрии / асимметрии bid-ask, стабильности spread, реакции на midprice, частоте обновлений. Не утверждать, что bid и ask принадлежат одной фирме. Не приравнивать любой near-best bid/ask к маркет-мейкеру.

**OFI:** использовать paper Cont, Kukanov, Stoikov, *The Price Impact of Order Book Events* https://arxiv.org/abs/1011.6402 . Пример OFI на лучшем уровне при переходе `n-1→n`:

```text
e_n = I(bid_p_n >= bid_p_prev)*bid_q_n
    - I(bid_p_n <= bid_p_prev)*bid_q_prev
    - I(ask_p_n <= ask_p_prev)*ask_q_n
    + I(ask_p_n >= ask_p_prev)*ask_q_prev
OFI(window) = sum(e_n)
```

Эта формула — показатель изменения предложения/спроса, **не счётчик роботов**. Применять как объясняющую переменную/контроль рынка; сопоставлять с baseline forecast и отмечать потерянные book updates.

**Reactive:** модель `trigger -> response_lag distribution`, где trigger = изменения bid/ask, расширение spread, print крупнее квантиля, пересечение цены. Проверять на placebo triggers и same-time market confounders; не выводить причинность из корреляции.

## 6. Кластеризация и ML

Открытый проект [ClusterLOB](https://github.com/YichiZhang-Oxford/ClusterLOB), статья [arXiv:2504.20349](https://arxiv.org/abs/2504.20349): K-means++ над признаками индивидуальных MBO order events, кластеры, интерпретируемые как directional/opportunistic/market-making. **Оригинал требует MBO и не является готовым решением на обезличенном L2 T-Invest.**

Наш эксперимент: `feature store` только по реально доступным prints/L2 (relative spread, OFI, imbalance, quote refill, trade intensity, phase concentration, time-since-last-event). Сначала линейная/правиловая baseline, затем K-means/HDBSCAN/GMM и light supervised models **только** на синтетически или независимым образом размеченной проверочной выборке. Визуально и количественно оценить стабильность кластеров между инструментами, датами, рынками. Кластер ≠ независимый участник.

Запрещены утечки по времени: per-instrument scaler fit only on train; selection и label tuning только на development; blind test не трогать. Публиковать feature ablations, calibration, CI и breakdown.

## 7. Исследование metaorders

Источники:
- Lillo, Mike, Farmer (2005), *Theory for Long Memory in Supply and Demand*: https://doi.org/10.1103/PhysRevE.71.066122 — дробление больших поручений и корреляция направлений.
- Goliath & Gebbie, *Metaorder modelling and identification from public data*, arXiv:2602.19590v2: https://arxiv.org/abs/2602.19590 — авторы реконструируют синтетические метаордера по анонимным данным; совпадение агрегированных «stylized facts» не доказывает правильность восстановления исходных поручений.

Модель `metaorder_like_segment`: contiguous/coherent signed-order-flow segment с change points (CUSUM/Bayesian offline/online), execution rate, participation rate, market-impact path, confidence interval, start/end posterior. Сравнивать segmentation models на синтетических поручениях с известной truth; затем на исторической реальности — только «совместимо с metaorder». Если underlying side не установлена, signed flow не делать видимым без предупреждения.

Не обещать оставшийся объём родительского ордера: возможен только **условный диапазон** под явно записанными предположениями и с проверкой прогнозной точности.

## 8. Оценка «сколько роботов»

Пусть `H` — подтверждённые гипотезы, а ребро графа соединяет гипотезы с существенным shared evidence/совместимой фазой/объёмом. Выполнить fusion и найти минимальный набор **различимых потоков**, объясняющих уникальные события. Отображать:
- `confirmed_pattern_count`: число выделенных неперекрывающихся потоков;
- `ambiguous_groups_count`: сколько групп с неразличимой атрибуцией;
- `estimated_activity`: доля объёма в достоверно отнесённых событиях (не double-count);
- `physical_bot_count`: **unknown**, если нет привилегированного ground truth.

Число не является нижней математической границей числа физических ботов: один бот может запускать несколько потоков. Не называть его «точным» или «минимально достоверным числом участников».

## 9. Тесты, этапы, критерии завершения

A1: variable TWAP scenarios и null common rhythm; A2: POV/VWAP out-of-sample vs baselines; A3: L2 order book replay; A4: iceberg-like+grid; A5: OFI/MM-like; A6: reactive; A7: clustering ablations; A8: metaorders with segmentation controls; A9: UI/API schema migration; A10: pilot and audit.

Каждая новая категория:
1. machine-readable specification + доказуемые признаки из источника;
2. synthetic known-truth tests и null;
3. coverage gate (достаточны ли качество и частота данных);
4. held-out evaluation, comparison с более простой baseline;
5. предупреждение об идентифицируемости в API/UI;
6. non-regression старых категорий;
7. документ лицензии/доступности данных, реплей и commit SHA.

**Definition of Done:** никакой категории не выдаётся `confirmed` по одним графическим совпадениям; все классы прошли реплей и контроль ложных срабатываний; отсутствие MBO не маскируется, сервис остаётся read-only, интеграция с OsEngine не открывает торговых команд.


## 10. Новые практические алгоритмы из открытого кода (18.11.2026)

Подробности и ссылки на конкретные файлы в [обзоре](RESEARCH_EXPANSION_2026-11-18.md).

### A. L2+prints replenishment по Flowdepth

В [`flowdepth/data/src/orderflow/iceberg.rs`](https://github.com/Niketion/flowdepth/blob/develop/data/src/orderflow/iceberg.rs) реализовано отслеживание visible qty, pending aggressor executed qty, refill/cancel, rolling baseline и state machine на каждом уровне цены. Наш **собственный** референс:

```text
expected_after = max(previous_visible - pending_executed, 0)
replenished = max(current_visible - expected_after, 0)
cancelled = max(previous_visible - min(previous_visible, pending_executed) - current_visible, 0)
```

Тест: visible 100, executed 60, visible снова 100 → replenished=60 (если есть непрерывность book и правильный aggressor sign). Это **не доказательство** скрытого заказа. Потеря глубины между двумя снапшотами или плохое соответствие сделок уровню → `INSUFFICIENT_L2_CONTINUITY`, а не уверенный iceberg.

Параметры **оригинального** Flowdepth: `min_refills=3`, `ratio_executed/displayed=2.5`, `refill_ratio>=0.5`, `score>=70`, `reorder_ms=150`, `idle=5s`. Эти значения — **не наши дефолты** и не калиброванная вероятность; на MOEX/СПБ должны проверяться отдельно.

### B. Synthetic ML benchmarking

[apexfund/iceberg-detection](https://github.com/apexfund/iceberg-detection) моделирует iceberg with labeled truth и сравнивает L2-CNN с richer events CNN; автор приводит ROC-AUC 0.8285 vs 0.890 **только на собственном симуляторе**. Наши модели должны проходить L2-sampling degradation и сравнение с правиловой replenishment baseline на одной выборке. Не публиковать чужой AUC как ожидаемый результат T-Invest.

### C. Сегментация metaorders и смены режима

Использовать как исходные подходы: [FlowForge](https://github.com/jialuechen/flowforge) и [BOCPD paper](https://arxiv.org/abs/2307.02375), [bocpd Rust](https://github.com/OctopusTakopi/bocpd). Pipeline: `signed trade run` → `CUSUM/BOCPD segmentation` → `holding/impact/participation tests` → `synthetic known truth` → `held-out prediction`. FlowForge random trader mapping годится для **null**, не для восстановления идентичности клиента.

### D. Вывод и данные о направлении

[Lee–Ready (1991)](https://doi.org/10.1111/j.1540-6261.1991.tb02683.x) — альтернативное определение направления агрессора при отсутствующей метке. Из-за рассинхронизации quotes/trades и inside-spread сделок хранить `direction_source=provider|quote_test|tick_test|unknown`, `direction_quality`, `inference_lag`. Не обучать классификатор истинности робота на предположительной пассивной стороне.

**Acceptance supplement:** минимум три L2 scenarios (true simulated iceberg, independent refills, missed updates); путаница между ними снижает уверенность вместо ложного «true positive». Metaorder/change-point test должен продемонстрировать увеличение прогнозной точности сверх простого детектора или оставаться экспериментальным и выключенным по умолчанию.

## 11. Новая категория: QuoteOscillationDetector (по Bogoev–Karam 2017)

В [статье](https://www.sciencedirect.com/science/article/pii/S0378437117304673) исследуются oscillation best bid/ask без обязательного наличия совершённых сделок. [Подробные формулы, прямые ссылки и граничные условия](RESEARCH_EXPANSION_2026-11-18_PART2.md).

**Реализация:** `CarryAsk = sum(abs(delta_ask))`, `BigAsk = abs(ask_last-ask_first)` и аналогично Bid; `OscAsk = CarryAsk/max(BigAsk,price_step)`, `OscBid = CarryBid/max(BigBid,price_step)` — **наша нормализация**, не буквально все zero-denominator правила исходной статьи. Раздельные scoring channels `ask_only`, `bid_only`, `both`, реальный tick size, spread, `net_move`, normalized activity baseline. Конфиг окон `1s/2s/10s` только как эксперимент; пороги — stage-2 held-out.

**Тесты:** Q01 no trade + zig-zag ask, Q02 missing snapshots, Q03 устойчивый тренд без возвратов, Q04 два competing quotes, Q05 price-step differs between instruments, Q06 unobserved 20ms oscillations at 100ms sampling. Не маркировать `spoofing` или «манипулирующий робот» на одном QV; не включать count episodes в execution-pattern-count. При недостаточном L2 покрытии категория скрывается с объяснением.

## 12. Без периодичности: повторяющиеся мотивы через Matrix Profile

Библиотека [STUMPY](https://github.com/stumpy-dev/stumpy), [stumpi streaming](https://github.com/stumpy-dev/stumpy/blob/main/stumpy/stumpi.py), [научное описание](https://doi.org/10.21105/joss.01504). Создать **экспериментальный** `BehavioralMotifDetector`, не production dependency Python в C# runtime.

Вход — лаговые normalized `[bid/ask delta ticks, top sizes, count buys/sells, spread]` по *синхронизированным* временным корзинам. По nearest-neighbor subsequence/matrix profile искать шаблоны `quote->trade->refill->quote`. Проверять self-match/exclusion-zone, короткие и длинные шаблоны, common triggers, day/time leakage, downsampling; сравнивать с baseline `autocorrelation`, `frequency` и DTW (если нужен).

Выход `behavioral_motif` с `repeat_count`, `typical_duration`, `similarity_distance`, `coverage`, `null_significance`, но **не** `bot_id` и не однозначный владелец. Публикация в UI возможна только после контроля ложных повторений на ABIDES no-agent / common-trigger scenarios.

## 13. Distinguishable streams vs actual agents

Добавить ABIDES-NG privileged truth-evaluation из [stage 2](STAGE_02_VALIDATION.md) к тестам всех новых L2/POV/VWAP модулей: TWAP underfill меняет размер clip, VWAP U-shaped profile может совпадать с общим рынком, POV подстраивает q под наблюдаемый оборот. Код [TWAP](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/twap_execution_agent.py), [VWAP](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/vwap_execution_agent.py), [POV](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/pov_execution_agent.py).

**Отдельная исследовательская идея (не текущая цель):** оценка параметров Lillo–Mike–Farmer по long-memory trade signs ([Sato–Kanazawa 2023](https://arxiv.org/abs/2301.13505)) только как aggregate market model. Нельзя использовать модельную оценку средних параметров скрытых parent orders как точное число активных физических программ.

**Приёмка:** каждый новый детектор должен доказать дополнительную предсказательную полезность относительно stages 1–3 и false discovery control, либо оставаться выключенным `EXPERIMENTAL`. Вся система продолжает работать при отсутствии L2 и не делает торговых операций.
