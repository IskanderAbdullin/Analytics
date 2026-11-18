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

Каждый детектор имеет \`evidence_kind\`, \`attribution_level\`, \`limitations\`, \`min_data_quality\`, \`config_version\`, \`null_model\`; confidence только после валидации своей модели.

## 2. Variable-size TWAP

Найти равномерный временной ритм **без фильтра по одинаковому q**. Сначала определять \`T,phase\` по weighted impulses событий и фазовой концентрации; далее проверять, что условная последовательность объёмов статистически отличается от случайных принтов на такой же фазе и частоте. Модели размеров: \`q_i = q0 + noise\`, \`q_i ~ categorical({q_a,q_b,...})\`, \`q_i ~ lognormal truncated\`. Отдельно учитывать дробление одной сделки на исполнения, чтобы не превращать пачку принтов в «много циклов».

Контроль: вероятный общий метроном рынка от Muravyev et al. (2022) и Spectral Volume Models (2025) должен объясняться **market-wide component**; индивидуальный алгоритм регистрируется только с выделяемым и подтверждённым подмножеством событий и превышением условного null.

## 3. POV/VWAP-кандидаты

**POV-признак:** в фиксированных или скользящих окнах \`V_candidate(w) ≈ beta * V_market(w)\`. Требования: оценить \`beta\` только на прошлом, проверить стабильность и отдельную прогнозную точность на новых окнах; baseline \`beta=const\` сравнить с независимым trend/seasonality estimator. На окнах с low volume — интервалы неопределённости/отказ.

**VWAP-like:** сравнить \`candidate volume intensity\` с заранее рассчитанным историческим U-shaped профилем рынка с point-in-time ограничением. Распознаватель не видит цель алгоритма, поэтому выдаёт «совместимо с распределением по профилю», а не точный тип реализации VWAP.

**Режим:** не смешивать собственное исполнение алгоритма с фоновым \`V_market\` без leave-one-out корректировки — иначе механическая корреляция. Результаты без устойчивого out-of-sample преимущества над простыми baseline не включать в online.

## 4. Айсбергоподобное поведение по L2

Источники: T-Invest агрегированный OrderBook Stream, синхронизированный с prints. Контроль точности времени и редкой дискретизации стакана; у T-Invest действует отдельное ограничение обновлений book (сверить документацию на дату внедрения).

Кандидат \`replenishment\`, если (a) у уровня \`p\` наблюдался resting volume \`Q_before\`; (b) подтверждены сделки на этом уровне; (c) вскоре появляется/сохраняется объём \`Q_after\` на том же \`p\`; (d) эпизод повторяется с более высокой частотой, чем обычное обновление стакана в сходных условиях. На L2 это **видимое повторное пополнение**, а не доказанное native iceberg.

Литература: Zotikov & Antonov, *CME Iceberg Order Detection and Prediction* (2019) https://arxiv.org/abs/1909.09495 . Авторы различают native и synthetic icebergs, используют сведения о trade-summary и изменениях конкретных ордеров и модель Kaplan–Meier для цензурированных объёмов. Наш план: перенести **структуру проверки гипотезы + survival/censoring**, **не переносить** CME-specific признаки order ID/MBO на T-Invest L2.

Модель: \`replenishment_event\`, \`price_level\`, \`post_trade_refill_time\`, \`observed_executed_lots\`, \`visible_lots_before/after\`, \`book_sampling_gap\`; результат \`iceberg_like\` c \`not_identifiable_as_native\`. Объём скрытой части не выдавать точным; по умолчанию null, при калибровке диапазон.

## 5. Сетка/маркет-мейкер/реактивное поведение

**Grid-like:** обнаруживать несколько параллельных уровней \`p0 + k * step\` с повторной синхронной коррекцией объёмов; признаки: расстояния в тиках, длительность поддержки, повторяемость появлений и исчезновений после сделки, относительная симметрия. Контрпример — статический стакан с независимыми заявками на круглых ценах.

**MM-like:** score по симметрии / асимметрии bid-ask, стабильности spread, реакции на midprice, частоте обновлений. Не утверждать, что bid и ask принадлежат одной фирме. Не приравнивать любой near-best bid/ask к маркет-мейкеру.

**OFI:** использовать paper Cont, Kukanov, Stoikov, *The Price Impact of Order Book Events* https://arxiv.org/abs/1011.6402 . Пример OFI на лучшем уровне при переходе \`n-1→n\`:

\`\`\`text
e_n = I(bid_p_n >= bid_p_prev)*bid_q_n
    - I(bid_p_n <= bid_p_prev)*bid_q_prev
    - I(ask_p_n <= ask_p_prev)*ask_q_n
    + I(ask_p_n >= ask_p_prev)*ask_q_prev
OFI(window) = sum(e_n)
\`\`\`

Эта формула — показатель изменения предложения/спроса, **не счётчик роботов**. Применять как объясняющую переменную/контроль рынка; сопоставлять с baseline forecast и отмечать потерянные book updates.

**Reactive:** модель \`trigger -> response_lag distribution\`, где trigger = изменения bid/ask, расширение spread, print крупнее квантиля, пересечение цены. Проверять на placebo triggers и same-time market confounders; не выводить причинность из корреляции.

## 6. Кластеризация и ML

Открытый проект [ClusterLOB](https://github.com/YichiZhang-Oxford/ClusterLOB), статья [arXiv:2504.20349](https://arxiv.org/abs/2504.20349): K-means++ над признаками индивидуальных MBO order events, кластеры, интерпретируемые как directional/opportunistic/market-making. **Оригинал требует MBO и не является готовым решением на обезличенном L2 T-Invest.**

Наш эксперимент: \`feature store\` только по реально доступным prints/L2 (relative spread, OFI, imbalance, quote refill, trade intensity, phase concentration, time-since-last-event). Сначала линейная/правиловая baseline, затем K-means/HDBSCAN/GMM и light supervised models **только** на синтетически или независимым образом размеченной проверочной выборке. Визуально и количественно оценить стабильность кластеров между инструментами, датами, рынками. Кластер ≠ независимый участник.

Запрещены утечки по времени: per-instrument scaler fit only on train; selection и label tuning только на development; blind test не трогать. Публиковать feature ablations, calibration, CI и breakdown.

## 7. Исследование metaorders

Источники:
- Lillo, Mike, Farmer (2005), *Theory for Long Memory in Supply and Demand*: https://doi.org/10.1103/PhysRevE.71.066122 — дробление больших поручений и корреляция направлений.
- Goliath & Gebbie, *Metaorder modelling and identification from public data*, arXiv:2602.19590v2: https://arxiv.org/abs/2602.19590 — авторы реконструируют синтетические метаордера по анонимным данным; совпадение агрегированных «stylized facts» не доказывает правильность восстановления исходных поручений.

Модель \`metaorder_like_segment\`: contiguous/coherent signed-order-flow segment с change points (CUSUM/Bayesian offline/online), execution rate, participation rate, market-impact path, confidence interval, start/end posterior. Сравнивать segmentation models на синтетических поручениях с известной truth; затем на исторической реальности — только «совместимо с metaorder». Если underlying side не установлена, signed flow не делать видимым без предупреждения.

Не обещать оставшийся объём родительского ордера: возможен только **условный диапазон** под явно записанными предположениями и с проверкой прогнозной точности.

## 8. Оценка «сколько роботов»

Пусть \`H\` — подтверждённые гипотезы, а ребро графа соединяет гипотезы с существенным shared evidence/совместимой фазой/объёмом. Выполнить fusion и найти минимальный набор **различимых потоков**, объясняющих уникальные события. Отображать:
- \`confirmed_pattern_count\`: число выделенных неперекрывающихся потоков;
- \`ambiguous_groups_count\`: сколько групп с неразличимой атрибуцией;
- \`estimated_activity\`: доля объёма в достоверно отнесённых событиях (не double-count);
- \`physical_bot_count\`: **unknown**, если нет привилегированного ground truth.

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

**Definition of Done:** никакой категории не выдаётся \`confirmed\` по одним графическим совпадениям; все классы прошли реплей и контроль ложных срабатываний; отсутствие MBO не маскируется, сервис остаётся read-only, интеграция с OsEngine не открывает торговых команд.
