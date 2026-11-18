# Этап 1 — исторический детектор регулярных сделок (детальное ТЗ)

**Цель:** из архивов сделок выявлять и объяснять устойчивые периодические потоки с приблизительно фиксированным количеством лотов. **Не** оценивать владельцев; не использовать торговые API.

## A. Требования к данным

1. Сделать `TInvestHistoryTradeSource` с официальным архивом https://developer.tbank.ru/invest/services/history-md/head-history-md . Проверить вручную фактические URL, обязательные параметры/авторизацию, размер/формат архива, точность `TRADE_TS`, `QUANTITY`, `DIRECTION`, `PRICE`, `TRADE_SOURCE`, `INSTRUMENT_UID`, покрытия MOEX/СПБ. Поля/ограничения записать в `provider-capabilities.json` с датой проверки.
2. CLI: `robot-detector history-audit --instrument <UID> --date YYYY-MM-DD --source exchange`; `download`, `normalize`, `detect`, `export`, `replay`. Поддержать локальный CSV для разработки без токена и без сети.
3. Не загружать большой архив без явного действия. Разумный default: 1 дата, 1 инструмент, лимит объёма на диск, resume/кеш; backoff/429, прокси-конфигурация, checksum, retries только на идемпотентное чтение.
4. Изолировать данные: `EXCHANGE`, `DEALER`, `UNKNOWN`; нельзя смешивать. Выявить смысл стороны в разных рынках, если неизвестен — `UNKNOWN` и не выдавать уверенную атрибуцию покупателя/продавца.
5. Учитывать разные режимы торгов, premarket/closing auction, перерывы, дни без торгов, изменения lot size; не склеивать паттерны поверх смены сессии без отдельного правила.
6. Сырые строки и нормализованные события отдельно: raw immutable + SHA-256 + provenance. Большие и лицензированные реальные выгрузки не коммитить. Тестовые маленькие анонимные/синтетические данные коммитить разрешено.

## B. Предобработка prints

- `quantity_lots > 0`, корректный price tick, неотрицательные timestamps; битые строки в quarantine c причиной.
- Детерминированная сортировка `(timestamp, sequence)`; контроль повторной доставки.
- Соседние исполнения одного пакета могут давать одинаковые timestamps, поэтому определить *два варианта*: исходные отдельные prints и `assembled_burst` с суммированием в маленьком окне. Запрещено делать вывод, что одинаковые timestamps принадлежат одному ордеру. Все варианты учесть в валидации.
- Строить статистику рынка: rate по 100мс/1с/10с, распределение размеров, доля нулевых/совпадающих моментов, time precision, активность по сессиям. Проверить, не округлены ли timestamps источником.
- Стороны `BUY/SELL` разделять **по значению поля провайдера**, без гипотезы о лимитной стороне.

## C. Схема детектора

### C1. Гипотеза

Регистрировать `H=(UID,source,side,q,T,phi,jitter,session)`, где `q` — типичный объём, `T` — период, `phi` — фаза. Для print `i`:

```text
phase_residual(i) = min_{k in integers} abs(t_i - (phi + k*T))
volume_residual(i) = abs(q_i - q)
match(i) = phase_residual(i) <= eps_time(T, source_precision)
           AND volume_residual(i) <= eps_volume(q)
```

Начальные конфиги **для перебора, а не доказанные пороги**: `T` от 200 мс до 30 мин (логарифмическая сетка + выделенные круглые значения); `min_matches` 6; `eps_time=max(2*timestamp_resolution, min(200ms, 0.02*T))`; `eps_volume` 0 для fixed-volume и `max(1 lot, 0.05*q)` для near-fixed. Разрешить `max_missing_cycles` и `gap_multiple <= N` в пределах непрерывной торговой сессии.

### C2. Поиск кандидатов (не O(N²) по полной ленте)

1. Разделить события по `instrument/venue/source/session/side`.
2. Построить индексы `quantity bucket → sorted times`, отдельные агрегации для `assembled_burst`.
3. Генерировать периоды из гистограмм временных разностей нескольких лагов, с разумными верхними ограничениями соседства; дополнить autocorrelation/periodogram на агрегированных импульсах. Учитывать гармоники (`T`, `2T`, `T/2`).
4. Для каждой пары `(T,q)` найти фазу через circular histogram: `t modulo T`, локальный пик, затем устойчиво уточнить `T, phi` на тренировочном отрезке (например RANSAC/robust regression).
5. Использовать динамическое сопоставление событий с ожидаемой сеткой времени, допускающее пропуск циклов и **не более одного использования одного print одним независимым кандидатом** после глобального разрешения пересечений.
6. Ранжировать: уникальность размеров/времени относительно фона, стабильность периода, доля прогнозов в holdout, count, coverage, p-value из этапа 2.
7. Сливать гармоники, практически совпадающие фазы и перекрывающиеся наборы принтов. Общее `observed_lots` считать по уникальным событиям, double-count = 0.
8. Каждая гипотеза имеет explain trace: `matched events`, отклонения, пропуски, альтернативные периоды, нетронутые события, reason for reject.

### C3. Пример, который обязаны воспроизвести

```text
Данные SYNTHETIC, время от начала сессии:
t(s)     q(lots)     side
0.000    100         SELL
5.015    100         SELL
10.010   100         SELL
12.300    40         SELL   <- фон
20.020   100         SELL   <- пропущен цикл 15.000
25.005   100         SELL
30.012   100         SELL
```

Ожидаемый вывод: гипотеза `q=100`, `T≈5.0s`, `matched=6`, `missed=1`, `observed_lots=600`; `t=12.300, q=40` не включать. Нельзя заявлять «единственный реальный продавец», только отдельный паттерн. Если появится параллельный робот `q=100,T=5s,phi=0`, количество физических роботов по этой ленте **неразличимо**.

### C4. Отдельный контроль «общий рыночный ритм»

Построить интенсивность сделок в 100ms bins и индикатор первых 100ms каждой секунды. В работе Muravyev et al. *Does trade clustering reduce trading costs?* (Financial Management 2022, DOI 10.1111/fima.12405) обнаружены абсолютная и относительная периодичности: https://onlinelibrary.wiley.com/doi/full/10.1111/fima.12405 . **Считать это фоновым эффектом**, не автоматически «найденным роботом». Сравнивать при фиксированной фазе с общерыночной сезонностью.

## D. Выход

- `robot-detector detect --input normalized.csv --config config.json --output results.json`.
- JSON строго по модели [ARCHITECTURE.md](ARCHITECTURE.md), плюс CSV таблица и audit report с количеством повреждённых/дублированных/пропущенных данных.
- Каждая строка: `pattern_id,side_label,typical_quantity_lots,period_ms,phase,last_seen,observed_lots,missed_cycles,matched_count,detector_state,confidence=null,predictions_unvalidated,coverage`.
- Печатать предупреждение о том, что `confidence` до этапа 2 **не калибрована**.
- Встроенный реплей: вывод от начала периода до каждого решения; запрет look-ahead на пути live-compatible detection.

## E. Тесты и критерии приёмки

Обязательно: unit tests на `phase modulo`, timestamp precision, 0/negative lots, битые строки, одинаковые timestamps, нехватку данных; property tests на перестановку входа и квантизацию; golden тест примера C3; 1 и 2 потока с различными фазами, поток с пропусками, нулевой поток, фоновая синхронизация на целых секундах; перекрывающиеся гипотезы и дедуп объёма; граница сессии; округление; разные `source`; отсутствие токена; ошибка HTTP и rate-limit.

**Definition of Done**:
- На фиксированных synthetic fixtures детектор воспроизводимо находит известные потоки; отчёт включает почему нашёл.
- Обнаружение истинных *реальных* роботов не заявляется до этапа 2.
- Нет future leakage и запросов на торговые операции.
- Архив выбранного инструмента реально протестирован (если данные доступны) либо официально зафиксирован blocking reason, не скрыт.
- Сборка и unit tests проходят без доступа к брокеру; live integration smoke тест запускается только явно с read-only token.
- Бенчмарк: 1 млн принтов, фиксированное железо, измеренные throughput/RAM/CPU; целевые SLA — в архитектуре.
- Коммит не содержит архивов с запретом распространения, секретов и изменений к IPO-модели.

## F. Порядок работ / коммиты

`01-schema-and-fixtures` → `02-tinvest-history-adapter` → `03-normalization-and-quality` → `04-period-candidates` → `05-phase-matching-dedup` → `06-cli-reports` → `07-integration-smoke-and-benchmark`. После каждого коммита — тест и отчёт о SHA.


## G. Дополнительные требования по реальным open-source реализациям (18.11.2026)

**Первичные исходники:** [Crypto Lake notebook](https://github.com/crypto-lake/analysis-sharing/blob/main/twap_detection.ipynb) и [binance_l3_est TWAP Rust](https://github.com/OctopusTakopi/binance_l3_est/blob/main/src/engine/twap.rs). Подробный разбор в [дополнительном исследовании](RESEARCH_EXPANSION_2026-11-18.md).

G1. Два раздельных экспериментальных baseline:
- `B0 MinuteBoundary`: селектор близости к границе целой секунды `[-50,+80]ms` по примеру Crypto Lake, **но сам по себе не объявляет минутный TWAP**. Обязательный дополнительный тест на `t modulo 60s` и сравнение с такой же фоновой активностью рынка.
- `B2 FFT`: `ClockTimeBinner` строит равномерную ось UTC; `sum(count)`, `sum(quantity_lots)`, `sum(notional)` независимо; линейный detrend, Hann, FFT, one-sided PSD, периоды `T=1/f`, кандидаты top N по threshold и последующий stage-1 event-level matching по фазе/q. Кол-во peak frequencies **не** равно числу алгоритмов.

G2. Проверенные параметры другого проекта `bin_ms=500`, `window_bins=512`, `threshold_sigma=3` — только контрольный benchmark, не настройки по умолчанию для нашей среды. Тесты `bin_ms` в {100,250,500,1000}, окна 5–60 минут, дополнительное окно для T>=60s. `cycles_in_window` и `nyquist_ok` выводить явно: `f_Nyquist=1/(2*bin_seconds)`. Если T неразрешим, не выдавать гипотезу.

G3. Не повторять возможную ошибку notebook: `signal.periodogram(trades.quantity,fs=1e6)` на **нерегулярных событиях** без временного бининга даёт частоты по номеру события, не физическому времени. Написать unit/property тест: при независимом изменении плотности фоновых prints, но одинаковой UTC периодичности целевого алгоритма, оценка T остаётся устойчивой на допустимой нагрузке; при `fs` ошибочно принятой за частоту поступления сделок — тест должен падать.

G4. Каждому спектральному кандидату записать `feature_type=count|lots|notional`, `bin_ms`, `window_s`, `candidate_T`, `peak_power`, `phase_match_score`, `number_of_cycles`, `null_baseline_version`, `holdout_status`. Калибровка вероятности — только этап 2.

G5. Synthetic test: каждая секунда занята разными участниками, но только один `T=60s,phase=5s,q=100` во всём потоке; `B0` поднимает фоновый кандидат, `B2` находит период, `PhaseAndQuantityMatcher` выделяет q=100 в 6+ последовательных минутных циклах, не принимая все секундные trades.

G6. Отдельные типы ошибки `INSUFFICIENT_CYCLES`, `NYQUIST_VIOLATION`, `BAD_TIME_PRECISION`, `MARKET_WIDE_PHASE`, `NO_UNIQUE_EVENT_ATTRIBUTION`. Не маскировать «нет доказуемого алгоритма» под «нет роботов».

G7. **Acceptance supplement:** deterministic comparison `B0` vs `B1 fixed-q` vs `B2 FFT-candidates`; performance/precision на одной synthetic fixture, обязательный контроль круглой секунды/минуты. В каждой релизной заметке указать, почему portable алгоритм отличается от описанного Rust и notebook, и почему нельзя заявить count.

## H. Временные шкалы и невозможность восстановления расписания по исполнению (дополнение)

Новые [научные и кодовые примеры](RESEARCH_EXPANSION_2026-11-18_PART2.md): ABIDES-NG/TWAP `remaining_quantity/slices_remaining`, hftbacktest latency/queue, Angstmann–Gebbie event vs physical clock.

- Каждая гипотеза фиксирует `observed_event_type=trade_print`; **нельзя** переименовывать прогноз следующего print в прогноз постановки следующего лимитного ордера.
- Отдельно проверять паттерны в `UTC` времени и `event index` (проверка длительной корреляции); выводить `time_basis`. Корреляция по номеру события — не интервал в секундах.
- Test H1: child-order schedule с постоянным `T=5s`, но fills с задержкой 0–20s. Детектор может найти слабый/non-periodic print pattern и обязан не заявлять точный schedule постановок.
- Test H2: один TWAP агент меняет дочерние размеры из-за частичных исполнений; `quantity change` не автоматически означает нового робота. Пример кода: [ABIDES-NG TWAP source](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/twap_execution_agent.py).
- Test H3: два независимо заданных истока prints имеют полностью одинаковые timestamps, объёмы и направление, но разную privileged truth; при публичном входе отображение не должно различаться из-за скрытого истинного count.
- Test H4: `lot_size` изменение и инструменты разных единиц; нормализовать количество и notional отдельно, не связывать q по одному числу без валюты/лотности.

**Acceptance:** доказательная таблица в отчёте разделяет `pattern of observed executions` от `hypothesized scheduling`; фикстуры с частичными fill задержками включены в CI. Неподтверждённый original parent order size оставлять `unknown`.
