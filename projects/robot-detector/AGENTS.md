# Agent engineering contract — Market Robot Detector

Этот файл относится **только** к \`projects/robot-detector/\`. Проект независим от IPO Analytics.

## Строгие ограничения

1. НЕ менять \`src/ipo_forecast/\`, существующие Python модели/CLI IPO, \`pyproject.toml\` корневого IPO проекта и текущие источники данных IPO, если отдельного явного запроса нет.
2. НЕ внедрять торговую функциональность. Работать только с обезличенными публичными рыночными данными, read-only потоками, локальным replay и экспортом аналитики. Не запрашивать доступ к счетам, портфелю или заявкам.
3. НЕ выводить «N настоящих роботов/владельцев»: только различимые алгоритмические паттерны с неопределённостью и исследовательским объяснением. Не приписывать стороне пассивной заявки направление потока без проверки семантики провайдера.
4. НЕ помещать в коммиты токены, сырые рыночные архивы с сомнительной лицензией, реальные торговые персональные данные. В .gitignore проекта исключить data/raw, data/normalized, data/results, .env, traces и build artifacts.
5. Все эмпирические метрики привязать к конкретной выборке/seed/версии модели, не выдумывать confidence и backtest.
6. Сначала воспроизводимая baseline и stage-2 validity, потом streaming и ML. Сложный модуль не должен переписывать общий data contract без версии и теста миграции.
7. Не добавлять runtime dependency на OsEngine в Core. Адаптер OsEngine отдельный и опциональный.
8. Существующие данные и ошибки не исправлять «молчаливой очисткой»; quarantine + coverage flags + provenance.

## Обязательный порядок при реализации

- Прочитать README и ARCHITECTURE, затем документ текущего этапа, RESEARCH и [RESEARCH_EXPANSION_2026-11-18.md](docs/RESEARCH_EXPANSION_2026-11-18.md). В первую очередь изучить код прямых аналогов TWAP (Crypto Lake и binance_l3_est), без копирования ошибок нерегулярной временной шкалы.
- Создать issue/короткий change-plan: цель, точные файлы, тесты, риски.
- Делать минимальные осмысленные коммиты по предложенному порядку этапа; перед каждым push прогонять relevant unit tests. Нет force-push.
- Добавлять synthetic fixture, unit test, negative test, null model и измеримую acceptance criterion для каждого detector feature.
- В отчёте указывать branch, commit SHA, запущенные проверки, результаты, незакрытые вопросы и что **не** тестировалось.
- Любая внешняя научная статья: хранить URL, дату обращения, какие фрагменты реализованы, какие ограничены недоступностью MBO.
- Перед живым подключением проверять актуальную документацию провайдера и отсутствие методов торговли.

## Приоритет задач

1. Stage 1: data schema, history import, normalization, fixed-volume cadence, no-double-count, CLI/reports.
2. Stage 2: null models, synthetic truth, blinded calibration, forecast scoring.
3. Stage 3: robust T-Invest stream, UI, API and optional OsEngine adapter.
4. Stage 4: variable TWAP, book heuristics, model comparison, metaorder experiments.

Если source capability недоказана, помечать \`BLOCKED_BY_DATA\`, описывать альтернативы и продолжать независимые synthetic tests; не объявлять работу завершённой без проверок.
