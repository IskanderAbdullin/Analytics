# Этап 2 — строгая валидация и калибровка детектора

**Предусловие:** полностью воспроизводимая историческая обработка этапа 1. **Цель:** измерять качество, отделять повторяющиеся общерыночные ритмы от индивидуально различимых потоков, выбрать пороги без переобучения.

## 1. Обязательные артефакты

- Синтетический генератор `MarketTapeSimulator` с фиксируемым seed, сохраняющий `truth.json` (скрытый от детектора) и `tape.csv`.
- Четыре контролируемых фоновых процесса: неоднородный по времени Poisson; clustered/Hawkes-like; эмпирический replay с инъекциями; «секундные отметки» всей биржевой активности.
- Движок `Backtester` выполняет online-like пошаговый replay, не допускающий использования будущих данных ни при выделении паттерна, ни при предсказании.
- Метрики detection/forecast/calibration, в том числе разрезы по `instrument,venue,liquidity,session,frequency,jitter,quantity,coverage`.
- Версионируемый `validation-report.md` с параметрами, source hashes, периодом, hardware, метриками, confidence intervals и порогами релиза.
- Тест на "unknown count": два абсолютно совпадающих робота должны возвращать **один неразличимый паттерн**, а не два реальных робота.

## 2. Матрица синтетических сценариев

| Код | Генерация | Что требуется |
|---|---|---|
| S00 | 0 роботов, только фон | Низкая частота ложных «confirmed» |
| S01 | 1 fixed q/T/phase | Правильные q, T, phase и поток событий |
| S02 | 2 разных T | Разделение двух потоков |
| S03 | 2 одинаковых T, разные phase | Разделение при достаточном временном разрешении |
| S04 | 2 одинаковых q/T/phase | Не заявлять идентификацию двух роботов |
| S05 | Пропущено 10/30/50% циклов | Recall-vs-FDR и интервал T не превращать в 2T |
| S06 | Jitter 1/20/100/250/500 мс | Отдельные кривые устойчивости |
| S07 | Частичные fills на одном timestamp | Проверка политики `assembled_burst` |
| S08 | q изменяется по сценарию | Fixed detector должен честно промахнуться; advanced отдельно |
| S09 | Интенсивный фон на открытии и закрытии | Защита от сезонности |
| S10 | Общерыночные импульсы раз в 1 с | Не считать «одного робота» без устойчивого подмножества |
| S11 | Несколько сессий, перерыв, аукцион, halt | Не обучаться на разрыве как непрерывном времени |
| S12 | Две среды EXCHANGE и DEALER | Никакого объединения |
| S13 | Запаздывающие/перемешанные/дублированные сообщения | Idempotent replay или `coverage_bad` |
| S14 | Ошибки таймштампов 1 с округление | Запрет неоправданной субсекундной точности |
| S15 | Резкая смена T/phase/q, start/stop | Верные state transitions, отсутствие фиктивных новых потоков |
| S16 | Привязка объёма к рыночной активности | Проверить, что fixed TWAP не классифицирует как fixed без доказательств |
| S17 | Одновременные алгоритмы с общей сеткой, но разные источники | Сохранить отдельные гипотезы и неопределённость |

Сетка параметров: `T={0.25,0.5,1,2,5,8,10,30,60,300}s`; `q={1,10,50,100,1000}`; `pattern_count={0,1,2,5,10}`; интенсивности фона 0.1–1000 prints/s; random seeds >=100 для выбранных сочетаний. Полный декартов перебор может быть дорог — стратифицированная матрица + фиксированные worst-case tests.

## 3. Статистические нулевые модели

Уровень 1: условно неоднородный Poisson `lambda(t)` по времени сессии и волатильности.

Уровень 2: эмпирический conditional shuffle — сохранять разбивку по торговому режиму, локальную интенсивность (короткие бакеты), side, распределение q и одинаковые timestamps в пакетах, **переставлять фазы между временными блоками**, чтобы удалить конкретную долгоживущую последовательность, не уничтожив фон.

Уровень 3: clustered/Hawkes-like поток с burstiness и self-excitation, чтобы проверить ложные детекции на несамостоятельных кластерах.

Уровень 4: исторический non-injected replay как «неразмеченная действительность», **не** считать его строгим ground truth=0. Использовать как контроль частоты алертов и ручную инспекцию.

Для каждого найденного паттерна вычислять statistic `S` = сочетание вневыборочного precision, фазового контраста, counts и coverage. Для каждого `S` оценить эмпирический tail probability `p=(1 + #{S_null>=S_observed})/(1+B)`. Прогонять **полный pipeline поиска кандидатов** на каждой null-реплике: p-value уже выбранного периода при игнорировании процедуры выбора недействителен. При массовых гипотезах контролировать FDR через BH и/или глобальный max-statistic; доказать эмпирическую валидность при зависимости тестов, иначе применять более консервативные процедуры. Стороны и инструменты — отдельные family с явно определённой политикой множественных проверок.

## 4. Разделение на train/validation/test

- Разделение по дням/неделям, источнику, режиму ликвидности и инструментам; не перемешивать события одной серии между train и test.
- `development`: поиск формул/порогов; `calibration`: calibrator и ranking; `held-out`: окончательная слепая оценка (параметры заранее заморожены).
- Пошаговый тест по времени: для прогноза `t_{n+1}` использовать только `t<=t_n`; записывать forecast до открытия outcome window.
- `prediction_hit` — существование допустимого **нового**, не использованного ранее события в заранее объявленном интервале времени, в допустимом диапазоне q, side и источника. Разрешить one-to-one matching.
- Обязательно отчёт по confidence bins и reliability plot; если эмпирическая калибровка не работает, выводить `unrated`, а не «98%».

## 5. Метрики

**Pattern level:** precision, recall, F1, PR-AUC при сопоставлении *обнаружимых* паттернов с truth; matching через minimum-cost bipartite assignment на event overlap и разнице q/T/phi. На S04 `true_physical_robot_count` заведомо неидентифицируем — метрика `recoverable_pattern_count` отдельно.

**Event level:** доля правильно приписанных принтов; false attribution; двойное включение одного принта (строго 0 после fusion); inferred volume error.

**Prediction level:** hit rate top-K и unconditional baseline, Brier score/log loss (только если получены вероятности), calibration error, lead time; каждый прогноз проверять на будущем.

**Operational:** detections per instrument-hour, false alerts per instrument-day под null, throughput, memory, coverage-aware uptime, replay parity.

**Subgroups:** разбивка по ликвидности, бирже/источнику, periods <1s / 1–10s / >10s, фазам на круглых секундах, partial fills, session regime.

## 6. Целевые gates (предварительные, пересматриваемые ТОЛЬКО на development)

- `S00` и `S10`: не более 0.1 ложного confirmed паттерна на инструмент-час в контролируемых null сценариях; 95% CI и нагрузка/диапазоны обязательно приложить.
- `S01` при `q` фиксирован, `T=5s`, 8+ циклов, шум <10% соответствующей величины, timestamps <=10мс, фон до 10 prints/s: recall >=0.95, precision >=0.95 на held-out seeds. Не переносить этот порог на все рынки.
- `S02/S03`: F1 >=0.85 в заранее зафиксированном «разделимом» пространстве; невыполнение указывает на необходимость усилить модель.
- `S04`: запрещён подтверждённый count=2.
- Прогноз следующего события должен превзойти frequency-/size-matched null baseline на held-out, статистическая неопределённость рассчитана блоковым bootstrap.
- Для каждого релизного сравнения: точечная метрика + CI + количество наблюдений; только measured, без фиктивных значений.
- Если биржевые архивы неполны, quality gate честно возвращает `NOT_EVALUABLE` по отдельному рынку, а не «тест пройден».

## 7. Научное обоснование и конкретные переносы

- Muravyev et al., 2022, *Does trade clustering reduce trading costs?*: https://onlinelibrary.wiley.com/doi/full/10.1111/fima.12405 — абсолютная активность в первых 100мс секунды и относительная 1-секундная периодичность. Применение: **не** считать каждую синхронизацию секундным торговым роботом, строить null с common rhythm.
- *Spectral Volume Models: Universal High-Frequency Periodicities in Intraday Trading Activities*, Management Science: https://pubsonline.informs.org/doi/10.1287/mnsc.2024.06215 — Fourier-составляющие агрегированной активности; применить только как **генератор кандидатов/фоновую модель**, не идентификацию участников.
- Lillo, Mike, Farmer, 2005: https://journals.aps.org/pre/abstract/10.1103/PhysRevE.71.066122 — дробление крупных ордеров способно вызывать долгую корреляцию знака; не выдавать корреляцию за ID metaorder.

## 8. Tests + воспроизводимость

Собрать fixed `seeds.json`, golden fixture и сценарий скрытой разметки; CI проводит быстрый subset, nightly/full benchmark — отдельно. В отчёт включать commit SHA, OS, runtime, CPU, источник данных, версии календарей, config hash, seed, exact train/test boundaries, число просканированных T/q/phi и число проведённых проверок. Повторение одной и той же команды должно давать идентичный результат.

**Definition of Done:** все сценарии S00–S17 реализованы; отчёты и automated gates; независимая проверка на held-out; откалиброванные или явно `null` вероятности; отсутствуют завышенные claims; следующий этап разрешён только по итогам открытого scorecard.


## 9. Дополнительная матрица научных контрпримеров (18.11.2026)

Основание и исходники — [расширенный обзор](RESEARCH_EXPANSION_2026-11-18.md).

| ID | Новый тест | Pass criterion |
|---|---|---|
| P1 | Общерыночные prints каждую 1 секунду без единого последовательного владельца | FFT может найти период; `confirmed_pattern_count` только при уникальном out-of-sample event assignment, не равен 1 по FFT |
| P2 | Два независимых q/T/phase с несмежными наборами prints | Detected patterns отделены без повторного учёта принтов |
| P3 | 100 prints в ±80мс целой секунды без стабильной фазы минуты | Фильтр Crypto Lake не производит ложное `minute_twap confirmed` |
| P4 | Время округлено до секунды, истинный T=250ms | `INSUFFICIENT_TIME_RESOLUTION`, нельзя выдавать 250ms как проверенный |
| P5 | FFT при `bin_ms=500`, T=400ms | `NYQUIST_VIOLATION` или честный alias warning |
| P6 | FFT окно 256s, T=60s, недостаточно циклов | `INSUFFICIENT_CYCLES` до дополнительного окна, не подделывать confidence |
| P7 | Hawkes-clustered backgrounds из [HFT Simulator](https://github.com/sohaibelkarmi/High-Frequency-Trading-Simulator) и [hawkes-order-flow](https://github.com/MaherHarp/hawkes-order-flow), matched Poisson baseline | Раздельные false alarm rates; clustered null обязательно сильнее/равен по требованиям, а не автоматически эквивалентен Poisson |
| P8 | Одинаковая публичная лента для 1 vs 2 совпадающих синтетических «владельцев» | Система не может правильно угадать физическое число по одинаковым observations; показывать unidentifiable |
| P9 | Поток с 1s/1min common-clock periodicity по [Muravyev](https://doi.org/10.1111/fima.12405) и [Chen et al.](https://doi.org/10.1111/jfir.12280) | Controlled FDR при обоих clocks, не только 1s |
| P10 | Один refill между двумя невидимыми L2 updates, gap/resync | Нельзя утверждать true iceberg или calibrated probability |

**Обязательный benchmark:** составить detection PR curve по каждого из `B0 simple time filter`, `B1 fixed q/phase`, `B2 clock FFT+match`, `B3 Hawkes-adjusted`; измерить на одинаковых synthetic truth и той же holdout sample. Сравнить event-rate per bin и `notional` из Rust. Не переносить заявленные внешними проектами AUC или 3-sigma thresholds на MOEX.

**Дополнительно:** random shift test фаз относительно минут и секунд при сохранении сезонности; train/test split по инструменту/дню; отдельно оценивать качество Lee–Ready/tick-rule side inference, когда брокер не отдаёт authoritative aggressor sign. Для каждого conditional null публиковать чувствительность к временной точности, окну и ликвидности.

## 10. Новый основной benchmark: ABIDES-NG с известной правдой и обезличенным входом

**Основание:** [ABIDES](https://github.com/abides-sim/abides), [RMSC03](https://github.com/abides-sim/abides/wiki/RMSC03), [ABIDES-NG](https://github.com/GabrieleDiCorato/abides-ng), [исходный TWAP агент](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/twap_execution_agent.py). Подробно: [Research Part 2](RESEARCH_EXPANSION_2026-11-18_PART2.md).

### 10.1 Самый важный принцип

Обычный генератор `T=5с q=100` и шум мало что говорит о работе на реальном рынке: фоновая ликвидность **взаимодействует** с алгоритмом. В ABIDES есть агенты, биржевой matching и задержки. Провести blinded experiment: симулятор знает parent order IDs / agent IDs / order submission times; наш детектор получает только такую проекцию, какую может дать T-Invest.

### 10.2 Воспроизводимые deliverables

- Создать отдельное окружение `research/abides`, записать upstream SHA + BSD-3-Clause для ABIDES-NG.
- Реализовать `abides-generate`/помощник с manifest; генерировать `private_truth.json`, `public_trades.csv`, `public_l2.csv`, `projection_config.json`, `score.json`; **не** коммитить секретные/огромные артефакты.
- Сценарии: no-agent; 1 TWAP; 2 TWAP с разными фазами; 2 совпадающих TWAP; 1 VWAP; 1 POV; смесь 5–10 агентов; underfill catch-up и частичные исполнения; разные тик-сайзы; фиктивный feed loss и 100/250/500мс book sampling.
- Для каждого сценария 20+ seeds для пилота и отдельные 100+ unseen seeds для итоговой оценки после заморозки параметров; это **цель**, не выполненная статистика.
- Метрики: event attribution с one-to-one matching child fills, matched recoverable patterns, false positives per simulated-hour, `physical_count_not_identifiable`, period/phase error, holdout forecast performance.
- Контрфактические пары `with agent/without agent` с одним seed используются для comparison of distributions, **не** вычитать prints друг из друга — вмешательство меняет рынок.
- Выводить `simulator_truth` и `public_identifiability` как разные поля. Если два реальных агента создают один наблюдаемый паттерн, «найден 1 различимый поток» является корректным результатом.

### 10.3 Additional gates

ABIDES-0: контроль без execution agents не порождает массовый confirmed count из noise/market makers.

ABIDES-1: при underfill размеры TWAP клипов меняются; событие смены q не обязательно lifecycle нового агента.

ABIDES-2: VWAP profile совпадает с U-shaped рыночной активностью; тест показывает способность отличить stream от market-wide seasonality или `insufficient_identifiability`.

ABIDES-3: при идентичном публичном projection две разные `private_truth` обязаны давать идентичный detector output — защита от «угадывания владельца».

ABIDES-4: сравнение результатов `trades-only` и `trades+L2` при book downsampling: если информация потеряна, точность/уверенность должна деградировать, а не расти.

ABIDES-5: train vs blind test по **seed/scenario/time**, без leakage из private IDs, intervention label и будущих prints.

**Новый DoD:** хотя бы пилот ABIDES-0..5 с report и raw reproducibility hashes выполнен до серьёзного online заявления о «числе роботов». Никаких целей вроде 99% без измерений; целевые числа предыдущих разделов для toy scenarios не переносятся автоматически.

## 11. Дополнительные негативные сценарии Q01–X01

Перенести все идентификаторы и точные ожидания из [Research Part 2, §6](RESEARCH_EXPANSION_2026-11-18_PART2.md) в генератор и CI. Особое внимание Q01 (осцилляции котировок без сделок), A02 (изменение размера TWAP из-за underfill), C01 (подача регулярная, исполнения нерегулярны), A04 (неидентифицируемый count). Для экспериментальных методов quote/motif/ML отчётовать `NOT_EVALUATED` до добавления входных L2/benchmarks, а не «passed».

## Реальные результаты текущего прототипа (18.11.2026)

1. [Две исторические даты 16/17 ноября, две отрицательные модели](MULTIDAY_NULL_PROTOCOL.md): больше кандидатов в исходной выборке, чем в 12 контрольных перестановках и 12 циклических сдвигах для каждой даты, но **нет идентификации физических роботов и нет калиброванного FDR**.
2. [Хронологическая проверка на ранее не использованных 12/13 ноября](ROLLING_REAL_PILOT.md): **983 проверенных прогноза, 14 совпадений, 14 совпадений у сдвинутого контроля**. Преимущество над placebo в этой проверке **не обнаружено**.
3. Поэтому **релизный gate Stage 2 не пройден**. Не считать `confirmed`/реальные вероятности, не использовать исторические кандидаты как автоматические торговые сигналы и не обещать положительную предсказательную точность. Новые параметры изучать на отдельной development выборке, затем неизменёнными проверять на untouched dates/instruments.

