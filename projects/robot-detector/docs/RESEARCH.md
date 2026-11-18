# Публичные научные методы и конкретные примеры для Robot Detector

**Дата проверки:** 2026-11-18. Не копировать закрытые алгоритмы коммерческих продуктов. Использовать только общедоступные описания, научные статьи, разрешённый код и собственную реализацию. Разделять **что показывают авторы** и **наш предлагаемый перенос**.

## 1. Периодичность: Muravyev et al. — измеряемый феномен, а не ID робота

**Публикация:** *Does trade clustering reduce trading costs? Evidence from periodicity in algorithmic trading*, Financial Management 51(4), 2022, DOI https://doi.org/10.1111/fima.12405 . Открытый HTML: https://onlinelibrary.wiley.com/doi/full/10.1111/fima.12405 .

**Что исследовано:** абсолютный всплеск сделок/quote updates в первые 100мс каждой секунды; относительный всплеск активности ровно через 1 секунду после предыдущего. Используются NASDAQ trade+quote данные и независимый Nanex sample; авторы оценивают зависимости в 100-мс бакетах с лагами и абсолютными временными индикаторами. В их выборке первая сотая доля секунды (первые 100мс, т.е. 10% секунды) характеризовалась повышенным числом событий по сравнению с соседним бакетом; это не основание переносить численную величину на MOEX.

**Наша реализация:**
- \`count(t)\` по 100-мс бакетам;
- \`absolute_component = mean_count(first_100ms) - mean_count(other_bins)\`;
- \`relative_component = corr(count_t, count_{t+1s})\` после снятия общего time-of-second эффекта;
- прогнозировать фоновую ритмику; индивидуальный \`PatternHypothesis\` только если дополнительные признаки отделяют определённые события и подтверждаются вне выборки.

**Конкретный ложный сигнал:** 100 независимых участников ставят заявки на границе секунд. Сканер, который считает «1-секундный пик» одним ботом, неверен. В stage 2 нужен null с common rounded-second activity.

## 2. Fourier для многомерного потока: Wu, Zhang, Dai

**Публикация:** *Spectral Volume Models: Universal High-Frequency Periodicities in Intraday Trading Activities*, Management Science, опубликована онлайн 14.11.2025; https://doi.org/10.1287/mnsc.2024.06215 ; HTML https://pubsonline.informs.org/doi/10.1287/mnsc.2024.06215 .

**Авторы:** исследуют высокочастотную периодичность внутридневных объёмов через Fourier analysis на данных США/Китая; цель — идентифицировать частотные компоненты активности, не личности участников.

**Наш перенос:** строить импульсный ряд \`x[b] = sum lots in 100ms bin\`, удалять intra-day baseline \`x[b]/E[x|time_of_day]\`, получать периодограмму и пики T. Затем — уточнять фазы для *выбранного подмножества событий*, а не объявлять «N роботов» по N частотным пикам.

\`\`\`text
# Псевдокод: ВНИМАНИЕ, наша адаптация, не цитата из статьи
events = group_by_venue_session_side(trade_tape)
x = sum_quantity_into_bins(events, dt=0.1s)
x_detrended = x - rolling_expected_activity(x)
peaks = dominant_frequencies(fft(x_detrended))
for freq in peaks:
    T = 1/freq
    fit_phase_and_quantity_hypotheses(T, events)
    test_on_future_events()
    compare_to_null_with_same_market_rhythm()
\`\`\`

**Риски:** spectral leakage, алиасинг из-за разрешения timestamps, гармоники \`T/2,2T\`, нулевые бакеты, пики в начале/конце сессии, разные торговые режимы.

## 3. Order splitting и metaorders: Lillo–Mike–Farmer / Goliath–Gebbie

**LMF:** *Theory for Long Memory in Supply and Demand* (2005), https://doi.org/10.1103/PhysRevE.71.066122 . Идея: дробление больших поручений на дочерние сделки способно объяснить долгие корреляции знаков в order flow.

**Современная проверка публичных данных:** Goliath & Gebbie, *Metaorder modelling and identification from public data*, [arXiv:2602.19590v2](https://arxiv.org/abs/2602.19590), переработана 03.09.2026. Авторы используют обезличенные transaction/quote данные JSE и реконструируют синтетические metaorders. Важный результат: подгонка агрегированных статистик сама по себе не означает, что индивидуальные metaorders восстановлены верно.

**Наш перенос:** инструментальные метрики автокорреляции направлений \`C(lag) = E[sign_t * sign_{t+lag}] - E[sign]^2\`, с контрольной реализацией для irregular timestamps; change-point сегментация; условное распределение длины/объёма. Запрет утверждений о реальном parent order ID.

## 4. Айсберги: Zotikov & Antonov

**Публикация:** *CME Iceberg Order Detection and Prediction* (2019), https://arxiv.org/abs/1909.09495 .

Авторы предлагают native/synthetic iceberg detection на CME с использованием **специфичных данных полной глубины и признаков отдельных заявок**, и survival modelling c Kaplan–Meier для объёма. Это не универсальный детектор, работающий на любом L2 feed.

**Наш перенос:** repeated replenishment at price, ограниченное окно после подтверждённой сделки, сравнение с baseline восстановления объёма и цензурированные наблюдения. Пометка \`iceberg_like\`; для \`native iceberg\` в T-Invest L2 требуется независимое доказательство доступности нужной микроинформации.

**Конкретный контрпример:** объём ask 500 лотов; исполнено 300; снова показывается ask 500 на той же цене. Это может быть айсберг, два разных продавца или потерянное обновление агрегированного book. Система не должна утверждать «скрыто 300 лотов».

## 5. OFI: Cont, Kukanov, Stoikov

**Публикация:** *The Price Impact of Order Book Events* (Journal of Financial Econometrics), открытый препринт https://arxiv.org/abs/1011.6402 ; авторская страница https://www.sashastoikov.com/finance/2015/3/12/the-price-impact-of-order-book-events .

Авторы связывают краткосрочные изменения цены с \`order flow imbalance\` на лучшем bid/ask. Это **контрольная переменная и контекст**, а не формула подсчёта программ. Пример вычисления по двум снимкам — см. [STAGE_04_ADVANCED.md](STAGE_04_ADVANCED.md).

## 6. Кластеризация участников: ClusterLOB

**Публикация:** Zhang, Cucuringu, Shestopaloff, Zohren, *ClusterLOB: Enhancing Trading Strategies by Clustering Orders in Limit Order Books*, https://arxiv.org/abs/2504.20349 ; опубликована в Quantitative Finance (2026), DOI https://doi.org/10.1080/14697688.2026.2665153 .

**Открытый код:** https://github.com/YichiZhang-Oxford/ClusterLOB .

**Метод:** признаки для индивидуальных market-by-order событий (MBO), K-means++ и три интерпретируемых кластера (directional/opportunistic/market-making); оценки order flow imbalance внутри каждого кластера.

**Ограничение:** в агрегированном стакане T-Invest нет наблюдений каждого MBO add/cancel/modify и ID отдельных заявок. Переносить можно принцип event-level feature engineering и оценку кластеров, **нельзя заявлять репликацию результатов статьи**.

## 7. Инженерные примеры коммерческих детекторов (не доказательство качества)

**Trading Tools**, страница возможностей: https://tradingtools.ru/features ; сканер роботов MOEX, объём, период, продолжительность, прогноз следующих исполнений — ориентир UI, не раскрытие исходного кода.

**AutoTrade Pro**, описание детектора: https://autotrade-pro.ru/docs/виджет-детектора-настройки-и-принцип/ ; использовать только общедоступные принципы и проверять настройки на реальном архиве.

**HookScreener**, статья от 07.09.2026: https://www.hookscreener.com/ru/blog/kak-naiti-robotov-v-stakane/ . Авторы выделяют метроном, лестницу, плавающий кусок, всплеск; декларируют условия обнаружения: около \`max(200ms, 2% интервала)\`, минимум 6 исполнений и окно 300 секунд. Это **параметры конкретного продукта**, а не подтверждённая универсальная статистическая граница. Для MOEX/СПБ настраивать через [STAGE_02_VALIDATION.md](STAGE_02_VALIDATION.md).

**Вывод:** оба типа научных данных полезны: (а) факт общей ритмичности рынка, (б) методы выделения специфичного последовательного потока. Переход от (а) к (б) требует собственной валидации.

## 8. Открытые программные основы

- [ClusterLOB](https://github.com/YichiZhang-Oxford/ClusterLOB) — MBO clustering, изучить признаки/репликацию; зафиксировать лицензию перед использованием кода.
- [Order Flow Tracker](https://github.com/zadescoxp/order-flow-screener) — инженерные идеи order-flow ingestion/replay/icebergs, самостоятельная проверка кода, текущей лицензии и тестов обязательна.
- [Order-Flow](https://github.com/BEINOMUGISHA/Order-Flow) — структура проекта, глубина стакана/визуализации, проверить актуальность.
- [Orderflow Engine](https://github.com/gregorian-09/orderflow) — практические признаки и архитектура orderflow, не считать исходный код доказательством качества.

Ни один проект не принят автоматически как production dependency; сначала code audit, license/SBOM, benchmark и проверка фактических входных данных.

## 9. Прямые ссылки на первичную документацию T-Invest

- [История обезличенных сделок](https://developer.tbank.ru/invest/services/history-md/head-history-md). Архив следует инспектировать по полям \`TRADE_TS,TICKER_CC,DIRECTION,PRICE,QUANTITY,TRADE_SOURCE,INSTRUMENT_UID\`; не путать с candles/history-data.
- [MarketDataStream API](https://developer.tbank.ru/invest/api/market-data-stream-service-market-data-stream).
- [MarketData schema](https://developer.tbank.ru/invest/services/quotes/marketdata).
- [Ограничения](https://developer.tbank.ru/invest/intro/intro/limits).
- [Сервис последних сделок](https://developer.tbank.ru/invest/api/market-data-service-get-last-trades), пригоден для восстановления ограниченного окна только после проверки API semantics.

## 10. Воспроизводимый расчёт без внешних библиотек (псевдо-C#)

**Synthetic tape:** \`(0.000, 100),(5.015,100),(10.010,100),(12.300,40),(20.020,100),(25.005,100),(30.012,100)\`.

\`\`\`csharp
// Учебный пример. Совместимость со схемой production проверяется отдельно.
var times = new[] { 0.000, 5.015, 10.010, 12.300, 20.020, 25.005, 30.012 };
var volumes = new[] { 100L, 100L, 100L, 40L, 100L, 100L, 100L };
double period = 5.0;
double tolerance = 0.1;
long targetLots = 100;
int matches = 0;
long matchedVolume = 0;
for (int i = 0; i < times.Length; i++)
{
    var nearestCycle = Math.Round(times[i] / period);
    var phaseError = Math.Abs(times[i] - nearestCycle * period);
    if (volumes[i] == targetLots && phaseError <= tolerance)
    {
        matches++;
        matchedVolume += volumes[i];
    }
}
// matches = 6, matchedVolume = 600; пропущенный цикл t=15s
\`\`\`

**Ограничение кода:** здесь \`T=5\`, \`q=100\`, \`phase=0\` заданы заранее; это только **проверка гипотезы**, не алгоритм её обнаружения. Production система должна искать кандидаты сама, учитывать разные фазы/источники, test-set и множественные проверки.

## 11. Как читать результаты исследований

- «В статье найдено увеличение числа событий около целой секунды» ≠ «можем посчитать идентичные программы на T-Invest».
- «Обнаружен айсберг на CME с MBO» ≠ «можно доказать iceberg по агрегированному стакану MOEX».
- «Кластеризованы MBO order events» ≠ «кластеры = независимые реальные владельцы».
- «Найдена статистически значимая периодичность» ≠ «можно предсказать сделку с такой же вероятностью».
- Результаты других рынков/лет могут не переноситься на СПБ, особенно при дилерском источнике и pro-rata / других правилах исполнения.

## 12. Очередность применения

**Сразу:** Muravyev (обязательный null), HookScreener (эвристика как candidate), fixed TWAP + прогноз на holdout.

**После стабильной базы:** Fourier model (candidates), LMF/metaorders (знаки/сегментация) и empirical validation.

**Только после доступности L2/проверки покрытия:** OFI, iceberg-like, grid, MM-like.

**Только при доступе к MBO:** прямой воспроизводимый порт ClusterLOB и CME-specific native iceberg features; иначе адаптация с честной маркировкой и совершенно новой валидацией.
