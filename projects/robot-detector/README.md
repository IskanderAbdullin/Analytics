# Market Robot Detector — самостоятельный проект внутри Analytics

**Версия проекта:** 0.2 (исследовательская) · **Обновлено:** 2026-11-19 · **Статус:** исторический прототип с подтверждённым импортом 121 920 реальных обезличенных сделок SBER (17.11.2026); статистическая точность распознавания не установлена.


## Adversarial common-clock null experiment — 2026-11-21

New read-only command `benchmark-clock-null` constructs market-wide periodic **background** prints (zero controlled execution agents) with opaque IDs and private independent producer labels. Both detectors see only the identical public tape; any claimed controlled-execution evidence is counted as a synthetic false attribution. Two independent profiles are available: fixed 100-lot prints and variable 25/50/75/100-lot market-wide clocked prints (`--clip-mode variable`). Both have **zero** controlled program ground truth. Aggregated per-trial alarms are **not** calibrated real-market FPR or proof of physical robot identities.

```powershell
dotnet run --project src/RobotDetector.Cli -- benchmark-clock-null `
  --trials 20 --background-prints 120 --cycles 12 --period-ms 5000 `
  --output data/results/clock-null.json
```

[Protocol, limitations and acceptance](docs/CLOCKED_NULL_STRESS.md). In the [verified 120-check CI smoke](https://github.com/IskanderAbdullin/Analytics/actions/runs/44888523166), each detector falsely attributed 81/180 independent prints from its matching adverse 3-seed clocked-null profile; this does **not** establish a real-world market false-positive rate. The prior four-scenario blinded benchmark remains available and unchanged. **Stage-2 scientific release gate remains CLOSED.**

## Научная проверка с приватной синтетической разметкой — 19.11.2026

Добавлен независимый `benchmark-blind` на четырёх сценариях: кластеризованный фон без контролируемого агента, TWAP с фиксированным объёмом, TWAP с переменным объёмом и TWAP с двумя отпечатками на один временной срез. **116 из 116 тестов пройдены**: [CI #44577833225](https://github.com/IskanderAbdullin/Analytics/actions/runs/44577833225).

Метки реальных генераторов **не передаются** детекторам: публичные `EventId` непрозрачные, оценки TP/FP считаются отдельно, уже после работы алгоритмов. В небольшом синтетическом тесте фиксированный алгоритм обнаружил 24/24 событий с постоянным объёмом и 0/24 с переменным; второй алгоритм, наоборот, 0/24 и 24/24. При расщеплённых исполнениях оба теряют часть доказательств. **Реальное количество независимых биржевых роботов по открытым сделкам не определяется**; принципиальная неидентифицируемость проверена на двух разных приватных разметках одной публичной ленты.

```powershell
dotnet run --project src/RobotDetector.Cli -- benchmark-blind `
  --seeds 5 --background-prints 120 `
  --output data/results/blind-research.json
```

[Подробный протокол](docs/BLIND_EXECUTION_BENCHMARK.md). Это мини-симуляция для тестирования, **не** полноценный ABIDES-NG, не калибровка на рынке и не торговый сигнал.

## Текущее состояние: локальная панель и API (19.11.2026)

**Проверено: 108/108 автоматических тестов.** Реализованы `dashboard` (один архив), `compare-archives` (2–20 архивов) и отдельный локальный сервер `RobotDetector.Server`. Проверки [сравнения SBER/MOEX](https://github.com/IskanderAbdullin/Analytics/actions/runs/44573901868) и [защищённого HTTP API](https://github.com/IskanderAbdullin/Analytics/actions/runs/44575738794) успешно прошли. История и локальный интерфейс работают без токена брокера и без торговых функций.

```powershell
# Из projects/robot-detector/
dotnet run --project src/RobotDetector.Server -- `
  --input fixtures/synthetic_activity_episode.csv --port 8765
# Открыть http://127.0.0.1:8765/
# Агрегированные данные: http://127.0.0.1:8765/api/v1/summary
```

Без сервера: `compare-archives --inputs "data/raw/SBER.csv;data/raw/MOEX.csv" --html comparison.html`. Подробности в [локальном API](docs/LOCAL_READ_ONLY_API.md) и [сравнении архивов](docs/MULTI_ARCHIVE_RESEARCH_COMPARISON.md). Сервер слушает **только 127.0.0.1**, отклоняет POST и внешние Host/Origin; HTML без скриптов и внешних ресурсов.

**Не готово:** аутентифицированный live T-Invest MarketDataStream, отдельный OsEngine клиент и статистически валидированный подсчёт физических роботов. На исторических holdout-данных старый прогноз регулярного q не обошёл placebo. Панель показывает рыночные наблюдения, а не подтверждённые роботы.

## Replay на исторической ленте — проверен на реальном SBER

Реализована команда `replay-audit` с ограниченным буфером событий и event-time watermark. В проверке [GitHub Actions #44572400620](https://github.com/IskanderAbdullin/Analytics/actions/runs/44572400620) воспроизведены **121 920** сделок SBER и **19 769 931** лот, без потерь и принудительного сброса очереди. **100/100 тестов пройдены**; [реализация в PR #23](https://github.com/IskanderAbdullin/Analytics/pull/23) объединена с `main`.

```powershell
dotnet run --project src/RobotDetector.Cli -- replay-audit `
  --input data/raw/sber.csv --receipt-order archive_row `
  --lateness-ms 500 --max-pending 10000 `
  --output data/results/replay.json
```

**Предупреждение:** `archive_row` — порядок строк архивного файла, **не реальное время доставки через API**. Он дал 11 394 нарушения хронологии и 54 429 событий старше watermark; искусственно отсортированный эталон `exchange_time_ideal` дал нули, не измеряя сетевые задержки. [Методика и ограничения](docs/BOUNDED_EVENT_REPLAY.md). Живой T-Invest Stream и настоящий streaming receiver пока не подключены, торговые команды отсутствуют.

## Локальный HTML-отчёт — готов к использованию

Добавлена команда `dashboard`, объединяющая профиль потока, всплески активности и диагностику качества временных меток. Она создаёт **автономный HTML**, открываемый на Windows без сети и сервера, и необязательный агрегированный JSON. **91/91 автоматический тест пройден**, на реальном SBER за 17.11.2026 обработаны **121 920** обезличенных сделок и **19 769 931** лот без потери исходных событий. [Проверка архива и панели](https://github.com/IskanderAbdullin/Analytics/actions/runs/44570331435).

```powershell
# Из каталога projects/robot-detector/
dotnet run --project src/RobotDetector.Cli -- dashboard `
  --input fixtures/synthetic_activity_episode.csv `
  --html data/results/research.html `
  --json data/results/research.json
start data/results/research.html
```

[Полное руководство по панели](docs/OFFLINE_RESEARCH_DASHBOARD.md). HTML не содержит скриптов, отдельных записей сделок и обращений к внешним сайтам. Результат **не** устанавливает владельцев заявок и не является торговым сигналом; достоверность обнаружения реальных роботов пока не подтверждена.

## Новые независимые методы и проверки источника — 19 ноября 2026

**Текущий проверенный код:** .NET 10, **83/83 офлайн-тестов**, [GitHub Actions](https://github.com/IskanderAbdullin/Analytics/actions/runs/44554682245). Проект остаётся исследовательским read-only инструментом: **подтверждённое число физических роботов/владельцев неизвестно; прогностическая точность не подтверждена**.

- `clock-phase-audit` — десять 100-миллисекундных фаз секунды, исторически заданная первая фаза и контроль максимума из десяти фаз по 99 сдвигам времени **целых минутных кластеров**. [Метод, литература, SBER/MOEX 17–18 ноября](docs/MARKET_CLOCK_PHASE_AUDIT.md), [проверка максимума на другой дате](docs/MAX_BIN_PHASE_AUDIT.md). Небольшая концентрация near-second у одного инструмента может исчезнуть на следующей дате, поэтому **это не доказательство конкретного робота**.
- `timestamp-quality` — количество уникальных времён, совпадающих timestamps, совпадающих времён и цен, доля кратных 1 мс и минимальный наблюдаемый интервал без удаления исходных сделок. На 18 ноября в группах одинаковых timestamp находились **32 311 из 83 515** сделок SBER и **5 902 из 10 584** MOEX. [Результаты](docs/TIMESTAMP_QUALITY_AUDIT.md).
- `cluster-compare` — отдельно создаёт **прослеживаемые аналитические группы** совпадающих по полному времени/цене/направлению/источнику/режиму/сессии сделок и сравнивает исторические кандидаты регулярности с оригинальными записями. На 18 ноября: SBER **57 → 64** кандидата, MOEX **6 → 6**, без потери лотов. **Группы не равны родительским заявкам или владельцам**. [Описание и тесты](docs/OBSERVABLE_PRINT_CLUSTERS.md).

```powershell
dotnet run --project src/RobotDetector.Cli -- clock-phase-audit --input data/raw/market.csv --trials 99 --output data/results/clock.json
dotnet run --project src/RobotDetector.Cli -- timestamp-quality --input data/raw/market.csv --output data/results/quality.json
dotnet run --project src/RobotDetector.Cli -- cluster-compare --input data/raw/market.csv --output data/results/clusters.json
```

[Проверка на реальных архивах](https://github.com/IskanderAbdullin/Analytics/actions/runs/44554682105) · [объединённые изменения PR #18–21](https://github.com/IskanderAbdullin/Analytics/pulls?q=is%3Apr+is%3Aclosed+robot+detector). Автоматические выставления заявок, онлайн-подключение, подтверждённая идентификация ботов и окончательная калибровка качества **не реализованы**.

## Альтернативные методы — доступны отдельно (19 ноября 2026)

Чтобы не подгонять один плохо предсказывающий регулярный алгоритм, в проекте реализованы **несколько независимых исследовательских вариантов**:

- **Фиксированный объём + периодичность** (`detect`) и **переменный объём + периодичность** (`variable-cadence`): только кандидаты последовательностей, а не доказанные торговые роботы.
- **Простой профиль потока** (`flow-footprint`): объёмы, reported BUY/SELL imbalance, лаг-1 по направлениям, межсделочные интервалы, Fano по секундным корзинам и доля сделок около круглой секунды. Испытан на 121 920 реальных сделках SBER, **203 групповых пятиминутных окна**, медианный Fano **8,883**. Данные показали неравномерность, но **не подтвердили** владельцев. [Описание](docs/TRADE_FLOW_FOOTPRINT.md), [реальный прогон](docs/FLOW_PUBLIC_PILOT.md).
- **Простые эпизоды высокой активности** (`activity-episodes`): сравнение с четырьмя **предыдущими** соседними окнами того же источника и сессии по числу сделок, лотам и перевесу reported side. **Не является детектором физических роботов** и не использует будущие сделки при формировании текущего наблюдения. [Метод и границы](docs/SIMPLE_ACTIVITY_EPISODES.md).

```powershell
dotnet run --project src/RobotDetector.Cli -- flow-footprint --input fixtures/synthetic_variable_clip_5s.csv --output data/results/flow.json
dotnet run --project src/RobotDetector.Cli -- activity-episodes --input fixtures/synthetic_activity_episode.csv --output data/results/activity.json
```

Проверка [GitHub Actions (62/62)](https://github.com/IskanderAbdullin/Analytics/actions/runs/44543220045) подтвердила сборку и офлайн-тесты второго простого детектора. Новые методы **read-only** и независимы от IPO-проекта. Логи реального рынка не позволяют идентифицировать отдельных владельцев алгоритмов. Исторический прогноз фиксированного объёма **не показал преимущества** перед контрольным сдвигом (14/983 против 14/983); не использовать кандидатов как торговые сигналы.

[Исследование альтернатив и открытые исходники](docs/ALTERNATIVE_APPROACHES.md). Реальное подключение T-Invest MarketDataStream, полноценный GUI, расширенный учёт стакана L2 и валидированный счёт физических роботов по-прежнему не завершены.

## Запускаемый прототип (Milestone 0.1)

Требуется **.NET SDK 10**. Запускайте команды из `projects/robot-detector/`. Проект **не** зависит от Python-пакета IPO, торговых API или установленного OsEngine.

```powershell
# Только синтетические сделки из репозитория
dotnet run --project src/RobotDetector.Cli -- detect --input fixtures/synthetic_twap_5s.csv

# Осцилляции best ask в синтетическом стакане (без биржевых сделок)
dotnet run --project src/RobotDetector.Cli -- quote --input fixtures/synthetic_quote_oscillation.csv

# Набор детерминированных офлайн-тестов
dotnet run --project tests/RobotDetector.SelfTests

# Иллюстративная статистика false positives / recall в синтетике
dotnet run --project src/RobotDetector.Cli -- benchmark --seeds 20 --noise-trades 200 --output data/results/benchmark.json

# Проверка одного прогноза на будущих событиях, не использованных при поиске
dotnet run --project src/RobotDetector.Cli -- walkforward --input fixtures/synthetic_twap_5s.csv --cutoff 2026-11-18T07:00:20.020Z --min-matches 4

# Второй независимый алгоритм — частотные кандидаты (FFT по UTC)
dotnet run --project src/RobotDetector.Cli -- spectrum --input fixtures/synthetic_twap_5s.csv --bin-ms 500
```

Чтобы скачать **публичный архив** с реальными обезличенными сделками, сначала проверьте нужный UID/тикер с кодом режима и день в официальном [T-Invest archive browser](https://developer.tbank.ru/invest/services/history-md/head-history-md). Команда скачивает **ровно один** файл, не запрашивает токен и не выставляет заявок:

```powershell
dotnet run --project src/RobotDetector.Cli -- fetch --date 2026-11-17 --instrument-id SBER_TQBR --output data/raw/sber_2026-11-17.csv
```

Укажите реальную дату/инструмент с доступным архивом. Фактически сервер возвращает **gzip-сжатые байты**, даже при имени `.csv`. Импортёр определяет GZip/ZIP по сигнатуре файла и распаковывает автоматически; расширение `.csv` для такого ответа корректно. Запись идёт в новую папку `data/raw/`, которая игнорируется Git. Ограничение провайдера: **не более 30 файлов в минуту с IP**; не запускайте массовые параллельные загрузки. Данные могут быть неполны/недоступны. Одна скачанная история не доказывает полноту потока и может не раскрывать сторону пассивной заявки.

**Семантика первых результатов:** поле `candidatePatternCount` — количество *кандидатов на различимые повторяющиеся потоки* в наблюдениях; `physicalBotCountKnown=false`, `confidenceCalibrated=null` и `state=candidate` должны сохраняться, пока нет проверенной калибровки. Анализ выполняется независимо в часовых UTC-окнах (параметр `--window-minutes`), поэтому один и тот же алгоритм в двух окнах может учитываться дважды как *эпизод*, а не как уникальная программа. Слишком плотные отдельные окна делятся на последовательные непересекающиеся части с предупреждением `SPLIT_DENSE_GROUP` — истинный единый паттерн может разделиться между ними.

См. [текущий статус реализации и ограничения](docs/IMPLEMENTATION_STATUS.md). GitHub Actions workflow [robot-detector-ci.yml](../../.github/workflows/robot-detector-ci.yml) компилирует и запускает синтетические регрессии без токенов брокера. **Сборка подтверждена:** [CI 44278450065](https://github.com/IskanderAbdullin/Analytics/actions/runs/44278450065) — .NET сборка, офлайн-тесты (18 проверок), CLI smoke успешно. [Реальный архив 44278450117](https://github.com/IskanderAbdullin/Analytics/actions/runs/44278450117): 121 920 сделок, 0 ошибок импорта, 209 предварительных кандидатов-эпизодов, без утверждения о числе физических роботов. [Методика и TLS](docs/PUBLIC_ARCHIVE_VALIDATION.md).

## Стадия исследования после двухдневной проверки (18 ноября 2026)

**Обновление:** самостоятельный .NET 10 проект собирается в GitHub Actions; 32 офлайн-теста пройдены. [Проверенный двухдневный протокол](docs/MULTIDAY_NULL_PROTOCOL.md): SBER 16.11.2026 (143 929 сделок, 126 отдельных эпизодов, 120 консервативно сгруппированных потоков) и 17.11.2026 (121 920 сделок, 209 эпизодов, 206 групп). Исходные наблюдаемые кандидаты превышают результаты 12 перестановок объёмов и 12 циклических сдвигов на каждой дате; это только предварительное, **не откалиброванное** наблюдение, не число независимых торговых роботов.

Реализован [консервативный алгоритм группировки эпизодов](docs/EPISODE_FUSION.md), не смешивающий источники, стороны и торговые режимы. Две различные контрольные модели доступны через CLI. Целая лента сделок не сохраняется в репозитории; отчёты по реальной истории содержат только агрегированные данные и SHA-256.

```powershell
# Дополнительные команды к основному историческому экрану:
dotnet run --project src/RobotDetector.Cli -- fusion --input data/raw/sber.csv --max-gap-cycles 12 --output data/results/fusion.json
dotnet run --project src/RobotDetector.Cli -- null-shuffle --input data/raw/sber.csv --mode permute --trials 12 --output data/results/null-permute.json
dotnet run --project src/RobotDetector.Cli -- null-shuffle --input data/raw/sber.csv --mode rotate --trials 12 --output data/results/null-rotate.json
```

Последняя самостоятельная проверка на данных двух торговых дней: [GitHub Actions #44295820963](https://github.com/IskanderAbdullin/Analytics/actions/runs/44295820963). До полноценного релиза остаются более реалистичные контрольные модели, оценка прогноза на будущих данных, живой T-Invest MarketDataStream и UI/OsEngine read-only adapter. Никакие торговые команды программа не посылает.

## Ограничение достоверности прогнозов

**Отдельная строго хронологическая проверка не показала преимущества перед контрольным прогнозом.** На ранее не использованных датах 12 и 13 ноября 2026 года детектор проверил 983 будущих окна: 14 совпадений с прогнозами и 14 совпадений с прогнозами, сдвинутыми на половину периода (в обоих случаях 1,42%). Это **не подтверждает** практическую прогностическую ценность текущих правил. Не использовать найденные кандидаты как готовые торговые сигналы.

Результаты с зафиксированными параметрами: [ROLLING_REAL_PILOT.md](docs/ROLLING_REAL_PILOT.md). Методика: [ROLLING_FORECAST.md](docs/ROLLING_FORECAST.md). Новый CLI-режим: `rolling-forecast --input file.csv --warmup-minutes 60 --stride-minutes 30 --max-cutoffs 12`.

## Назначение

Бесплатно выявлять по доступным публичным биржевым данным повторяющиеся алгоритмические торговые **паттерны** в инструментах MOEX/СПБ. Первый сценарий: одинаковые или сходные объёмы покупок/продаж через регулярные интервалы. Дальше — переменный TWAP, зависимость от рыночного объёма, повторное пополнение стакана, сетки, вероятные маркет-мейкеры и скрытые крупные поручения (*metaorders*).

**Не утверждать, что алгоритм показывает истинное число независимых программ или участников.** У обезличенных сделок нет идентификаторов конечного трейдера. Система считает *различимые потоки/гипотезы* с подтверждением и неопределённостью: один робот может породить несколько потоков, несколько — один неразличимый поток. Отдельно показывать «периодическую рыночную активность» и «выделенный поток сделок».

## Изоляция от IPO Analytics

Этот каталог — независимый проект, **не модуль IPO-прогнозирования**. Не менять существующие `src/ipo_forecast`, его зависимости, модели, CLI и данные. В дальнейшем использовать собственный `src/`, `tests/`, `data/`, `config/`, CI и сборку. Требуемый стек основного приложения — C#/.NET (совместимость с Windows и OsEngine); Python допустим только как **необязательный исследовательский инструмент** в отдельном окружении. Общий с IPO Analytics только Git-репозиторий; общего runtime нет.

## Дорожная карта и отдельные ТЗ

| Этап | Документ | Выход |
|---|---|---|
| 0. Основание | [Архитектура](docs/ARCHITECTURE.md) · [научные источники и примеры](docs/RESEARCH.md) | Проверяемые определения, интерфейсы, факты и гипотезы |
| 1. Исторический TWAP | [STAGE_01_HISTORICAL.md](docs/STAGE_01_HISTORICAL.md) | Архивы сделок, реконструкция потоков, CSV/JSON отчёты |
| 2. Валидация | [STAGE_02_VALIDATION.md](docs/STAGE_02_VALIDATION.md) | Синтетика, реалистичный фон, blind walk-forward и метрики |
| 3. Онлайн | [STAGE_03_REALTIME.md](docs/STAGE_03_REALTIME.md) | Stream-подписки, read-only сканер, web/UI, экспорт в OsEngine |
| 4. Расширение | [STAGE_04_ADVANCED.md](docs/STAGE_04_ADVANCED.md) | Стакан, условные классы стратегий, metaorder research, ML |

Релизный порядок: **1 → 2 → 3 → 4**. Внеочередное внедрение ML до измерения точности базового детектора запрещено.

## Принципы

- Начинать с официального сервиса [истории сделок T-Invest](https://developer.tbank.ru/invest/services/history-md/head-history-md) и [MarketDataStream](https://developer.tbank.ru/invest/api/market-data-stream-service-market-data-stream); сначала проверить наличие полей и реальное покрытие каждого рынка. Не подменять историю сделок свечами.
- Разделять биржевой и дилерский источники, сессии, тикеры и UID; не суммировать лоты из разных инструментов.
- Не путать сторону агрессора в сделке со стороной пассивной лимитной заявки.
- Реплей должен быть детерминированным, без доступа к будущим событиям.
- Базовые детекторы — прозрачные, с математически определяемыми признаками и объяснениями; сложные методы сравнивать с базовым.
- Для вероятности/уверенности использовать **эмпирическую калибровку**, а не произвольные проценты в UI.
- Все реальные запросы read-only. Ни токен с правами торговли, ни торговые команды приложению не нужны. Секреты только из переменных окружения/безопасного хранилища; без логирования и коммита.
- Источники, лицензии, ограничения хранения и распространения данных проверять до загрузки и публикации.
- В тестах различать реальные лицензированные данные, синтетические последовательности и неподтверждённые предположения.
- Все изменения — небольшими коммитами; без force-push; не разрушать существующий IPO-проект.

## Целевые сценарии пользователя

1. «Покажи, какие различимые регулярные продавцы работают в SBER сейчас: объём, интервал, фаза, общий оборот, последний/следующий прогноз».
2. «Сравни число подтверждённых потоков вчера и сегодня; укажи степень достоверности и покрытие данных».
3. «Проанализируй неликвидный инструмент: отличай один повторяющийся алгоритм от одной заявки, разбитой на несколько исполнений».
4. «Подключи аналитический сигнал к Babid Demo/другим OsEngine-роботам без открытия торговых полномочий в детекторе».
5. «Реплей одной и той же истории с одинаковым конфигом выдаёт побитово сопоставимые результаты».

## Что не является обещанием

Нельзя бесплатно гарантировать получение полных MBO-данных с order ID, истинных идентификаторов участников, скрытых поручений и каждой промежуточной модификации стакана. Сканер должен возвращать `unknown`/качество покрытия, а не выдумывать данные. Торговая прибыль и прогноз цен не входят в критерии приёмки.

## Справочные материалы

Научная и инженерная база с прямыми ссылками, формулами и воспроизводимыми примерами: [docs/RESEARCH.md](docs/RESEARCH.md). Отдельные технические проверки до подключения: [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md). Правила работы ИИ-агентов: [AGENTS.md](AGENTS.md). Первый воспроизводимый синтетический тест: [fixtures/](fixtures/). Точные квоты и состав полей T-Invest проверять по официальной документации перед разработкой и повторять проверки в интеграционных тестах; спецификация не фиксирует неподтверждённые лимиты как вечную истину.


## Дополнительный обзор реальных открытых реализаций (2026-11-18)

[**RESEARCH_EXPANSION_2026-11-18.md**](docs/RESEARCH_EXPANSION_2026-11-18.md) — конкретные репозитории/файлы: Crypto Lake `twap_detection.ipynb`, `binance_l3_est/src/engine/twap.rs` (500мс bins, FFT), Flowdepth L2 refill, BOCPD, Hawkes simulators, FlowForge и научные исследования. В каждом этапе ниже новые требования ссылаются на этот обзор. **Документы — ТЗ, а не заявление о готовой программе.**

## Третье расширение исследований: от периодических сделок к пассивным алгоритмам

Новый обзор [**Quote Volatility, ABIDES с известной разметкой и Matrix Profile**](docs/RESEARCH_EXPANSION_2026-11-18_PART2.md) (18.11.2026): опубликованная метрика осцилляций best bid/ask Bogoev–Karam, исходники TWAP/VWAP/POV агентов ABIDES-NG, контрфактическая проверка обнаружения, STUMPY motifs и различие event/UTC time. Добавлены критерии пригодности данных T-Invest и метрики невозможности идентификации конкретных владельцев.

**Приоритетное изменение roadmap:** stage 2 должен включать blinded симуляцию известных execution-агентов, а stage 4 — независимый детектор котировочных осцилляций, который может видеть активность без сделок. Оба направления остаются исследовательскими до воспроизводимых измерений.
