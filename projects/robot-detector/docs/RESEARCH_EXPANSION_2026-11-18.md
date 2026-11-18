# Дополнительное исследование open-source и научных методов (18.11.2026)

**Контекст:** независимый проект `projects/robot-detector` в Analytics. Этот обзор расширяет [RESEARCH.md](RESEARCH.md). Источники проверены по доступным GitHub README, исходным файлам или статьям. Реального запуска стороннего кода и сравнительных backtest на MOEX/СПБ **ещё не проводилось**. Ссылки на конкретные версии/файлы предпочтительнее общих обещаний README; показатели сторонних авторов не подтверждены нами.

## A. Приоритетные находки с открытым КОДОМ

| Приоритет | Проект и конкретный путь | Выявленный способ | Как использовать и что не переносить автоматически |
|---|---|---|---|
| P0 | [Crypto Lake TWAP Notebook](https://github.com/crypto-lake/analysis-sharing/blob/main/twap_detection.ipynb) | Частотный поиск исполнения TWAP и окно около границы целых секунд, пример FTRB-USDT/AscendEX | Репликация как базовый `minute-boundary filter`, затем критический аудит спектрального метода; sample данные через внешний lakeapi требуют проверки доступности |
| P0 | [binance_l3_est/src/engine/twap.rs](https://github.com/OctopusTakopi/binance_l3_est/blob/main/src/engine/twap.rs) | Реальный Rust код: count/volume bins, linear detrend, Hann, FFT, PSD, sigma peak threshold для taker buy/sell | Прямой шаблон для самостоятельной .NET FFT baseline, **не** достоверный классификатор числа роботов |
| P1 | [binance_l3_est TWAP UI](https://github.com/OctopusTakopi/binance_l3_est/blob/main/src/ui/windows/twap_view.rs) | Пики частот/спектральная мощность и buy/sell panel | Аналог информационных панелей stage 3; название «Market Participant Clustering» в README не гарантирует идентификацию участников |
| P1 | [flowdepth docs](https://github.com/Niketion/flowdepth/blob/develop/docs/binance-iceberg-detector.md) и [исходник iceberg.rs](https://github.com/Niketion/flowdepth/blob/develop/data/src/orderflow/iceberg.rs) | L2+trade replenishment, контролируемые потери, объяснимый score | Сценарий этапа 4 с квалификацией «possible iceberg», без ложной certainty |
| P1 | [crypto-lake/analysis-sharing](https://github.com/crypto-lake/analysis-sharing) | Notebook реальной tick tape, графики share/price impact | Контрольная реализация и visual explainability, MIT по GitHub README |
| P1 | [flowforge](https://github.com/jialuechen/flowforge) | Синтетическое order splitting/метаордеры + вероятностное реконструирование через случайную карту «трейдеров» | Генератор известной truth и null-модель, **не** доказательство реального owner ID; BSD-2-Clause |
| P1 | [sohaibelkarmi/High-Frequency-Trading-Simulator](https://github.com/sohaibelkarmi/High-Frequency-Trading-Simulator) | Детерминированный LOB и Hawkes-генератор кластерных потоков | Отдельный non-Poisson контрпример/воспроизводимая симуляция этапа 2 |
| P1 | [hawkes-order-flow](https://github.com/MaherHarp/hawkes-order-flow) | Многомерный Hawkes, `lambda_i(t)`, fit и time-rescaling goodness-of-fit | Контрольная clustered null, проверка против ложного TWAP; MIT, молодой проект — оценить код/качество независимо |
| P2 | [OctopusTakopi/bocpd](https://github.com/OctopusTakopi/bocpd) | Rust BOCPD, bounded-memory log-space update, Gaussian/Poisson/Bernoulli/score-driven и Hawkes варианты | Экспериментальный online change point для старта/остановки, MIT; не использовать как готовую .NET зависимость |
| P2 | [mansoor-mamnoon/limit-order-book](https://github.com/mansoor-mamnoon/limit-order-book) и [TWAP YAML](https://github.com/mansoor-mamnoon/limit-order-book/blob/main/docs/strategy/twap.yaml) | Генератор TWAP/VWAP/POV-like child fills, snapshot/replay equivalence | Разнообразить инъекции синтетических исполнений и тестировать split-fills, restart parity; проект прежде всего исполнения, не детектор |
| P2 | [apexfund/iceberg-detection](https://github.com/apexfund/iceberg-detection) | Симулятор скрытых заявок + сравнение CNN L2 vs L2+events | Образец ablation, но результаты **только synthetic** и частота L2 выше T-Invest; лицензия повторно проверить |
| P2 | [MotiveWave MBO tracker](https://github.com/matejddc/motivewave-mbo-iceberg-tracker) | MBO/refill markers, MIT | Сравнение UI/сигналов, зависит от SDK и order-level feed; не самостоятельный источник для T-Invest |

### A1. Конкретный исходник TWAP на Rust: что там действительно написано

Открыт и прочитан [`src/engine/twap.rs`](https://github.com/OctopusTakopi/binance_l3_est/blob/main/src/engine/twap.rs), фактический blob SHA при проверке `e257684219e8ad07060ff343a06c0f4cfaaff1e1`.

- `bin_ms = 500` (один bin — 0.5 s), `window_bins = 512` (окно 256 s), `threshold_sigma = 3.0`.
- Отдельные `bins_buy`, `bins_sell` считают **число prints**, `vol_bins_buy`, `vol_bins_sell` считают **notional** (`quantity * price`), не типичное количество лотов ребёнка.
- Биржевое поле `is_buyer_maker` используется для определения *taker* направления; семантика специфична для Binance, не переносить непосредственно на T-Invest.
- FFT вычисляется при каждом 32-м закрытом bin (или после 64 bins при первом запуске).
- `run_fft_pipeline`: **линейный detrend → Hann window → FFT → one-sided PSD → threshold = mean(PSD) + 3 * std(PSD)** → взять top 5 peak frequencies. Частота `f_k = k / (N*bin_ms/1000)`; период `T=1/f_k`.
- При скачке timestamp код вставляет пустые bins, ограниченные размером окна. Это полезно для непрерывной временной оси, но **большие gap и разрывы сессии должны иметь отдельный coverage status**, а не трактоваться нормальным отсутствием сделок.
- Модуль не восстанавливает уникальные реальные parent orders или owner IDs, а частотные пики могут отражать общий рыночный ритм/гармоники.

**Наша версия:** `ClockTimeBinSeries` с 100/250/500/1000мс в конфиге; обязательное нулевое заполнение на непрерывных здоровых интервалах; `FftCandidateGenerator` выдаёт `period_candidates`, затем `FixedQuantityPhaseMatcher` и holdout/null. Нельзя подтверждать N ботов по N спектральным пикам. Сравнить спектр count vs quantity vs notional (объёмы в разных единицах); общий peak не равен отдельному потоку.

**Два обязательных теста**: при `dt=0.5s` период 0.4s выше частоты Найквиста и недопустим для FFT; для T=60s и 256s окна всего ~4.27 периода, поэтому требуется значительно более длинное наблюдение, а не преждевременное подтверждение. Спектральный threshold 3 sigma не является статистически откалиброванной вероятностью.

### A2. Crypto Lake notebook: реальные строки и воспроизводимая адаптация

Источник [`twap_detection.ipynb`](https://github.com/crypto-lake/analysis-sharing/blob/main/twap_detection.ipynb), проверенный blob `888293594f9cf695fd189d7fae2a819e6908f249`. Прямое содержание code cells:

- `lakeapi.use_sample_data(anonymous_access=True)`; `lakeapi.load_data(table='trades', symbols=['FTRB-USDT'], exchanges=['ASCENDEX'], start='2022-09-01', end='2022-12-15')`; указан **free sample, а не гарантированная полная лента**.
- Готовые признаки `signed_quantity = quantity * side_sign`, `price_ewm = price.ewm(halflife=5).mean()`, `aggressivity = (price-price_ewm)/price_ewm`, `aggr_quantity=quantity*aggressivity`. Последнее — *авторская прокси силы тренда*, **не сторона агрессора**.
- Авторский periodogram: `signal.periodogram(trades.quantity, fs=1e6, nfft=1000)`. **Методологический риск:** `trades.quantity` индексирован по номеру сделки, а не по равномерным моментам времени. Указанный `fs=1e6` не исправляет нерегулярную шкалу. Данный код нельзя брать как надёжное измерение периодов в секундах без дополнительной независимой проверки.
- Фильтр около ровной секунды `(microsecond < 80000) OR (microsecond > 950000)` — простая эвристика, фактически окно \[-50мс,+80мс\] относительно границы. Для 60-секундного TWAP одного такого фильтра **недостаточно**: он захватывает события каждой секунды. Нужно отдельное сравнение минутных фаз, боковых потоков и null.
- В notebook авторы визуально отмечают вероятные sell-twap периоды 7–11 ноября и другие интервалы 2022, но это исследовательская визуальная интерпретация без размеченного ground truth.

**Наш фикс:** производить `x[b] = sum prints (or lots) with clock_time in bin b`, `fs = 1 / bin_duration_sec`, тогда `periodogram(x, fs=...) ` физически интерпретируем. Альтернатива для неравномерных событий — метод Lomb–Scargle / point-process periodogram с корректной нулевой моделью. Для minute-boundary эвристики считать `phase_mod_60s` и сравнивать выбросы с `phase_mod_1s`.

**Конкретный контроль:** если имеется 100 случайных prints с метками `HH:MM:05.010` в разные секунды, фильтр «в начале секунды» обнаружит многие события, но только строгая проверка `time mod 60s` покажет, относятся ли они к одной минутной фазе.

### A3. Flowdepth: конкретный L2 bookkeeping и условия обнаружения

Реальные [описание](https://github.com/Niketion/flowdepth/blob/develop/docs/binance-iceberg-detector.md) и [Rust файл](https://github.com/Niketion/flowdepth/blob/develop/data/src/orderflow/iceberg.rs), blob `5704f4edd66e3823633ff0eb62d0dcb9daf8f89b`.

Для текущего видимого объёма `Q_before`, подтверждённого объёма агрессивных исполнений на уровне `E`, нового видимого объёма `Q_after`:

```text
expected_after = max(Q_before - E, 0)
replenished = max(Q_after - expected_after, 0)
cancelled = max(Q_before - min(Q_before, E) - Q_after, 0)
```

**Пример (синтетика):** видимое bid = 100, агрессивно продали 60 по bid, новый bid = 100. Без пополнения ожидали 40; `replenished=60`. Это **не доказательство** одной скрытой заявки: 60 могли добавить разные трейдеры. Если `E` не сопоставлено со стороной/ценой, результат unknown.

Значения в оригинальной реализации: `minimum_refill_count=3`, `minimum_executed_to_displayed=2.5`, `minimum_refill_ratio=.5`, `minimum_score=70`, `reorder_window_ms=150`, `episode_idle_timeout_ms=5000`, `episode_max_duration_ms=30000`, `max_distance_from_touch_ticks=2`; baseline по rolling 60sec и минимум 12 trades/touch observations. **Это чужие эвристические параметры**, не нормативные пороги и тем более не калиброванные вероятности. Из-за ограниченной частоты обновления агрегированного book T-Invest меньшая точность может делать отдельные episodes вообще неидентифицируемыми.

Внести в наш stage-4 detector: `book_continuity_status`, `pending_executed_at_level`, `replenished_qty`, `cancelled_qty`, `peak_visible`, `refill_count`, `data_quality`, `confidence_calibrated=null` пока нет валидации. На каждом resync/gap инвалидировать открытые episode hypotheses.

## B. Дополнительные научные статьи, не повторяющие основной список

| Статья, прямая ссылка | О чём | Практическое добавление в ТЗ |
|---|---|---|
| [Tsaknaki, Lillo, Mazzarisi (2025), Online Learning ... BOCPD](https://doi.org/10.1080/14697688.2024.2337300), [открытый препринт](https://arxiv.org/abs/2307.02375) | Bayesian online change-point для смен режима order flow и прогнозирования impact | `RegimeChangeDetector`: начало/конец потока по posterior change-point vs CUSUM/EWMA baseline; stage 3/4 |
| [Chen, Chan, Chang (2022), Periodicity of trading activity in foreign exchange markets](https://doi.org/10.1111/jfir.12280) | Пики активности **в начале минуты** на 25 валютных парах | stage 2 дополнительный null `minute-boundary synchronization`, отделять от отдельного minute TWAP |
| [Tóth et al., Why is equity order flow so persistent? (2015)](https://arxiv.org/abs/1108.1632) | Разделение механизма order splitting и herding при наличии идентификаторов членов биржи | Не утверждать «один крупный игрок» только по автокорреляции знаков; explicit unidentifiability |
| [Lee & Ready (1991), Inferring Trade Direction from Intraday Data](https://doi.org/10.1111/j.1540-6261.1991.tb02683.x) | Quote/trade classification, коррекция временных несовпадений, сделки внутри спреда | Разделить authoritative provider side и inferred Lee-Ready/tick-rule side с оценкой ошибки; никакой безусловной стороны пассивного order |
| [Martínez-Miranda et al. (2019), Order flow dynamics ... cancellation](https://doi.org/10.1002/hf2.10026) | SVM на динамике полного LOB для прогноза отмен крупных orders | На L2 допустима отдельная `cancellation-like` эвристика; «spoofing/manipulation» без MBO и правового контекста **не маркировать** |
| [Poutré, Chételat, Morales (2024), Deep unsupervised anomaly detection in high-frequency markets](https://doi.org/10.1016/j.jfds.2024.100129) | Transformer representation и synthetic injected anomalies в NASDAQ LOB | Stage 4 как *optional* ML benchmark после baseline; не путать аномалии и независимые роботы |
| [Lajbcygier et al., Who can see the iceberg's peak? (2024 online)](https://doi.org/10.1111/jfir.12414) | Iceberg study с **явно помеченными iceberg orders**; repeated replenishments | Учесть принцип: надёжный ground truth требует venue tagged data; на L2 разрешён только iceberg-like |
| [El Karmi (2025), A Deterministic LOB Simulator with Hawkes-Driven Order Flow](https://arxiv.org/abs/2510.08085) | Полный воспроизводимый Hawkes/LOB симулятор | Сопоставить ложные TWAP детекции при clustered null и pure Poisson |

Статья BOCPD опубликована в Quantitative Finance (2025), arXiv версия датирована 2023. Даты указывать по версии, не путать.

## C. Что конкретно добавляем в ПО

### Stage 1 — два независимых baseline алгоритма

1. `B1_FixedQuantityPhase`: q/T/phase на matched print IDs с запретом double-count.
2. `B2_FFTCandidates`: clock-time counts и lots в bins, PSD peaks как **кандидаты**; обязательный subsequent phase+volume matcher, no owner inference.
3. `B0_MinuteBoundary`: примитивное правило по `time mod 60s`, отдельно контроль целой секунды, как воспроизводимая нижняя планка из Crypto Lake. Не использовать без holdout как «робот».

Отчёт `detector_family`, `evidence_events`, `period_search_range`, `fft_bin_ms`, `window_s`, `nyquist_ok`, `cycles_observed`, `null_model`. Ни один канал не может порождать число владельцев.

### Stage 2 — изолированные сравнения и негативные контрпримеры

- `P1`: один трейд/секунду много разных агрессоров, нет выделяемого объёма → общий peak, 0 подтверждённых физических источников.
- `P2`: два потока `T=5s`, `T=8s` и шум → два различимых регулярных паттерна, если хватает SNR; контроль гармоник.
- `P3`: 100 событий около `...:SS.010` при каждом целом `SS`, но нет повторяемой minute phase → `B0` не должен подтверждать minute TWAP.
- `P4`: timestamp разрешение 1s и период 250ms → неидентифицируем, а не ложная точность.
- `P5`: FFT `bin_ms=500`, T=400ms → aliasing; `nyquist_ok=false`.
- `P6`: частота T=60s при окне 256s → `insufficient_cycles` по строгому gate; не выдавать confidence.
- `P7`: Hawkes clustered background с аналогичным темпом и объёмами против Poisson → сравнить false discovery per instrument-hour.
- `P8`: одна и та же последовательность prints, но различное фактическое число независимых генераторов → оценка count одинакова (идентифицируемости нет).
- `P9`: повторные исполнения и пересортировка timestamp; same-time events не схлопывать без trade ID.
- `P10`: в live stream 100 мс book snapshot пропускает refill между двумя снимками → no `iceberg confirmed`.

Каждая гипотеза проверяется на будущем. Анализ false alarms по market-wide common clock и 1-minute macro clock обязателен.

### Stage 3 — устойчивость онлайн

Добавить `RegimeChangeDetector` экспериментальной ветки: BOCPD vs EWMA/CUSUM, только на `healthy` feed; на reconnect posterior не трактовать как смену режима торгового алгоритма. Для UI отдельно показывать «рынок вошёл в новый режим активности» и «обнаружен выделяемый паттерн». Вариант BOCPD строго read-only.

### Stage 4 — L2/refill и сегменты крупного потока

Применить flowdepth-style `expected_after/replenished/cancelled`, но только с измеренной непрерывностью book. A/B сравнение `L2-only heuristic` vs `L2+prints` vs `L2+prints+ML`; ablation и calibration, чтобы не копировать результаты CNN из синтетики как точность MOEX.

Для metaorder segmentation сравнить CUSUM, BOCPD, Hawkes-adjusted baseline и FlowForge randomized-trader null на known-truth synthetic, с запретом считать reconstructed traders реальными.

## D. Решения по приоритету

**Немедленно реализовывать (этап 1):** два baseline + исправленная временная спектральная шкала + minute phase negative controls. Сырые данные для графиков не импортировать из сторонних проектов без лицензии.

**Этап 2:** Hawkes/null + timezone/clock periodicities + hard gate на Nyquist, количество периодов и семантику направления.

**Этап 3:** BOCPD только как сравнительный кандидат для определения переключения режима; без утверждений о трейдере.

**Этап 4:** flowdepth bookkeeping, synthetic CNN ablation, metaorder reconstruction с непроверяемым owner count.

## E. Code/license audit checklist до заимствования

- Записать SHA файла, лицензию и распространяемые third-party assets; MIT/BSD permissions не заменяют проверки зависимостей/использования данных.
- Воспроизвести алгоритм минимальным independent C# тестом, без вставки неуточнённых копий.
- Проверить, не требуют ли проекты Binance-specific fields `is_buyer_maker`, `trade_id`, `sequence_id`, глубокий L3 feed.
- Отдельно считать цены и объёмы: `lots` vs `shares`, `notional` vs `quantity`, buy-maker vs taker-buy.
- Оценить качество кода/историю проекта (возраст, тесты, issue activity); внешние заявленные benchmarks не считать фактом нашей реализации.
- Результаты строго атрибутировать как `third_party_reported` до собственного повторения.

**Статус:** исследование и включение в ТЗ, ни одна новая реализация не объявлена готовой или протестированной на MOEX/СПБ.
