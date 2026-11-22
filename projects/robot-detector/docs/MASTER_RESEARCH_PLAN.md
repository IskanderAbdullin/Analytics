# Market Robot Detector — единый живой научный план и техническое задание

**Версия:** 1.0 · **Состояние на 21.11.2026** · **Статус:** ACTIVE_RESEARCH_NOT_RELEASED  
**Репозиторий:** [IskanderAbdullin/Analytics](https://github.com/IskanderAbdullin/Analytics) · **Каталог:** \`projects/robot-detector/\`  
**Рабочая ветка:** \`agent/robot-detector-l2-binphase-20261121\`  
**Контроль конечной цели:** [issue #72](https://github.com/IskanderAbdullin/Analytics/issues/72)  
**Операционное ТЗ:** [AUTONOMOUS_RESEARCH_TZ.md](AUTONOMOUS_RESEARCH_TZ.md)  
**Точка восстановления:** [autonomy_state.json](../research/autonomy_state.json)  
**Правила каждого агента:** [AGENTS.md](../AGENTS.md)

> **Назначение.** Это единая актуализируемая карта проекта: научная цель, выполненное с доказательствами, незавершённые задачи, измеримые критерии, зависимости, методология и порядок пересмотра плана. **Не считать план завершённым, пока не выполнены независимые научные release-gates.** После каждого этапа выбрать следующий и продолжить в пределах активного запуска. При почасовом расписании каждый запуск восстанавливается по реальному GitHub HEAD, а не по старому сообщению чата.

## 0. Как пользоваться этим файлом: приоритет и источник истины

1. **Научная цель и требования к достоверности:** этот план + \`AUTONOMOUS_RESEARCH_TZ.md\`. Изменять можно обоснованно, без снижения критериев задним числом.
2. **Что произошло фактически:** оригинальные source-run GitHub Actions, репозиторные коммиты, тесты, пререгистрации и неизменяемые исходные агрегаты. Текст без evidence — **не доказательство**.
3. **Какую задачу делать прямо сейчас:** \`research/autonomy_state.json.current_stage\`, сверенный с фактическим branch HEAD и открытыми issue.
4. **Как выполнять:** \`AGENTS.md\` и секция 8 этого плана. Условия пользовательского разрешения / безопасности всегда выше любых локальных инструкций.
5. **Непрерывность:** GitHub Actions являются ограниченными проверками, а не средой для бесконечных циклов. Запланированный почасовой сеанс ChatGPT — отдельный запуск, не непрерывное вычисление в промежутках. Нельзя симулировать выполнение задач, которых не было.

**Если план, checkpoint и HEAD противоречат друг другу:** сначала проверить HEAD/CI, затем совместным commit обновить план и checkpoint; не стирать проверенную историю и не делать force push. Если параллельная ветка выросла — свериться и выполнить безопасное fast-forward/отдельную ветку, не перезатирать чужой результат.

## 1. Конечная научная цель и границы утверждений

### 1.1. Что хотим получить

Открытый воспроизводимый исследовательский комплекс для **обнаружения и объяснения наблюдаемых признаков алгоритмического исполнения и взаимодействия с L2** в обезличенной публичной биржевой ленте. Минимально пригодный научный результат:
- прозрачный replay событий, синхронизированного стакана и публичных сделок; контроль отсутствующих данных, семантики агрессора/пассивной заявки и причинного порядка;
- объяснимые baseline-признаки: ритмы в event и clock time, размер/сторона/кластеризация сделок, quote depth/imbalance, spread, latency/age, лагированные L2 признаки, различие split fills и независимых событий;
- сравнение с **сложными отрицательными контролями**: Poisson, fixed-cadence без целевого робота, momentum, event-cluster-preserving null, неполные потоки;
- изолированная проверка на *независимых* симуляциях ABIDES с приватной oracle-разметкой **только после public-only inference**;
- отдельная честная описательная проверка на публичных исторических данных, где нет реальных owner labels; указание устойчивости к рынку, дню, фазе, полноте стакана, горизонту и источнику;
- воспроизведение кода, фиксированных протоколов, всех исходов и статистики по одной документированной процедуре.

### 1.2. Чего принципиально НЕ утверждать

По обезличенным сделкам и L2 **нельзя автоматически доказать**, что конкретную заявку выставил конкретный человек/робот, посчитать число независимых физических владельцев или вычислить реальную owner-level FDR без независимого ground truth. Синтетическая oracle accuracy не равна real-market accuracy; **real-market FDR** остаётся неизвестной без независимых меток; ассоциация цены и книги не доказывает причинность. Отсутствие обнаруженного сигнала при неизвестном покрытии данных не означает отсутствие робота.

**Допустимый альтернативный научный итог** при доказуемой неидентифицируемости — воспроизводимый набор методов, экспериментальных ограничений и контрпримеров с честными границами, а НЕ искусственно положительная метрика.

## 2. Что уже выполнено — факты с проверяемыми доказательствами

| ID | Статус | Полученный результат | Где проверять |
|---|---|---|---|
| BASE | **DONE — инфраструктура** | Автономное ТЗ, \`AGENTS.md\`, checkpoint, GitHub master issue, seed/provenance/negative tests | [AUTONOMOUS_RESEARCH_TZ](AUTONOMOUS_RESEARCH_TZ.md), [#72](https://github.com/IskanderAbdullin/Analytics/issues/72) |
| REAL-PRINTS-01 | **DONE — отрицательная переносимость** | 8 оригинальных Binance SPOT архивов LTCUSDT/BCHUSDT, **776 007** публичных исполнений; сильные cluster-preserving nulls. Несколько фаз/дней BCH **не** подтвердили переносимость наблюдаемого эффекта LTC | [BCH_FOUR_DAY_OCCUPANCY_PANEL_20261121](BCH_FOUR_DAY_OCCUPANCY_PANEL_20261121.md), [original run #44921851326](https://github.com/IskanderAbdullin/Analytics/actions/runs/44921851326) |
| LOBSTER-QA | **DONE — формат, не детектор** | Исторический NASDAQ AMZN 2012-06-21, 10 уровней, **269 748** синхронизированных \`message + post-event book\`. Реальные участники неизвестны; у вендора нет отдельно опубликованной подписанной SHA | [исходная QA #44922750898](https://github.com/IskanderAbdullin/Analytics/actions/runs/44922750898), [формат](LOBSTER_AMZN_PUBLIC_SAMPLE_FORMAT_AUDIT_20261121.md) |
| L2-EVENT-01 | **DONE — описательный replay** | Реальный event-time spread/depth/imbalance, quote transitions, tied timestamps и исполнение пассивной заявки. Source-only агрегаты; raw vendor events не публикуются | [исследование #44925498585](https://github.com/IskanderAbdullin/Analytics/actions/runs/44925498585), [метод](LOBSTER_EVENT_TIME_FEATURES_20261121.md) |
| L2-CLOCK-02 | **DONE — ошибка взвешивания** | Event-weighted spread **1308.6169** против duration-weighted **1284.8502** единиц цены ×10000; right censoring, без look-ahead | [оригинальный прогон #44926012965](https://github.com/IskanderAbdullin/Analytics/actions/runs/44926012965), [отчёт](LOBSTER_CLOCK_VS_EVENT_WEIGHTING_20261121.md) |
| ID-BOUND-03 | **DONE — конструктивный отрицательный результат** | Два синтетических мира: полностью идентичные публичные события и 10-level L2, но **1 против 3** скрытых владельцев. Поэтому public order reference не owner ID | [контрпример](SYNTHETIC_L2_OWNER_NONIDENTIFIABILITY_20261121.md), [CI #44926352634](https://github.com/IskanderAbdullin/Analytics/actions/runs/44926352634) |
| COVERAGE-04 | **DONE — исходная полнота** | UNKNOWN, ABSTAIN и synthetic-only eligible при пропусках источника, невыравненных книгах и stale quotes; **4/5** с известным oracle диапазоном нельзя выдавать за 5/5 | [отчёт](EXCHANGE_L2_COVERAGE_ABSTENTION_20261121.md), [CI #44926821602](https://github.com/IskanderAbdullin/Analytics/actions/runs/44926821602) |
| REPRO-05 | **DONE — offline на зафиксированной стадии** | One-command без внешних ZIP и секретов; исходная успешная проверка **113 тестов в 14 наборах** (позднее список может расти), агрегатные исходные JSON | [метод](OFFLINE_REPRODUCIBILITY_20261121.md), [CI #44927111552](https://github.com/IskanderAbdullin/Analytics/actions/runs/44927111552) |
| TOY-06 | **DONE — отрицательный hard negative** | Фиксированный 10s grid: 4/4 synthetic positives, **4/4 ложных тревог** на периодическом фоновом шуме без target; ленты совпадали с positive | [отчёт](TOY_PUBLIC_EXECUTION_RHYTHM_HARD_NEGATIVE_20261121.md), [CI #44927619509](https://github.com/IskanderAbdullin/Analytics/actions/runs/44927619509) |
| ABIDES-07 | **DONE — негативный genuine matching-engine transfer** | ABIDES-NG, seeds 2801/2802, 6 source runs: Poisson **0/2** alarms; fixed-cadence noise **2/2 ложных**; injected 45s TWAP **2/2 пропущены**, несмотря на 29 posthoc controlled executions | [отчёт](GENUINE_ABIDES_FIXED_CLOCK_TRANSFER_20261121.md), [original CI #44928306325](https://github.com/IskanderAbdullin/Analytics/actions/runs/44928306325) |
| ABIDES-08 | **DONE — подтверждённый отрицательный контроль** | 12 независимых original ABIDES runs, 3 seeds×4 когорты: fixed-20s без TWAP превосходит TWAP по доле совпадений с 45s сеткой (**0,0820 против 0,0302**), legacy 10s — **3/3 ложных** и **3/3 пропуска**, controlled TWAP 67 fills | [отчёт](ABIDES_MULTISCALE_PUBLIC_L2_20261121.md), [original CI #44935340284](https://github.com/IskanderAbdullin/Analytics/actions/runs/44935340284) |

**Точные условия:** эти числа относятся только к указанным историческим и синтетическим выборкам; ни одна строка не устанавливает реальную биржевую FDR/личность участников. Все отрицательные результаты сохраняются, не «лечатся» подбором фазы. Старые исторические формулировки в IMPLEMENTATION_STATUS, которые позднее исправлены, читать с последующими уточнениями: научное использование публичного LOBSTER demo не тождественно условиям платной подписки. Не публиковать vendor ZIP/CSV как своё.

## 3. Что предстоит — основная зависимая программа

Приоритет означает **научную полезность**, не обязательное строгое движение по номерам. Агент вправе менять порядок на основании проверяемых данных по протоколу секции 7. Каждая стадия имеет собственные acceptance criteria и NEXT_ACTION.

### VERIFIED / RD-ABIDES-MULTISCALE-08 — завершённый пререгистрированный эксперимент с отрицательными контролями

**Инициатива:** [issue #89](https://github.com/IskanderAbdullin/Analytics/issues/89)  
**Frozen design:** [abides_multiscale_public_l2_protocol_20261121.json](../research/abides_multiscale_public_l2_protocol_20261121.json). **Оригинальный протокол был записан до просмотра данных. 12 исходных matching-engine запусков успешно выполнены [#44935340284](https://github.com/IskanderAbdullin/Analytics/actions/runs/44935340284)**; это отдельный эксперимент после первого 10s теста #44928306325.

- **Исследовательский вопрос:** отделяют ли фиксированные и многошкальные публичные temporal/L2 признаки специально введённый execution agent от обычного periodic/momentum noise лучше, чем один 10s-clock сигнал? И какие ложные признаки сохраняются?
- **Источник:** ABIDES-NG pinned \`ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242\`, публичный matching engine, 5-level L2, рынок ABM, 09:30–09:38.
- **Зарезервированные в локальном seed registry, ещё не выполненные в новом source-run seeds:** 2901/2902/2903; зарегистрированы *до запуска* как `genuine_abides_public_multiscale_l2_12run`. Регистрация **не доказывает глобальную невиданность** и не является успешным экспериментом.
- **Всего 12 source runs:** для каждого seed — Poisson 60, fixed-20s noise 60, 50 Poisson +10 momentum-25s, 60 Poisson + один injected TWAP 45s/1200 lots.
- **Предзаданные публичные признаки:** grid 10/20/45/90 sec с допуском ±250 ms и фиксированным anchor 09:31; event fraction/lift как описательная величина, **не p-value**; строго lagged L2 bins 30/60 sec с проверкой возрастов котировок и abstention. Для сопоставления сохранить и старое фиксированное правило 10s/0.22 отдельно, без переобучения.
- **Предохранитель от утечки:** public projection вычисляется до чтения \`passive_agent_id/aggressive_agent_id\`; private oracle допускается лишь после scoring для оценки simulator truth.
- **DoD:** (a) код и негативные offline тесты прошли, (b) ровно 12 исходных сопоставимых прогонов либо документированный источник препятствия, (c) все четыре сценария и все seeds сохранены, включая ошибки, (d) сравнения без posthoc thresholds, (e) отдельно показаны доля abstention и отсутствие реальной FDR, (f) source-only компактный отчет, source SHA/revision, commit+push+checkpoint, (g) дорогой workflow после первого успешного прогона manual-only.

**Если гипотеза не подтверждается:** не выбрасывать fixed-20s или momentum фон; сохранить отрицательный исход, проверить ошибки времени/метрик и перейти к обобщённому распознаванию observable patterns вместо «определения владельцев».

**Фактическая проверка и отрицательный вывод (21.11.2026):**
[полный оригинальный отчёт](ABIDES_MULTISCALE_PUBLIC_L2_20261121.md).
Source-only 45s fraction: Poisson **0,01022026**, fixed-20s background **0,08201092** (БЕЗ target), momentum **0,00990425**, injected TWAP **0,03022026**. Следовательно, **fixed-cadence фон даёт сильнее 45s-clock паттерн, чем подтверждённый TWAP**. Старый 10s classifier: **3/3 ложных тревоги** на fixed-noise и **3/3 пропуска** positive с **67 posthoc target fills**. Отрицательные результаты сохранены, thresholds не переобучены. 12 реальных симуляций ABIDES и L2 source есть; **реальная market-FDR по-прежнему неизвестна**.

### P0 / RD-SYNTHETIC-HOLDOUT-09 — текущая проверка ложной гармоники и подготовка независимого holdout

**Зависит от:** RD-08, проверки достаточности source simulation и корректного стыка времени/L2.

**Новый приоритет после отрицательного RD-08:** сначала доказать на source-free синтетике, почему фиксированный 20s фон может пересекаться с 45s сеткой при неизменном clock anchor (НОК/модульные фазы); затем зафиксировать **новую** адаптированную *conditioned-null* гипотезу и только после этого брать независимые seeds (ранее потраченные 2901–2903 не считать holdout). [Issue #90](https://github.com/IskanderAbdullin/Analytics/issues/90). Оценивать не «число роботов», а **специфичность наблюдаемого признака** при наличии сложного фона.

**Прогресс этапа (source-free проверено, original next source ещё не запускался):**
[Модульное доказательство 20s↔45s aliasing](PUBLIC_CLOCK_ALIASING_NEGATIVE_20261121.md):
`lcm(20,45)=180s` и **1/9** совпадений при полном отсутствии целевого TWAP;
односекундный сдвиг фона даёт **0/90** на той же сетке. [Новый frozen
exploratory hypothesis](../research/abides_background_conditioned_ratio_precommit_20261121.json):
`R=N45/N20>=0.60` по public prints, abstain если N<200, N20<8 или eligible lagged30<5.
**Этот порог выбран по уже просмотренным 2901–2903**, поэтому никакой
confirmatory точности до нового отдельного 16-run ABIDES с 3001–3004 нет.

- До просмотра данных объявить новое разделение development/test **по независимым matching-engine seeds и семействам фонов**, а не по фазам одного и того же файла.
- Разделить **периодические без injected target**, random, momentum, market-maker-like, а при возможности несколько TWAP/VWAP/POV режимов, выбор инструментов и активности. Исключить label leakage и дубль seed/replay.
- Конкуренты: trivial always-negative, random-fixed-rate, 10s legacy, intensity-conditioned grid, cluster-preserving timing, лагированное imbalance и их обоснованная простая комбинация.
- Предзадать покрытие и ошибки: TP/FP/FN/TN, precision/recall только **на симуляторных oracle labels**, abstain-rate, confusion per cohort, seed uncertainty и тренд по источнику. Небольшие N оформлять как exploratory, не как статистически значимый вывод.
- **DoD:** отдельный пререгистрированный документ, контрольные holdout-данные, воспроизводимые сводки *всех* сценариев, отсутствие выбора порога по holdout и evidence ссылок. Если метрика бесполезна — обязательный обоснованный негативный результат.

### P1 / RD-DATA-ROBUSTNESS-10 — полнота, реконнекты, идентичность и causal order

- Сопоставление exchange event time vs receive time, equal timestamps и split fills; данные после события не использовать как pre-event при той же метке.
- Incomplete/partial L2 depth, locked/crossed best book, stale quotes, zero-quote session, incomplete terminal bins и ненадёжные источники. Для неизвестного exchange-complete sequence возвращать UNKNOWN.
- Stress tests: drop 1/5/20% synthetic events, reorder, duplicate, systematic missing windows, quote-age mismatch; показать деградацию и долю abstention по сценарию, **не выдавая missing market truth за отрицательный класс**.
- **DoD:** deterministic source-free tests и reproducible coverage matrix с reason codes; минимум один «fail-closed» сценарий на каждую угрозу; source completeness точно обозначена.

### P1 / RD-REAL-CROSSMARKET-11 — независимая реальная описательная проверка

- Даты, символы, рынки и фазовые смещения фиксировать до анализа **новой** выборки, не переиспользовать ранее посмотренные дни как независимое подтверждение.
- Ленты Binance prints, публичный демонстрационный LOBSTER L2 и при наличии другие открытые источники: чётко обозначать несовместимые side/price/clock/depth/source semantics; не смешивать «число событий» с «временем котировки».
- Контроли: exact timestamp cluster-preserving, activity/occupancy-conditioned, multiple testing, dependence of overlapping bins, selection bias, feed gaps, source license.
- Метрики только **наблюдаемых паттернов**: их устойчивость, масштаб, отклонение от условных контролей. **Не** истинные личности, не owner-level accuracy/FDR.
- **DoD:** источник и hash/provenance, предрегистрация, все исходы и ограничения, один компактный агрегат; исходные ZIP и персональные идентификаторы не добавлять в Git.

### P1 / RD-SCIENTIFIC-INTERPRETATION-12 — статистическая честность и проверки опровержений

- Проверить причинные альтернативы: сезонность внутридневной активности, агрегирование частичных исполнений, queue effects, фоновые periodic quote updates, рыночные новости, microstructure latency.
- Невозможность идентифицировать владельца показать рядом с тем, что *может* наблюдаться; не смешивать задачи.
- Сопоставить ABIDES со статистикой реальных лент; domain gap документировать отдельно, не объявлять переносимость.
- Все отрицательные репликации BCH/ABIDES включить в основной отчёт, не в примечания.
- **DoD:** hypothesis ledger со статусом SUPPORTED / REFUTED / INCONCLUSIVE, ссылками, зависимостями, альтернативными объяснениями и независимым аудитом главных утверждений.

### P2 / RD-REPRO-RELEASE-13 — итоговый воспроизводимый исследовательский продукт

- Одна CLI-команда для offline tests/source-free synthetic benchmark; отдельный **явный** ручной путь для bounded external source replays.
- Версии зависимостей и upstream commit, фиксированные параметры/seed ledger, reproducible CI, unit/negative tests, manifest provenance, JSON scientific report + README.
- Minimal read-only исследовательский API/визуализации только если они верифицируют научную гипотезу, не ради интерфейса. Optional OsEngine integration — **позже** после приоритета статистической корректности.
- **DoD:** clean checkout build/test без закрытых source files или секретов; исходные source research результаты доступны по ссылкам/протоколу; независимый обзор «известно/неизвестно»; компактные артефакты.

### P2 / RD-FINAL-AUDIT-14 — решение о достижении конечной цели

- Проверить воспроизведение, baseline comparison, negative controls, source coverage, независимые holdouts и полностью описанные ограничения.
- Честно решить, достигнута ли ограниченная цель обнаружения **observable algorithmic patterns**, либо необходимо явное описание принципиальной неидентифицируемости. Без подтверждения критериев не заявлять победу и не закрывать #72.
- Отдельно зафиксировать *non-goals*: настоящие владельцы, истинная market FDR, коммерческая система исполнения, live order placement — не входят в доказанный научный результат.

## 4. Что исследовать дополнительно и где искать (разрешённый внешний поиск)

Агент **может и должен** искать лучшие методы, готовые тестовые источники и свежие работы, если это уменьшает конкретную неопределённость текущего этапа. Базовые проверенные ориентиры:
- [ABIDES-NG: quickstart + L1/L2 source semantics](https://github.com/GabrieleDiCorato/abides-ng/blob/main/docs/getting-started/quickstart.md) и [config-system](https://github.com/GabrieleDiCorato/abides-ng/blob/main/docs/reference/config-system.md); привязка исходных расчётов к **зафиксированному commit**, не автоматически к \`main\`.
- [Официальные публичные LOBSTER samples](https://php.lobsterdata.com/info/DataSamples.php) и [структура event/message/orderbook](https://php.lobsterdata.com/info/DataStructure.php).
- [ABIDES original](https://github.com/abides-sim/abides) — альтернативные типы агентов, пределы моделирования и baseline.
- [Statistical Predictions of Trading Strategies in Electronic Markets](https://academic.oup.com/jfec/article/23/2/nbae025/7826742) — пример того, что участник-уровневая эмпирическая задача зависит от наличия специальных данных; не выдавать её модель за уже внедрённую.
- [Order flow dynamics and cancellation](https://doi.org/10.1002/hf2.10026) — альтернативные микроструктурные признаки и ограничения вывода о манипуляции.

**Метод внешнего исследования:** сформулировать точный вопрос → найти первоисточник, проверить дату/версию, воспроизведение и доступность → сравнить с реализованными кодом и негативными тестами → предложить конкретный эксперимент/исправление с DoD → только затем изменить roadmap/checkpoint. Не переписывать в проект чужой непроверенный код, не скачивать массовые архивы, не обходить ограничения доступа. Новую литературу записывать как \`research leads\`, а не как подтверждённые результаты проекта.

## 5. Как организовать знания, исходники и доказательства

- \`AGENTS.md\`: **обязательные правила поведения агента**, ссылка на этот план и протокол его развития.
- \`docs/MASTER_RESEARCH_PLAN.md\`: **единый адаптивный стратегический план**, текущие научные эпики и результат этапов.
- \`docs/AUTONOMOUS_RESEARCH_TZ.md\`: неизменяемые принципы автономного выполнения, безопасности и критерия итоговой научной корректности.
- \`research/autonomy_state.json\`: машинно-читаемый конкретный \`current_stage\`, \`backlog\`, уже проверенные результаты и восстановление следующего запуска.
- \`research/seed_registry.json\`: уникальность локально потраченных synthetic seeds; невозможно называть новый seed «глобально слепым» только из отсутствия в локальном списке.
- \`research/*precommit*.json\`: frozen hypotheses/thresholds/scenarios **до** просмотра новых исходных источников.
- \`tools/\`, \`tests_background/\`, \`tests_research/\`: анализаторы, иммутабельные public-only projection gates, offline негативные тесты.
- \`fixtures/\`: небольшие **агрегатные** результаты, SHA, metadata — не исходные рыночные события.
- \`docs/*20261121*.md\`: архив доказанных этапов. Обнаруженная ошибка оформляется исправлением и новой записью, не тихой заменой исходного вывода.
- GitHub issues: [#72](https://github.com/IskanderAbdullin/Analytics/issues/72) навсегда служит конечной целью; частные issues только этапы.
- GitHub Actions: исходные дорогие source runs **ручные после первого успеха**; дешёвые offline проверки запускаются автоматически **только в открытом репозитории**.

В checkpoint достаточно компактной сводки. Гигантские исторические протоколы и отчёты хранятся в документах с ссылками, не копируются внутрь state. Не писать ключи, пароль, токены, private account/agent IDs или raw vendor trades.

## 6. DoD каждого этапа и единая шкала статусов

**Статусы:** \`PLANNED\` (идея), \`FROZEN\` (предрегистрация до данных), \`IN_PROGRESS\` (код/прогон), \`VERIFIED\` (тесты + source evidence), \`REFUTED\` (доказанный отрицательный итог), \`BLOCKED\` (точный блокер и обход), \`REPLACED\` (основанная на данных новая гипотеза), \`RELEASED\` (отдельный аудит всей цели).

В каждом чекпоинте фиксировать: stage ID; формулировку гипотезы; критерий успеха/опровержения; статус source coverage; source version; какой эксперимент **планировался**, какой **фактически** сделан; N и независимость; что вышло отрицательным; подтверждение unit/negative; источник CI URL; точный commit SHA и remote HEAD; \`NEXT_ACTION\` и его научную ценность.

Стадия может быть отмечена VERIFIED или REFUTED **только** если есть воспроизводимое доказательство. Если тесты не запускались, указывать NOT_RUN; если CI ещё в работе, PENDING. **Зелёный CI подтверждает выполнение конкретных тестов**, но не качество всех научных утверждений.

## 7. Как самостоятельно пересматривать и улучшать план (обязательное разрешение)

**План не догма.** Агент имеет полномочие **искать, исправлять, детализировать, переставлять, добавлять, объединять и удалять ещё не выполненные гипотезы**, если возникает научно более полезное направление. Это разрешение относится к техническим и методическим решениям внутри проекта; не отменяет требований безопасности, разрешений на подключение ПК, финансовых операций и использования приватных репозиториев.

### Триггеры пересмотра

1. Сильный negative control опроверг baseline / обнаружена утечка oracle labels, lookahead, нарушение семантики стороны.
2. Новые публикации, документы биржи или открытые библиотеки предлагают более строгую проверку, меньшие затраты или новое объяснение.
3. Изменился доступ к исходному источнику, его версия, часы, покрытие или правила распространения.
4. Пропавший/неполный CI, ошибка в источнике или несостоятельный научный критерий.
5. Следующий этап обещает меньшую информационную ценность, чем независимый тест оставшегося большого риска.

### Протокол законного пересмотра

- Сформулировать **почему меняем**: найденная проблема, ссылка на исходное доказательство / источник и что это означает для цели.
- Оценить 2–4 альтернативы (информационная ценность, независимость, стоимость, ресурсы, лицензии, риски, безусловные негативные проверки), выбрать наиболее полезную.
- Сохранить существующие VERIFIED/REFUTED результаты и frozen первоначальную гипотезу. **Не** редактировать исходный frozen протокол постфактум; создать новый \`v2\` с новым holdout, если меняется метрика/порог/сценарий.
- В ОДНОЙ логической change set обновить этот файл, \`AGENTS.md\` при изменении правил агента, \`research/autonomy_state.json\` и при необходимости GitHub issue/файлы тестов. Изменение плана зафиксировать отдельным **Decision Record**: что/почему/альтернативы/последствия.
- Сделать необходимые tests → commit → fast-forward push → проверить remote SHA и CI; если проверки ещё идут, оставить PENDING, не утверждать PASS.
- Немедленно начать новый приоритетный этап в **том же активном запуске**; почасовой планировщик в следующем сеансе читает обновлённые файлы.

### Строго запрещено под видом «улучшения»

Подбирать удобный seed, фазу, порог или дату после просмотра результата и выдавать за исходный confirmatory test; исключать неудачные дни/кохорты; выдавать синтетические oracle метки за реальные; заменять проверенные отрицательные исходы новыми; копировать raw биржевые файлы в публичный Git; отключать страховочные тесты ради зелёного CI; отправлять реальные торговые заявки; использовать PC-Agent/Computer Use без явного разрешения пользователя для соответствующего действия; запускать дорогие Actions в приватном репозитории.

## 8. Алгоритм работы **каждого** активного запуска и почасового продолжения

1. **READ:** fetch актуальный branch HEAD; прочесть этот план, \`AGENTS.md\`, \`AUTONOMOUS_RESEARCH_TZ.md\`, state, seed registry, master issue #72, issue текущего stage, последние CI. Сверить параллельные коммиты.
2. **DIAGNOSE:** найти наиболее опасную угрозу научной валидности и самый ценный ещё не выполненный test. При необходимости изучить источники в интернете/GitHub и обновить план по секции 7.
3. **FREEZE:** до загрузки/просмотра новых исходных данных записать primary question, cohorts/metrics/threshold/negative controls, seeds и acceptance; зарегистрировать seeds. Не тратить полные новые прогоны ради неопределённой идеи.
4. **EXECUTE:** реализовать code/negative tests, локально или в дешёвом public CI проверить, затем bounded original source run только если действительно полезен; сохранять исходы каждого сценария.
5. **AUDIT:** проверить число независимых наблюдений, side/time semantics, source coverage, leakage/abstain, формат, недостаточную мощность, отрицательные результаты.
6. **COMMIT:** отчёт+fixtures+тесты+план (при необходимости)+checkpoint, commit/push без force; проверить remote SHA, ссылки на точные workflow runs, переключить одноразовый source workflow в manual-only после успеха.
7. **NEXT:** сформулировать следующий лучший stage и его DoD, сразу начать его, пока активный запуск ещё доступен. Не останавливаться после одного зелёного CI/коммита.
8. **RECOVER:** при вынужденном конце — точный checkpoint с \`NEXT_ACTION\`, зависимостями и блокерами. Короткий итог допускается лишь по завершении конкретного запуска; **не утверждать, что агент физически работает между часовыми срабатываниями**.

## 9. Итоговый независимый release gate (закрытие master #72)

Только после независимо выполненных требований:

- [ ] С чистого checkout проходит source-free reproducibility suite, отсутствует необходимость в приватных данных и секретах.
- [ ] Публичные данные и L2 интерпретируются корректно: resting/aggressor, timestamp ties, previous/post-event state, gaps и incomplete depth.
- [ ] На независимых реальных/синтетических источниках пройдены заранее объявленные baseline и hard negative controls; отрицательные результаты явно опубликованы.
- [ ] **Синтетическая** метрика с независимой oracle truth и abstention разделена по сценариям, без утечки agent IDs. Нет ложного claim о real market owner FDR.
- [ ] Источники (original vendor ZIP / simulator source revision), seeds, лицензии и возможность воспроизведения проверены; недоступность отражена.
- [ ] Есть научный отчёт с supported/refuted/inconclusive hypotheses, альтернативами объяснений, ограничениями и аудитом независимости данных.
- [ ] Вывод ограничен тем, что реально доказано: наблюдаемые algorithmic patterns, **не физическое количество реальных роботов**.
- [ ] Последний snapshot issue #72, \`README\`, state и этот документ согласованы; done criteria не снижались задним числом.

**Если критерии недостижимы из-за реальных неразмеченных источников — издать ограниченный научный результат с доказанной границей идентифицируемости, а не фиктивный classifier.**

---

### P0 / RD-SYNTHETIC-HOLDOUT-09 — исходная проверка ЗАВЕРШЕНА

Оригинальный шестнадцатисценарный ABIDES source-эксперимент
[#44936592641](https://github.com/IskanderAbdullin/Analytics/actions/runs/44936592641)
на seeds 3001–3004: 4/4 TWAP обнаружены, 0/4 false
Poisson, 0/4 false fixed-20s, но **2/4 ложных тревог
momentum**, ни одного abstain, 74 oracle-confirmed
исполнения TWAP. Важно: порог ratio=0.60 выбран
после прежних 2901–2903, но до этих новых исходных
сессий. Результат [подробно сохранён](ABIDES_BACKGROUND_RATIO_HOLDOUT_20261121.md),
фальшивые срабатывания не замаскированы. **Не реальная FDR.**

### P0 / RD-MOMENTUM-NEGATIVE-10 — СЛЕДУЮЩИЙ незавершённый этап

[Issue #91](https://github.com/IskanderAbdullin/Analytics/issues/91).
Проверить, не является ли momentum false-alarm из ratio
последствием малого denominator20 и неустойчивого совпадения
по половинам сессии. До новых source runs зафиксировать
независимые seeds, **публичную** метрику consistency по
двум 4-минутным половинам исходной 8-минутной сессии,
правило отсутствия достаточных исполнений (ABSTAIN),
порог, четыре background/target cohorts, базовое
правило ratio>=0.60. Пререгистрация предшествует новым
прогонам. Проводить настоящие ABIDES matching-engine
проверки, сохранить все ложные срабатывания и пропуски,
не делать выводов о реальных владельцах.

### P0 / RD-MOMENTUM-NEGATIVE-10 — исходная проверка завершена

Независимый source experiment [#44937478576](
https://github.com/IskanderAbdullin/Analytics/actions/runs/44937478576):
**3/4 TWAP** обнаружены, **1/4 TWAP abstain**;
во всех трёх отрицательных когортах
**0 ложных тревог, но по 1/4 abstain**.
Исходный цельносессионный baseline на тех же
новых seeds тоже дал 0 ложных тревог, но
4/4 TWAP обнаружений. Split-half gate **не
показал прироста специфичности**, при этом
снизил coverage. Отрицательный результат
и исправление механической ошибки
`absolute timestamp vs exchange local clock`
[зафиксированы](ABIDES_SPLIT_HALF_MOMENTUM_20261121.md).

### P0 / RD-PHASE-ROBUSTNESS-11 — следующий научный приоритет

[Issue #92](https://github.com/IskanderAbdullin/Analytics/issues/92):
зафиксировать независимые проверки
чувствительности временного детектора
к fixed phase shifts, ±250ms краям,
зависимым split fills и группированию
одинаковых timestamps. Не называть разные
фазы одной ленты независимыми источниками,
не использовать частичные исполнения
для вывода о количестве владельцев.

### P0 / RD-PHASE-ROBUSTNESS-11 — source-free завершён

Пререгистрированный по всем пяти фазам синтетический
контрпример [CI #44937958809](https://github.com/IskanderAbdullin/Analytics/actions/runs/44937958809):
при **13 уникальных timestamps** изменение числа
public trade prints с **13 до 112** (100 fills
в одном timestamp вместо одного) подняло
`hits45/hits20` **0,1667 → 8,4167**,
создав ложный clock-grid alarm без target.
После collapse exact timestamp ratio
вернулся к **0,1667**. Сдвиг ±300ms
уничтожил знаменатель: **ABSTAIN**.
Это [отрицательный научный результат](
PUBLIC_PHASE_TIED_FILLS_NEGATIVE_20261121.md),
а не калибровка вероятности на реальной бирже.

### P0 / RD-CONDITIONAL-NULL-12 — следующий научный приоритет

[Issue #93](https://github.com/IskanderAbdullin/Analytics/issues/93):
исследовать условные timestamp-cluster-preserving nulls,
которые сохраняют число и размер кластеров
partial fills и сессионную активность,
и заранее фиксировать временные фазы и
критерии проверки. Нельзя выдавать сами
кластеры за физические parent orders,
случайные фазы одной source tape за
независимые репликации или synthetic
oracle за real-market FDR.

### P0 / RD-CONDITIONAL-NULL-12 — проверен точный synthetic cluster null

[Source-free CI #44938416432](https://github.com/IskanderAbdullin/Analytics/actions/runs/44938416432)
проверил **все 13 возможных** положений 100-fill
кластера при фиксированных 13 уникальных
timestamps и неизменных 112 public prints.
**2/13** naive print-weighted placements дают
ложный alarm (один кластер в grid45-only,
один в grid20∩45), **0/13** grouped timestamp
placements дают alarm. Это
[точный toy-контрпример](PUBLIC_CLUSTER_SIZE_CONDITIONAL_NULL_20261121.md),
а **не FDR, significance и не владелец
реальной заявки**. Offline подтверждение:
**23 набора / 174 source-free tests**.

### P0 / RD-CLUSTER-MARKET-13 — СЛЕДУЮЩИЙ исследовательский этап

[Issue #94](https://github.com/IskanderAbdullin/Analytics/issues/94):
перенести честное сравнение naive per-print
vs grouping identical timestamps на genuine
ABIDES-NG matching engine с Poisson,
fixed cadence, momentum и injected TWAP,
исследовать зависимость false positives,
coverage и агрегатов от кластеризации.
**До новых genuine source runs** отдельно
зафиксировать ещё не израсходованные
locally seeds, исходное окно,
threshold и все когорты.
Не использовать ранее просмотренные
3001–3104 как blind confirmatory данные,
не считать одинаковый timestamp
доказанным единым parent order.

### P0 / RD-CLUSTER-MARKET-13 — подлинный исходный genuine ABIDES перенос ЗАВЕРШЁН

[Оригинальный CI #44938991772](https://github.com/IskanderAbdullin/Analytics/actions/runs/44938991772)
выполнил все **16** заранее зарегистрированных
ABIDES matching-engine прогонов на seeds 3201–3204:
**16 142** public prints, **14 801** уникальных
timestamp групп и 61 подтверждённое posthoc
исполнение TWAP. **Naive per-print**: 4/4 TWAP,
1/4 Poisson false positive, 0/8 false positives
на fixed20/momentum. **Exact timestamp grouping**:
3/4 TWAP (пропуск seed 3204), **та же** 1/4
Poisson false positive, 0/8 fixed20/momentum.
В обоих методах 0 abstentions на этих данных.
Следовательно, **нет доказанной пользы grouped
score**, а один TWAP пропущен. Полные компактные
агрегаты: [документ](ABIDES_PUBLIC_CLUSTER_COMPARISON_20261121.md),
[JSON](../fixtures/abides_clustered_grid_original_20261121.json).
Не настоящая market FDR, не физические владельцы.
Первоначальная workflow больше не запускается
автоматически, чтобы не расходовать Actions повторно.

### P0 / RD-MATCHED-UNCERTAINTY-14 — СЛЕДУЮЩИЙ

[Issue #95](https://github.com/IskanderAbdullin/Analytics/issues/95):
строго парный small-sample аудит 4 seeds×4 cohorts
при исходной синтетической oracle truth.
Нужно отдельно показать итоговые ошибки,
paired decision discordances, интервалы
неопределённости **только по синтетическому
генератору**, подверженность автокорреляции
и невозможность реальной FDR.
Не переобучать порог на уже просмотренных
3201–3204 и не объявлять реальные owner IDs.

### P0 / RD-MATCHED-UNCERTAINTY-14 — ограниченная мощность проверена

[Source-free CI #44943333914](https://github.com/IskanderAbdullin/Analytics/actions/runs/44943333914):
**25 наборов / 190 пройденных тестов**,
исходные 16 synthetic matching-engine cases
сверены с агрегатными source totals.
Для `0/4` nominal exact Clopper–Pearson
95% верхняя граница **0,60236464**,
для `4/4` нижняя **0,39763536**.
Это широкие интервалы при *гипотетических IID
source-seed trials*, **не** реальные
market-owner confidence limits.
Парное сравнение показывает ровно
**один discordant TWAP** (naive обнаружил,
grouped пропустил, seed 3204),
и одинаковый Poisson ложный сигнал
3203. [Полный ретроспективный отчёт](
ABIDES_MATCHED_UNCERTAINTY_20261121.md).
Не выполнено ни одного нового source run.

### P0 / RD-ABIDES-POWER-15 — следующий этап: расширенная мощность

[Issue #96](https://github.com/IskanderAbdullin/Analytics/issues/96):
заморозить новый, более широкий
40-seed × 4-cohort genuine ABIDES
синтетический протокол (160 исходных
matching-engine cases) **перед** запуском,
не изменять старый source-frozen код,
порог 0,60, anchor, допуск ±250мс,
L2/coverage abstention и 4 семьи сценариев.
Только публичные features, oracle IDs
строго после inference, все исходы
и negative controls сохраняются.
Размер source artifacts небольшой;
после единственного успешного Action
перевести workflow в manual-only.
Даже 160 synthetic прогонов не
калибруют real-market FDR.

### RD-ABIDES-POWER-15 — все 160 genuine ABIDES source cases проверены

[Оригинальный исходный run #44944144915](https://github.com/IskanderAbdullin/Analytics/actions/runs/44944144915)
и [повтор #44944168231](https://github.com/IskanderAbdullin/Analytics/actions/runs/44944168231)
имеют **одинаковый** JSON SHA256 `55394e5dfda274613cb081ee4ad44e9b2b8e051eb2e0f0c361e4ee8016431d62`.
Это **160** независимых локальных комбинаций
seed×cohort, **НЕ 320**; source повторные
запуски служат только воспроизводимости.
**156 234 prints / 144 908 timestamps /
253 386 L2**, 617 контролируемых TWAP fills.
По старому замороженному ratio 0,60:
Poisson **7/40** ложных per-print и **6/40**
grouped; momentum **7/40** ложных у обоих;
fixed20 **0/40** ложных и 1 ABSTAIN;
injected TWAP **39/40** naive против **32/40**
grouped (7 дополнительный grouped misses
и один abstain). Описание настоящего
source, все seed-маски и точные CP интервалы
сохранены в [отчёте](ABIDES_160_ORIGINAL_SOURCE_AUDIT_20261121.md),
[долговременном компактном fixture](
../fixtures/abides_grid_160_source_aggregate_reconciled_20261121.json)
и [исходном исходном CI](https://github.com/IskanderAbdullin/Analytics/actions/runs/44944144915).
Оба source workflows manual-only.
Реальные владельцы и market FDR **неизвестны**.

### RD-PUBLIC-CONDITIONAL-NULL-16 — активная следующая научная задача

[Issue #97](https://github.com/IskanderAbdullin/Analytics/issues/97).
Сначала выполнить domain-gap/source-free
adversarial audit: изменения точности clock,
разбиение partial fills, неполнота L2,
непериодический momentum/Poisson null,
non-identifiability нескольких владельцев.
Затем исследовать публичный **period-agnostic**
conditional null с блоками event-rate/
timestamp cluster, previous-completed L2,
сильным abstention. Новый метод, source
seeds и thresholds фиксировать **ДО**
новых исходных симуляций. Старые 3301–3340
нельзя объявлять свежими holdout или
ретроспективно оптимизировать.
Master #72 открытый.

**Результат source-free domain-gap подзадачи [#98](https://github.com/IskanderAbdullin/Analytics/issues/98), без новых seeds:**
отдельно ДО эксперимента заморожена [precision/coverage матрица](../research/public_time_precision_coverage_precommit_20261121.json) из четырёх сконструированных публичных toy-tapes × четырёх разрешений exchange timestamps (1ns/1ms/10ms/100ms) × трёх уровней coverage (4/5/10 prior L2 bins), плюс четыре unknown-precision контроля; итого **52 зависимых наблюдения, 0 новых source samples**.
[Оригинальный дешёвый CI #44945044597](https://github.com/IskanderAbdullin/Analytics/actions/runs/44945044597) **SUCCESS**, 8 дополнительных adversarial tests.
При 100 split prints без target исходное per-print дало TARGET,
grouped — NO TARGET; при девяти sparse 45s событиях оба дали **ложноотрицательное отсутствие сигнала**, несмотря на искусственный cadence.
Из 52 dependent variants: 16 eligible, 16 low-prior-L2 ABSTAIN,
16 coarse-precision ABSTAIN, 4 unknown-precision ABSTAIN.
[Полный source-free отрицательный отчёт](PUBLIC_TIME_PRECISION_COVERAGE_NEGATIVE_20261121.md).
Не принимать выбранный игрушечный 1ms quality gate за проверенную реальную биржевую спецификацию.
Следующий основной шаг — **#97 period-agnostic conditional-null** с новыми prereg-controlled негативными источниками, не перенастраивая 0,60.

## 10. Журнал решений и изменения плана

| Дата | Изменение и причина | Статус |
|---|---|---|
| 2026-11-21 | Создана единая иерархическая дорожная карта из доказанных этапов 01–07 и исследовательских работ 08–14; по негативному genuine ABIDES результату periodic-background false alarms / TWAP misses приоритет отдан public-only multiscale/L2 и hard-negative переносимости | Документированное решение |
| 2026-11-21 | До первого engine-прогона зарезервированы seeds 2901–2903 и начата реализация source-only multiscale/L2 агрегатора с негативными offline tests (source results пока не подтверждены). | IN_PROGRESS; код/QA не являются исходным исследованием |
| 2026-11-21 | До исходного прогона зафиксирована 12-run ABIDES матрица (seeds 2901–2903, четыре сценария, сетки 10/20/45/90s, lagged L2 30/60s); на момент frozen дизайна результаты ещё отсутствовали | FROZEN на момент проектирования, затем проверено оригинальным CI #44935340284 |
| 2026-11-21 | В 12 matching-engine прогонах fixed-20s фон без target дал 45s-grid fraction **0,0820**, выше TWAP **0,0302**. 10s baseline дал 3/3 ложных и 3/3 пропуска. Приоритет скорректирован: сначала модель гармонического aliasing, затем отдельный independent synthetic holdout | REFUTED исходная гипотеза о специфичности, #90 открыт |

| 2026-11-21 | После original negative #44935340284 доказано точное фоновое aliasing 20s→45s (1/9 при нулевом TWAP); создана НОВАЯ ratio-гипотеза из просмотренной выборки с порогом 0,60 и abstention, назначено 16 независимых simulation cases 3001–3004 | source-free negative VERIFIED; ratio = FROZEN до нового исходного прогона, ещё НЕ подтверждено |

| 2026-11-21 | Независимый 16-run source experiment #44936592641: ratio>=0.60 обнаружил 4/4 TWAP, избежал fixed-20s и Poisson ложных тревог (0/8), но дал 2/4 ложных тревог momentum; научный приоритет — независимый тест внутри-сессионной устойчивости без переобучения на 3001–3004 | VERIFIED limited synthetic transfer; hard-negative momentum specificity NOT established; #91 открыт |

| 2026-11-21 | Split-half original 16 case source #44937478576: 3/4 TWAP alarm, 1/4 positive abstain, 0 false alarms in each of three negative cohorts but 1/4 abstain per cohort. Original full-session ratio on same new seeds had 4/4 positives and 0/12 background false positives; split-half no specificity improvement, only coverage loss | Negative scientific result VERIFIED; investigate phase/timestamp-cluster pseudo-replication in #92 |

| 2026-11-21 | Source-free phase/tied-fill counterexample #44937958809: 13 unique timestamps, but 100 fills at a 45s-only timestamp inflate print-weighted ratio 0.1667 → 8.4167 without any target; grouping timestamps reverses false signal; ±300ms shift leads to denominator 0/ABSTAIN | VERIFIED negative measurement artifact; cluster-aware conditional null #93 next |

| 2026-11-21 | 13-placement exact toy conditional null #44938416432: naive print-weighted ratio raised alarm in 2/13 placements of one 100-fill cluster, while timestamp-grouped score was constant and 0/13 alarm. Strong toy exchangeability assumption DOES NOT calibrate market FDR. Next #94 genuine ABIDES cluster-aware control | VERIFIED exact toy-only negative; new real matching-source study NOT_STARTED |

| 2026-11-21 | Genuine ABIDES original CI #44938991772 verified all 16 locally new 3201–3204 seeds; grouped timestamp score yields 3/4 TWAP vs print-based 4/4, Poisson false 1/4 in BOTH, 0/8 fixed/momentum false both. Preserve negative source outcome; paired small-N power audit next #95 | VERIFIED genuine source negative transfer; no real-market FDR |

| 2026-11-21 | Source-free small-N CI #44943333914: exact nominal 95% CP bounds 0/4 upper 0.6024, 4/4 lower 0.3976 conditional on hypothetical IID synthetic seeds; matched same source tapes show one extra grouped TWAP miss and unchanged Poisson FP. No real-market FDR. New 40-seed ×4 source replication frozen before running next | VERIFIED offline statistical audit only; #96 source NOT_RUN |

| 2026-11-21 | RD-MATCHED-UNCERTAINTY-14: additional source-fixture integrity hardening — exact allowlist for top-level/case/cohort/totals, original source and ABIDES revision pins, false-alarm/missed-TWAP conservation; adversarial private-ID/count tampering cases. No new simulations, no new threshold, no increase in claimed confidence. | Implementation committed; cheap CI required for verification |

| 2026-11-21 | PRE-SOURCE уточнение RD-ABIDES-POWER-15: исходный frozen 40×4 протокол оставлен неизменным; [отдельное addendum](../research/abides_160_zero_execution_oracle_handling_addendum_20261121.json) предотвращает отбрасывание source-сценариев, где injected TWAP агент не получил ни одного фактического исполнения; сохраняются все 160 seed×cohort, отдельно считаются zero-execution positives. Не считать их подтверждёнными публично наблюдаемыми execution patterns, не менять seed/порог/фазу и не включать oracle в public scoring. | PRE-SOURCE methodological guard; original 160 engine runs not yet verified |

| 2026-11-21 | Frozen 40-seed × 4-cohort original genuine ABIDES #44944144915 and exact replay #44944168231 (same source SHA, not 320 independent): per-print FP Poisson 7/40, momentum 7/40; grouped FP Poisson 6/40, momentum 7/40; injected TWAP per-print 39/40, grouped 32/40 (7 additional misses), fixed20/TWAP 1 abstain each. Pivot to period-agnostic conditional null #97 | VERIFIED source negative result, no real market FDR |

| 2026-11-21 | Separate preregistered **source-free** #98 precision+lagged-L2 control: 4 constructed public tapes × 4 nested timestamp resolutions × 3 synthetic coverage gates + 4 unknown-precision controls = 52 **dependent views** (0 new engine/market sources). CI #44945044597 GREEN, 8 adversarial tests; split-print null gave naive TARGET/grouped NO, but sparse synthetic 45s cadence was missed by BOTH. 16/52 views were numerically eligible, 36/52 required quality ABSTAIN. No owner/FDR claims; maintain primary #97 period-agnostic null. | VERIFIED source-free falsification and coverage guard, no new holdout |

| 2026-11-22 | Constructed 64×3 A/B/C hard-negative panel exposes C's failure to preserve 168 momentum burst gaps (17–34 resampled), while B preserves them mechanically. Existing green CI did NOT discover these new tests; explicit source-free test discovery and report CLI added to provenance workflow. | NEGATIVE SOURCE-FREE DEVELOPMENT; new CI PENDING, no market p-value/FDR |

| 2026-11-22 | Preregistered issue #97 paired 500ms occupancy-equivalence tapes; C's conditional resamples collapse different local gap structures (6 vs 0 observed) by construction, B is gap-preserving by construction; 10ms quantization erases dense short-gap evidence. Prior exact CI #44995874723 confirmed 38 source-free tests; new 4 exact tests CI pending. | Source-free identifiability limit, not statistical calibration |

| 2026-11-22 | Preregistered L2 ambiguity/tied-snapshot counterexamples (#97 comment 7075629666), conservatively block fallback to older covered L2 after a newer overlapping-precision sample; resolve input-order-dependent same-time conflicting coverage with deterministic ABSTAIN. Frozen thresholds untouched. | Source-free regression; new CI pending |

| 2026-11-22 | After registering #97 comment 7075657012, added optional conservative C quality wrapper: 1ms declared print precision plus strict previous-only public L2 needed before source-free sampling; all missing, coarse, ambiguous or private-field examples fail closed. No frozen candidate C parameters changed. | Engineering source-free diagnostic; exact new CI pending |

| 2026-11-22 | Added prospectively described D 10ms microburst-block relocation (#97 comment 7075675938), preserving short gaps but allowing greater between-burst timing support than B; D exactly conserves <=10ms gap count in Poisson/momentum/periodic constructed controls, so that statistic has no inferential power under D. | Technical source-free method development only; CI pending |

| 2026-11-22 | Identified v1 seven-period scan zero-harmonic bug: any 1–50ms gap matches all fixed 5–60s periods; froze distinct v2 that requires positive integer harmonic k>=1 and retained v1 historical code. Non-target 20s periodic still aliases 5/10/20s in v2. | Source-free methodological correction, v2 exact CI pending |

| 2026-11-22 | Predeclared all-period v2 A/B/C/D constructed non-target controls (#97 comment 7075711877): periodic20s no-target 5/5 observed at 5/10/20s; momentum23/191 5s hits. A/B/C/D can dilute both without any exchangeability proof. | Source-free hard-negative, new exact CI pending |

**Правило:** каждый существенный методологический поворот дополняет эту таблицу. Не переписывать историю, не удалять неожиданные отрицательные выводы и не называть собственное предположение полученным результатом.


### RD-CLUSTER-MARKET-13 — source execution verification checkpoint (2026-11-21)

Commit [`902fdeb`](https://github.com/IskanderAbdullin/Analytics/commit/902fdeb30e1548ab3722aa97718947cd9a9468fd) adds a **precommitted** original ABIDES 16-case source workflow for local seeds 3201–3204, four cohorts, threshold 0.60 and minimum 8 hits20. At this checkpoint the two observed HEAD workflow runs [44938997233](https://github.com/IskanderAbdullin/Analytics/actions/runs/44938997233) and [44938997239](https://github.com/IskanderAbdullin/Analytics/actions/runs/44938997239) passed provenance/.NET checks, **not** the new original ABIDES 16-case job. Therefore **no original source results or negative-control outcomes are yet verified**. Next action: execute the already-frozen original source workflow once, collect the short aggregate-only artifact, account for all 16 cases and abstentions, and only then update the scientific conclusion. Do not alter frozen seeds or threshold to fit outcomes.


### RD-PUBLIC-CONDITIONAL-NULL-16 — public-only invariance regression (2026-11-21)

Added `tests/test_public_cluster_invariance_20261121.py`: six deterministic adversarial checks covering split-fill multiplicity versus unique-timestamp interarrival, no inference of parent/owner from public cadence, strict public field allowlist, exclusion of same-time/future L2 from lagged coverage, and a fixed-cadence non-target counterexample. These are **constructed source-free tests**, not empirical evidence of specificity, independent ABIDES holdout, p-values or real-market FDR. An exact timestamp cluster is an observable grouping, **not** a proven parent order. No thresholds, frozen protocols or spent seeds changed. NEXT_ACTION: execute test discovery/cheap CI, investigate any failures, then implement preregistered occupancy/cluster-preserving conditional randomization with full phase/period enumeration and abstention before new source simulation.


### 2026-11-21 — RD-PUBLIC-CONDITIONAL-NULL-16 identifiability decision

[Source-free pre-analysis measurement gate](PUBLIC_CONDITIONAL_NULL_IDENTIFIABILITY_20261121.md): preserving **exact public timestamp positions** while permuting complete split-fill cluster sizes cannot calibrate interarrival cadence: the interval vector is unchanged by construction. Reject this null for timing p-values; retain only as a split-fill robustness check. A prespecified descriptive seven-period scan and a distinct, as-yet-unvalidated timing-resampling family are documented. No new ABIDES seeds, no source tests, no real-market FDR. NEXT_ACTION: implement period scan and adversarial controls, then prove or explicitly limit timing-null exchangeability before any new source run.


### 2026-11-21 — RD-PUBLIC-CONDITIONAL-NULL-16 seven-period implementation checkpoint

Added `tools/public_period_scan.py` and `tests_background/test_public_period_scan.py` for the **already preregistered** {5,10,15,20,30,45,60}s, ±50ms, unique-timestamp consecutive-gap descriptive scan. Every period is reported, no best-only selection, no oracle or owner ID, and no inferential p-value. Seven constructed adversarial checks cover split-fill invariance, unrelated fixed-cadence hard negative, zero-gap abstention, tolerance, invalid inputs and minute occupancy. Seven analogous scratch tests passed locally; **committed version has not yet been confirmed by GitHub CI**. Separate observed provenance CI #44950270121 failed at previous SHA because state.current_stage.status used unsupported ACTIVE_METHOD_DEVELOPMENT; fixed checkpoint status to IN_PROGRESS without weakening validator. No new ABIDES source runs or independent holdout. NEXT_ACTION: verify provenance and new scan tests on GitHub CI, add previous-only L2 coverage gating and a burst-preserving timing-null falsification suite before any statistical significance claims.

| 2026-11-21 | Preregistered descriptive seven-period scan implemented, with seven adversarial source-free tests; previous provenance failure was invalid checkpoint status, corrected to IN_PROGRESS. No new source data, p-values, FDR or owner labels. | Implementation pushed; CI verification pending |


### 2026-11-22 — RD-PUBLIC-CONDITIONAL-NULL-16 previous-only L2 gate (source-free)

Added `tools/public_period_l2_gate.py` and `tests_background/test_public_period_l2_gate.py`: a strictly prior-only descriptive scan eligibility gate. **Prespecified engineering rule:** a public L2 sample at time `s` is eligible for print `t` only if `s + source_precision_ms < t` and `t-s <= 1000 ms`, with explicit `covered=True`; use latest eligible snapshot. Exact public-field allowlist rejects private IDs and missing precision. Any print lacking eligible coverage causes full descriptive-score ABSTAIN; exchange-wide completeness remains UNKNOWN. Eight constructed negative/unit cases include same/future timestamps, precision overlap, stale samples, missing coverage, private fields, split fills, and no gaps. This is a **conservative local causal quality filter**, not a calibrated timing null, source validation, market FDR or robot-owner inference. It can abstain on otherwise useful feeds and must not be interpreted as proving complete historical book coverage. NEXT_ACTION: confirm committed test discovery/CI, correct failures, then preregister burst-preserving timing-null assumptions and falsification controls without p-values before fresh source runs.


### 2026-11-22 — conditional timing-null preregistration (method development)

After confirming three successful GitHub workflow runs on `b2c461b8`, froze a **source-free, unvalidated** candidate in [BURST_PRESERVING_TIMING_NULL_PREREG_20261122.md](BURST_PRESERVING_TIMING_NULL_PREREG_20261122.md). The proposal conditions on counts per prespecified 5-second cell and retains complete exact-timestamp split-fill clusters; event times are resampled within their cells. This is only a falsifiable working model, **not** an established market exchangeability assumption or a valid p-value. Explicit hard negatives include unrelated periodic actors, self-exciting bursts, identical public tapes with different private owners, and incomplete L2. No new seeds, source simulations, FDR or owner inference. NEXT_ACTION: implement deterministic sampler and invariance/falsification tests, then compare a relative-offset-preserving alternative without posthoc selection.


### 2026-11-22 — conditional sampler source-free implementation checkpoint

Implemented `tools/public_conditional_timing_null.py` with deterministic seeded within-5s-cell millisecond sampling and `tests_background/test_public_conditional_timing_null.py` with six constructed checks (occupancy, split-fill invariance, reproducibility, interval change, invalid inputs, non-target periodic hard negative). The sampler returns no p-value and **does not preserve within-cell autocorrelation or prove exchangeability**; tests are not independent market evidence. At this checkpoint committed test execution/CI remains **unverified**. NEXT_ACTION: execute the committed six tests in GitHub CI; add self-exciting within-cell falsification and cluster-size-vector preservation to the sampler; do not infer owners or market FDR.


### 2026-11-22 — cluster-multiplicity-preserving diagnostic (method development, not validation)
Implemented `conditional_cluster_sample` on top of the predeclared 5-second timestamp-cell sampler. Each exact-time public print cluster remains intact, with its multiplicity attached by original within-cell event rank; counts and cluster-size vectors per cell are preserved. Added adversarial tests for preservation, deterministic cell boundaries, and invalid timestamps. This is a technical invariance change only: within-cell exchangeability remains unvalidated, Hawkes/self-exciting bursts remain an obligatory falsification case, and no p-values, owner attribution, real-market FDR, fresh source seeds, or new ABIDES evidence are claimed. CI for the new tests must be verified before marking them passed.

NEXT_ACTION: confirm latest-HEAD cheap CI and the two new tests; build an explicit constructed self-exciting clustered-burst falsification against the uniform-within-cell sampler and compare a within-cell-offset-preserving alternative. Keep issue #72 open.


### 2026-11-22 — constructed burst exchangeability falsification (source-free)

Added `tools/public_burst_null_falsification.py` and `tests_background/test_public_burst_null_falsification.py` after preregistration in `BURST_PRESERVING_TIMING_NULL_PREREG_20261122.md`. The fixed constructed negative has six 5-second cells, eight consecutive millisecond event times per cell, and three extra simultaneous split-fill prints per cell. The preregistered uniform-within-cell sampler is compared over 64 deterministic replicate indices against a restricted offset-preserving comparator. The diagnostic counts adjacent unique event gaps <=10ms within each cell (42 constructed gaps). Uniform timing destroys local bursts; the offset-preserving translation retains all within-cell gaps by construction and is therefore low-power for distinguishing genuine bursts from unrelated bursts. **Neither procedure establishes real market exchangeability or calibrated p-values**. Four adversarial tests added; execution of the committed tests and latest CI is pending verification. No ABIDES source runs, fresh seeds, owner labels or FDR claims. NEXT_ACTION: verify latest-HEAD CI and execute the four tests; repair failures, document empirical deterministic counts, then investigate an intensity-conditioned model with an independent prospective protocol and strong momentum/Poisson controls.


### 2026-11-22 — RD-PUBLIC-CONDITIONAL-NULL-16: chronological input regression fixed

Executing a local source-equivalent reproduction of the four constructed burst adversarial tests exposed a real failure: `constructed_burst_falsification` appended three duplicate first-timestamp split fills *after* the eight ordered event timestamps per cell. The strict public conditional sampler correctly rejected this unsorted tape (`ValueError`). This is a fixture construction defect, **not** evidence against the sampler's validation guard. Fixed by sorting the constructed tape before sampling; did **not** relax sorted-input validation. Four locally reconstructed tests now pass (4/4); deterministic constructed diagnostic: 42 observed within-cell gaps <=10ms, uniform 64-replicate range 0..2, offset-preserving range 42..42. The local reconstruction is not a byte-for-byte test of checked-out repository files; GitHub CI must independently verify commit `4bb39917`. No market p-value, exchangeability proof, fresh ABIDES source seeds, or real-market FDR. NEXT_ACTION: verify new-HEAD CI and exact committed test discovery, then freeze intensity-conditioned null and Poisson/momentum negative controls before implementation.


### 2026-11-22 — prospective intensity-stratified timing-null protocol frozen before implementation

[INTENSITY_CONDITIONED_NULL_PREREG_20261122.md](INTENSITY_CONDITIONED_NULL_PREREG_20261122.md) freezes a new **source-free** 500ms-subcell conditional resampling candidate with full 5s/500ms occupancy and exact-timestamp split-fill multiplicity preservation, deterministic seed 404 and 64 replicate indices. Comparison against original uniform 5s and rigid offset-preserving diagnostics, Poisson/momentum/burst/unrelated-periodic hard negatives, and no-lookahead/precision abstention are all prescribed **before** implementation. This is explicitly not an exchangeability proof or calibrated p-value. Prior 3301–3340 genuine ABIDES cases remain spent. NEXT_ACTION: implement C and tests; verify exact new-HEAD CI and preserve all negative outcomes. No new market data or simulation run.


### 2026-11-22 — intensity-conditioned candidate C implementation (source-free, not calibrated)

Implemented `tools/public_intensity_conditioned_null.py` from the frozen [INTENSITY_CONDITIONED_NULL_PREREG_20261122.md](INTENSITY_CONDITIONED_NULL_PREREG_20261122.md): resampling unique millisecond slots without replacement within fixed UTC 500ms subcells, preserving original exact-time split-fill multiplicities by chronological rank, 5s and 500ms unique occupancy, and deterministic `rd-intensity-500ms-v1:404:{replicate}` seeds. Five adversarial tests cover 64-replicate occupancy/multiplicity, deterministic replay, invalid timestamp/seed rejection, UTC boundaries, and a constructed burst diagnostic. **Implementation and tests are not scientific calibration**; execution/CI is pending. Poisson, momentum and unrelated periodic hard-negative comparisons remain required, as does source/precision/L2 coverage audit. No new ABIDES or real-market source runs; no p-values, physical owner counts or real-market FDR. NEXT_ACTION: verify CI and execute committed tests, add the remaining preregistered hard negatives, record all outcomes without retuning 500ms width.


### 2026-11-22 — constructed hard-negative A/B/C comparison committed (pending CI)

Added `tests_background/test_public_abc_constructed_controls.py` on branch commit `7af347b168898ca705d5c8ce088aa1b4bb4d864f`. The frozen, source-free development panel includes quantized exponential-gap Poisson-like events, eight-event momentum-like millisecond bursts in 24 fixed five-second cells, and unrelated 20-second periodic events. Each is evaluated with **all** 64 deterministic replicate indices (seed 404) against A: uniform 5s cluster-preserving resampling, B: rigid within-cell offset-preserving translation, and C: intensity-conditioned 500ms cluster-preserving resampling. Descriptive metric: adjacent unique timestamp gaps <=10ms, with min/max/mean and all replicate values; no selective best candidate or market p-values. Three new adversarial tests check scenario coverage, reproducibility, cluster multiplicities, and explicit non-target burst classification. The Poisson-like generator is constructed and quantized, **not** a fitted real-market Poisson process; momentum-like bursts are constructed and not an estimated Hawkes process. The 20s control has no injected target. No real owner truth or market FDR, no new ABIDES simulations, no fresh source seeds. CI/exact committed test execution remains to be verified before interpreting empirical counts. NEXT_ACTION: verify exact new HEAD CI/test discovery, capture all A/B/C numeric outcomes, diagnose failures without silently retuning preregistered parameters; then test local-intensity confounding and source-precision abstentions.


### 2026-11-22 — A/B/C descriptive hard-negative panel and missing-CI-coverage correction

The exact HEAD \`87b0363690f7517b2e7be77b3486dc91c66be01d\` had five
successful GitHub workflows, **but their existing Python provenance job did
not discover the newly committed A/B/C tests**. A green unrelated workflow
is therefore not evidence those tests ran. Source-equivalent local Python
reproduction (no Git checkout) ran the three constructed-control tests
and three new aggregate-report tests (6/6 PASS); see
[ABC_CONSTRUCTED_CONTROLS_RESULTS_20261122.md](ABC_CONSTRUCTED_CONTROLS_RESULTS_20261122.md)
for the full scenario comparison and limitations. The constructed momentum
hard negative has 168 adjacent <=10ms gaps, while candidate C's 64
500ms-stratified resamples have 17–34 and A's have 0–7; B preserves
168 by construction. On a quantized Poisson-like control, observed 186
vs A mean 184.0625, C mean 185.453125; unrelated periodic 20s yields zero
short-gap counts for all candidates. These are **negative methodological
diagnostics, not p-values, calibration, independent simulation cases, owner
truth or real FDR**.

One atomic engineering change adds explicit cheap Python current-stage
test discovery, complete aggregate JSON report generation and three new
report-integrity tests to the existing provenance workflow. The workflow
is NOT an original ABIDES source run and the existing expensive source
frozen protocols remain unchanged. CI for the new commit is **PENDING**
until an exact HEAD run is inspected.

NEXT_ACTION: confirm the exact committed GitHub CI test output and bounded
artifact, investigate any failures without rewriting the registered 500ms
condition, then test predeclared intensity/autocorrelation confounding and
prior-only L2 precision abstention.

### 2026-11-22 — frozen paired 500ms-equivalence falsification (source-free)

Before implementing a new negative test, [issue #97 prereg comment](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075610380)
froze two 8-event public timestamp tapes with identical 500ms occupancy/rank
multiplicities but different <=10ms gap structure: dense 6 and dispersed 0.
Candidate C necessarily samples identical conditional timestamp tapes from both
for the same seed and replicate, by its original code construction; A does too.
B trivially retains the distinct gaps by rigid translation. Quantizing the
dense tape to 10ms erases six short unique gaps, underscoring why source
precision must be treated as a quality/abstention gate. See
[INTENSITY_CONDITIONAL_EQUIVALENCE_CLASS_NEGATIVE_20261122.md](INTENSITY_CONDITIONAL_EQUIVALENCE_CLASS_NEGATIVE_20261122.md).
Four preregistered adversarial cases passed on source-equivalent transcribed
local code (4/4), **not yet exact GitHub committed tests**. The existing
[provenance CI #44995874723](https://github.com/IskanderAbdullin/Analytics/actions/runs/44995874723)
verified **38** explicit current-stage tests on the preceding SHA
\`6505dbed\`, including the A/B/C full 64-replicate aggregate report and
3-day artifact; this is technical source-free execution, not calibration.
The new four tests are added to the same cheap provenance workflow;
CI for this next SHA is PENDING.

NEXT_ACTION: verify exact-HEAD new 4 tests and inspect CI; then design
a dependence-preserving but non-degenerate prospective comparison
without source/threshold retuning or real-market FDR claims.

### 2026-11-22 — strict previous-only L2 causal ambiguity guard (source-free)

[Pre-test frozen issue #97 comment](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075629666)
records two causal quality threats in \`public_period_l2_gate.py\`: a
known newer quote overlapping a public print under recorded timestamp
precision could be ignored in favour of an older covered quote; and
conflicting same-time L2 coverage samples had input-order-dependent
selection. The conservative fail-closed implementation adds
\`AMBIGUOUS_NEWER_L2_ORDER\` and
\`CONFLICTING_TIED_L2_SNAPSHOTS\`, with four new adversarial controls.
No change to 1000ms age, previous-only test or source allowlist.
The old eight tests and new four passed 12/12 on locally transcribed
source-equivalent code, **not yet on exact committed checkout**.
[Negative finding & fixtures](PREVIOUS_L2_AMBIGUITY_NEGATIVE_20261122.md).
Prior exact provenance CI #44996020719 independently verified all
**42** source-free current-stage tests including the paired 500ms
equivalence-class negative (4 tests). The new four tests now require
separate exact-HEAD CI. This does not validate external market
completeness, owner count, market FDR or timing-null p-values.

NEXT_ACTION: verify new four causal L2 regression tests in cheap CI,
then register stronger input completeness/precision missingness
abstention scenarios before any new synthetic or real source run.

### 2026-11-22 — conservative precision/L2 source-free quality wrapper for C

Following [pretest issue #97 comment](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075657012),
added a distinct optional \`quality_gated_intensity_sample\` wrapper that
returns no C samples without declared 1ms print precision, >=2 unique
public timestamps and strictly previous locally eligible L2. The 1ms
requirement is a conservative **toy diagnostic precondition**, not a
verified exchange spec or calibration. Unknown/coarse precision or
newer ambiguous coverage now ABSTAIN; private/oracle input fields fail
closed. This leaves the original frozen A/B/C models, 500ms width,
seed 404 and 64 replicate indices unchanged.
[Methods/negative results](INTENSITY_QUALITY_ABSTENTION_20261122.md).
Four source-equivalent locally recreated tests PASS (4/4);
exact new-HEAD GitHub CI remains pending. The earlier causal-L2 patch
has 4 new exact tests verified by
[provenance CI #44996216864](https://github.com/IskanderAbdullin/Analytics/actions/runs/44996216864),
plus its existing 8 prior-L2 checks: 12/12. These are technical
quality checks, not proof of real exchange completeness or p-values.

NEXT_ACTION: confirm four new wrapper tests by exact CI and prevent
label-leak/coverage assumptions; then freeze a more informative
dependence-preserving null comparison before adding more source data.

### 2026-11-22 — source-free candidate D, microburst-block relocation

[Preregistered exploratory implementation comment](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075675938)
freezes a *new* D sensitivity comparator. In every 5s UTC cell,
consecutive timestamp groups separated by <=10ms are joined into
ordered microburst blocks. Each block retains exact intra-block offsets
and split-fill multiplicities, while random weak compositions of slack
relocate the between-block intervals without merging blocks. The two
synthetic 8-event bursts retain 14 adjacent <=10ms gaps; B's interburst
boundary remains fixed at 1993ms, D's varies across 64 replicates.
On already inspected A/B/C constructed controls, D preserves the
short-gap statistic exactly (Poisson-like 186, momentum-like 168,
unrelated periodic 0) in every replicate, a **negative falsification
of D's usefulness for calibrating that statistic**.
See [MICROBURST_BLOCK_TIMING_NULL_NEGATIVE_20261122.md](MICROBURST_BLOCK_TIMING_NULL_NEGATIVE_20261122.md).
Four constructed source-equivalent tests locally PASS (4/4);
exact committed CI pending. Separate previous
[provenance CI #44996367981](https://github.com/IskanderAbdullin/Analytics/actions/runs/44996367981)
confirmed four new precision/prior-L2-wrapper tests on the preceding
SHA; this is technical, not source-validation of real timestamp
accuracy. No new ABIDES or market source data, no p-values, owner
labels or real market FDR.

NEXT_ACTION: verify exact latest D CI, then predeclare separate
long-period statistic and fixed periodic hard-negative family
to audit whether D's extra support has useful identification limits.

### 2026-11-22 — mathematical zero-harmonic defect in original seven-period scan

[Pretest issue #97 record](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075694957)
proves old \`public_period_scan.py\` treated 1ms adjacent gaps as
5/10/15/20/30/45/60s cadence hits because its modulus rule allows
the \`k=0\` multiple. Three consecutive 1ms gaps therefore produce
**3/3 false “periodicity”** under every original v1 period.
Without modifying the previously frozen v1, new explicit
\`scan_positive_harmonics_v2\` requires \`k>=1\` and yields
**0/3** for all periods on the same source-free input. It keeps all
seven fixed periods and ±50ms tolerance; there is no favorable-period
selection. Crucially, unrelated 20s fixed background still yields
**5/5** hits for 5,10,20s under v2 (positive harmonic alias),
so this is a measurement correction, **not** owner identification
or a calibrated inference method.
[Detailed negative v1/v2 record](PERIOD_ZERO_HARMONIC_V2_NEGATIVE_20261122.md).
Five preregistered source-equivalent tests pass locally (5/5);
exact new SHA CI pending. The preceding
[provenance CI #44996522344](https://github.com/IskanderAbdullin/Analytics/actions/runs/44996522344)
verified four D microburst-block tests and the previous 50 tests.
No new original ABIDES runs, source holdouts or real-market claims.

NEXT_ACTION: verify committed five v2 tests. Then compare frozen v2
all-period responses on the already-seen independent *constructed*
A/B/C/D hard negatives, emphasizing v2's residual positive-harmonic
false identification on unrelated periodic backgrounds; preserve all
negative results, no market p-values.

### 2026-11-22 — complete positive-harmonic A/B/C/D non-target panel

Source-free constructed 3×4×7×64 comparison frozen in
[issue #97 comment 7075711877](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075711877)
before viewing the new v2×D outcomes. All samples are
previously inspected, NOT new independent source data.
[Full negative panel](ALLPERIOD_V2_ABCD_NEGATIVES_20261122.md):
non-target momentum-like burst stream yields **23/191**
5s hits; unrelated periodic20s stream yields **5/5**
at 5s/10s/20s, despite zero injected target.
Sampled 5s means for periodic non-target A/B/C/D:
0.109375 / 0.125 / 0.796875 / 0.078125,
versus observed 5. Randomization-induced apparent anomaly
would be misleading without real source exchangeability.
Poisson-like v2 scored zero observed/all samples.
All 64 values for every candidate and period are preserved
by the aggregate-only CLI; no cherry-picking.
Three new source-equivalent integrity tests PASS locally
(3/3), exact HEAD CI PENDING. Previous
[CI #44996649423](https://github.com/IskanderAbdullin/Analytics/actions/runs/44996649423)
confirmed five v2 tests. No p-values, real FDR,
ownership or new ABIDES sources.

NEXT_ACTION: confirm exact current CI/aggregate artifact;
then register a scientifically independent new synthetic
source or derive and falsify exchangeability conditions.

**CI engineering correction (no experimental changes):** Exact
provenance runs [#44996834864](https://github.com/IskanderAbdullin/Analytics/actions/runs/44996834864)
and #44996830341 FAILED after all **three new report unit
tests passed**: the direct CLI \`python tools/public_allperiod_abcd_report.py\`
lacked the project ROOT on \`sys.path\`; importing
\`tools.public_period_positive_harmonics_v2\` raised
\`ModuleNotFoundError: No module named 'tools'\`.
No changes to frozen seeds, data, 7 periods, tolerances or observed
negative outcomes were made. Corrected CLI path bootstrap using
\`sys.path.insert(0,str(ROOT))\`, and executed direct CLI locally
without PYTHONPATH to validate. Exact corrected GitHub CI PENDING.



### 2026-11-22 — prospective conditional-intensity design (new protocol; no data evaluated)

[Preregistration](CONDITIONAL_INTENSITY_PREREG_20261122.md) specifies a public unique-timestamp-cluster conditional-intensity rescaling diagnostic with strictly previous-only L2, exposure gaps, fail-closed abstentions and eight mandatory adversarial cases. M0 activity baseline, M1 causal L2, and M2 self-excitation are competing hypotheses, not validated detectors. Original 3301–3340 remain spent; no new holdout or p-values. Corrected HEAD 8fd4590a CI five workflows successful; this addition is design-only and requires implementation/tests. NEXT_ACTION: implement rescaling core and negative controls, then freeze truly independent source allocation before evaluation.


### 2026-11-22 — fail-closed conditional-intensity rescaling prototype

Implemented `tools/public_intensity_rescaling.py` with public unique-cluster timestamps, piecewise externally fixed nonnegative causal rates, complete exposure tiling and explicit abstention on missing/overlapping/noncausal/zero-intensity input. Added `tests/test_public_intensity_rescaling.py` (12 source-free negative/unit cases). A locally transcribed source-equivalent implementation passed 11/11 before commit; exact GitHub test run still pending. This does **not** fit M0/M1/M2, validate model exchangeability, establish p-values, detect actors or calibrate real-market FDR. NEXT_ACTION: verify exact CI, integrate strict precision and previous-only L2 gates, then freeze independent training/evaluation allocation.


### 2026-11-22 — public input eligibility gate, prospective engineering checkpoint

The prior rescaling prototype's exact HEAD d30c8bb6 completed three successful GitHub workflows (provenance, ABIDES integration and .NET CI); this is **not evidence that the new Python unit tests ran**. Added strict source-record allowlists (no agent_id/private_truth), a declared <=1ms integer timestamp-resolution requirement, and strictly earlier complete L2 snapshot eligibility before rescaling. This rejects co-timestamp/future L2, incomplete prior coverage, invalid precision and extra fields; it does **not** verify that a real vendor clock actually has 1ms resolution or that book capture is truly complete. Nine adversarial source-free unit tests added, exact new-HEAD CI and test execution pending. No fresh ABIDES source, holdout, calibration or real FDR. NEXT_ACTION: execute the exact new Python tests in cheap CI; if green, preregister train/calibration/independent market-run partitions and predictable M0/M1/M2 fitting with time-causal features before allocating any new seeds.


### 2026-11-22 — exact-source Python CI gate and independent allocation design

Added lightweight public-branch-only `.github/workflows/robot-detector-public-intensity.yml` to execute the exact checked-out `tests/test_public_intensity_rescaling.py` without vendor data, secrets or expensive ABIDES. Found a concrete fail-open engineering case: a nonnumeric or boolean hazard could raise an uncontrolled Python exception or be treated as a numeric intensity. Updated `tools/public_intensity_rescaling.py` to reject non-(int,float) hazards, and added two source-free adversarial test methods (including negative rates). This is a defensive fix, not evidence of scientific calibration. Exact new HEAD GitHub CI must still be checked; no unverified test success is claimed.

Prospective [independent allocation/falsification gate](CONDITIONAL_INTENSITY_ALLOCATION_GATE_20261122.md) records independent run-level train/calibration/evaluation partition, M0/M1/M2 design requirements, public-feature/oracle separation, source rights and hard negatives. It explicitly blocks fresh source seeds until hyperparameters and independent run allocation are frozen. No source data or holdout was consumed. Previous 3301–3340 remain spent.

NEXT_ACTION: confirm exact source-free Python workflow and correct any failures; finish deterministic causal feature/fitting spec and adversarial controls before independent source registration. Preserve issue #97 and master #72 open.


### 2026-11-22: conditional intensity exposure quality gate (source-free)

Independent audit found that `Exposure.complete` and `Exposure.causal` accepted truthy non-boolean values (e.g. integer `1` or string `yes`). These are provenance/causality assertions and must be exactly Python booleans; otherwise the pipeline must ABSTAIN. A regression covering malformed flags is added before any new source run. This is a technical integrity fix, **not** evidence for M0/M1/M2 validity, calibrated significance, real-market FDR, or owner identification. Next: exact-source Python CI, then preregister and implement causal train-only model-fitting with prospective independent run-level split.


### 2026-11-22 — prospective train-only M0 public cluster intensity baseline

Before implementation, frozen [M0 protocol](CONDITIONAL_M0_TRAIN_ONLY_PREREG_20261122.md) defined the exposure denominator, unique-timestamp cluster counting, training-only estimation, explicit run-level split responsibility and nine adversarial checks. New `tools/public_m0_train_only.py` fits constant M0 hazard from declared training runs only and emits a fixed `Exposure` for evaluation without accepting evaluation event counts. `tests/test_public_m0_train_only.py` adds nine source-free tests, including split-fill multiplicity, pooled exposure, no-training, zero counts, malformed windows, unsorted/out-of-window timestamps, boolean/fractional times, evaluation-window invariance and invalid model. Lightweight Python CI workflow now discovers both public-intensity and M0 tests. **These tests are authored, not yet confirmed green on new HEAD.** No source data, new ABIDES seeds, calibration, p-values or real owner/FDR inference. M0 is a falsifiable baseline, not a detector.

NEXT_ACTION: confirm exact-source CI and repair failures; preregister M1 strictly previous-only L2 and M2 predictable self-excitation with run-disjoint fitting and mandatory hard negatives before allocating independent source seeds. All 3301–3340 remain spent.


### 2026-11-22 — prospective M1 lagged-L2 design (no evaluation)

A second independent design stage freezes [M1 lagged-L2 preregistration](CONDITIONAL_M1_LAGGED_L2_PREREG_20261122.md): strict previous-only complete BBO, training-only median relative-spread threshold, low/high strata rates based on fully observed exposure, fail-closed staleness/clock/coverage and missing-stratum conditions, and hard negatives including unrelated periodic backgrounds and momentum. This is design-only; M1 has **not** been implemented or tested. No new ABIDES seeds or market data, no calibration or actor/FDR claims. Exact-source M0 Python CI remains to be confirmed.

NEXT_ACTION: confirm M0 CI; implement causal M1 exposure construction with strict complete prior L2 and training-only spread threshold, then source-free negative tests before new source allocation.


### 2026-11-22 — prospective conservative M1 train-only implementation (source-free, CI pending)

[Preimplementation frozen addendum](CONDITIONAL_M1_SOURCE_FREE_IMPLEMENTATION_GATE_20261122.md) at commit `f3d78068` specifies narrow one-stable-prior-BBO-per-run windows (1ms precision, max 1000ms age, asserted coverage, no in-window change) rather than pretending arbitrary L2 sequences have complete causal exposure. Added `tools/public_m1_train_only.py` (training-run-only median relative-spread split, one cluster per unique timestamp, positive exposure/rate both strata, disjoint evaluation run ID and fail-closed strict BBO allowlist), plus `tests/test_public_m1_train_only.py` with 12 adversarial/positive source-free tests. Local standalone source-equivalent run (minimal imported `Abstain/Exposure` stub) passed 12/12; exact committed full-project CI **NOT YET VERIFIED**. No data, simulator seeds, calibration, p-values, owner count or real-market FDR. The stable-window restriction is a strong coverage limitation; dynamic book changes must ABSTAIN until a separately preregistered causal segmentation upgrade. NEXT_ACTION: verify exact M1 Python CI output, repair without retuning frozen gates, then preregister M2 predictable self-excitation and independent run-level allocation before fresh source seeds.


### 2026-11-22 — exact M1 Python CI and AGENTS migration regression (engineering evidence)

[Exact public Python CI #45024195498](https://github.com/IskanderAbdullin/Analytics/actions/runs/45024195498) on SHA `0f3728e1` PASS **51/51**, including **12 new M1** source-free unit/negative tests. This tests a narrow asserted stable-BBO window baseline, not real exchange completeness, new ABIDES data, M1 statistical calibration, p-values or FDR. A separate [provenance CI #45023898399](https://github.com/IskanderAbdullin/Analytics/actions/runs/45023898399) FAILED on migration HEAD `83d9be1c`: historical `test_master_research_plan.py` requires explicit autonomous/decision-log keywords in active AGENTS after its short-map replacement. All preceding source-free research suites in that run passed. The active AGENTS is amended to restore the autonomous, self-directed, negative-evidence and decision-log contract; the original long AGENTS remains archived verbatim. Exact provenance re-verification **PENDING**. NEXT_ACTION: confirm corrected provenance CI before M2, preserve all negative results and preregister M2 separately.


### 2026-11-22 — prospective M2 source-free predictable-history preregistration (NOT TESTED)

Following 51/51 exact M0/M1/cluster Python tests [#45024195498](https://github.com/IskanderAbdullin/Analytics/actions/runs/45024195498) and corrected AGENTS [provenance CI #45024279130](https://github.com/IskanderAbdullin/Analytics/actions/runs/45024279130) **SUCCESS**, froze [M2 predictable-history training-only candidate](CONDITIONAL_M2_PREDICTABLE_HISTORY_PREREG_20261122.md): `tau=1s`, fixed `mu`/amplitude grid, strictly past unique clusters, analytically integrated exponential excitation, train-only pooled log likelihood and mandatory independent run-level/negative controls. This is a **design-only** stage informed by point-process methods and warnings on in-sample time-rescaling calibration. No M2 code/tests or source runs have been executed, no new seeds allocated, no calibration or owner/FDR claims. NEXT_ACTION: implement M2 exact deterministic scorer/strict-causal tests before fresh original-source experiments.


### 2026-11-22 — M2 predictable-history source-free scorer, validation pending

The [prospective M2 freeze](CONDITIONAL_M2_PREDICTABLE_HISTORY_PREREG_20261122.md) was committed at `167d9174` **before** the new code and tests. Added `tools/public_m2_train_only.py`: O(N) strict-history exponential conditional intensity log likelihood, all 3×3 frozen grid candidates, original-run train-only fit, nonoverlapping evaluation identifiers, event-cluster deduplication, and complete/1ms asserted quality gates. Added 12 deterministic test methods (strict causality, exact one-event compensator, split-fill invariance, source IDs, negative backgrounds, missingness and malformed inputs). Local **source-equivalent** standalone code with minimal imported `Abstain` passed 12/12; exact GitHub code/tests **PENDING**. No M2 source holdout, statistical calibration, p-value, owner attribution, or real-market FDR. NEXT_ACTION: verify exact-source Python CI, fix any failures without retuning the frozen grid, then freeze independent original-run allocation before any new source simulations.


### 2026-11-22 — M2 numeric fail-closed integrity correction (source-free)

The exact-source [Python CI #45024579897](https://github.com/IskanderAbdullin/Analytics/actions/runs/45024579897) on `8a28d374` PASS **63/63** (12 new M2 negative/unit cases); [provenance CI #45024579964](https://github.com/IskanderAbdullin/Analytics/actions/runs/45024579964) SUCCESS. An additional deliberately malformed extreme integer timestamp/rate exposed unhandled Python `OverflowError` for `10**500` instead of scientific `ABSTAIN`, although all 63 original source-free tests were green. New defensive ceiling `2**53-1` integer milliseconds for exact float-safe timestamp representation, finite-real conversion guard for model parameters, and two adversarial cases make these violations explicit. Locally, equivalent exact M2 source on an isolated fixture passed **14/14** tests after the fix; new checked-out GitHub CI **PENDING**. The earlier failure is recorded, not erased. This is numerical robustness only: no source/holdout, no null exchangeability evidence, no p-values, no owner/FDR knowledge. NEXT_ACTION: verify exact GitHub new HEAD 65 tests; then independent original-run allocation/falsification protocol before fresh sources.


### 2026-11-22 — original-run split integrity source-free gate (NOT source allocation)

Prospective source-only contract frozen **before code** in commit `fe591340` at [CONDITIONAL_SOURCE_RUN_ALLOCATION_INTEGRITY_PREREG_20261122.md](CONDITIONAL_SOURCE_RUN_ALLOCATION_INTEGRITY_PREREG_20261122.md). New `tools/public_run_allocation_gate.py` audits only manifest structure: exact 3 train/calibration/evaluation partitions with all 4 original source cohorts, no repeated seeds across partitions, no dependent original-run/phase replay, no extra private fields, and rejection of every locally known spent seed from `seed_registry.json`. 10 adversarial tests use fake fixture IDs/seeds **NOT reserved**, plus a local minimal spent-ledger fixture; local run 10/10 PASS. Exact GitHub CI against full ledger **PENDING**. This gate cannot prove globally unused seeds, source independence, future scientific power, independent truth, or market FDR. No source/simulator runs or new experimental seeds allocated. NEXT_ACTION: confirm CI then document independent-run power/coverage calibration protocol and source license/revision before any original new source data.


### 2026-11-22 — final standard-migration and source-free CI checkpoint (no new empirical source)

The existing project alone was updated: short scoped AGENTS, original long AGENTS archived verbatim, GOAL/PROJECT_MAP/EVIDENCE navigation added, and canonical living MASTER/state history preserved; no Info or parallel project. Previous migration provenance regression was explicitly retained and fixed. **Exact current Python source-free CI on `32caf2c1`: [#45025008917](https://github.com/IskanderAbdullin/Analytics/actions/runs/45025008917) SUCCESS 75/75**, including new strict fail-closed M2 numeric cases and 10 original-run manifest integrity checks against the full local spent seed registry. [Current provenance #45025008831](https://github.com/IskanderAbdullin/Analytics/actions/runs/45025008831) SUCCESS. Other workflows on this SHA may still be running and must not be claimed complete. No new ABIDES source generation, new seeds, independent holdout, calibrated p-values, real-market FDR or owner attribution. The structural gate does **not** establish global novelty, statistical power, exchangeability or independent source truth. NEXT_ACTION: preregister justified sample size, power and independent original-run split with lawful source rights/revision before future source allocations; close master #72 only after independent scientific release audit.


### 2026-11-22 — prospective independent source evaluation design (not frozen)

A **design-only** precision/coverage and safety gate was added in [INDEPENDENT_SOURCE_EVALUATION_DESIGN_20261122.md](INDEPENDENT_SOURCE_EVALUATION_DESIGN_20261122.md). The prior 3301–3340 source worlds are inspected development data; the proposed >=100 independent seed worlds and four paired cohorts are **not allocated or run**, and proposed success criteria are not accepted without power/resource and multiplicity review. No original frozen protocol or threshold changed. Decision: prioritize source-free exact confidence-bound/clustered inference negative tests, provenance and feasibility before any expensive new source jobs. Real-market owner/FDR remain unknown.


**Source-free evaluation-bounds implementation (2026-11-22):** `tools/public_evaluation_bounds.py` and `tests/test_public_evaluation_bounds.py` add one-sided exact Clopper–Pearson bounds, fail-closed missing coverage and negative cases for zero alarms, invalid denominators, nonfinite alpha and abstentions. Commit `adbb776f` (after `02f9a90d`). **Tests and CI not yet independently verified on these commits; no original source runs.** The exact-binomial formula assumes independent original seed-world units and cannot be applied to repeated fills or paired-cohort differences without cluster-aware analysis. Next: verify CI, then implement paired seed-clustered inference and multiplicity controls before freezing any new source protocol.


### 2026-11-22 — prospective numeric and paired-seed negative-control registrations (NO DATA)

Before new source-free code/tests, registered [numeric coverage/overflow gates](EVALUATION_BOUNDS_NUMERIC_GATES_PREREG_20261122.md) and [paired original seed-world Bonferroni/conditional sign control protocol](PAIRED_SEED_CLUSTER_INFERENCE_PREREG_20261122.md). Parent HEAD `29bd4b80` verified: provenance, ABIDES and .NET all successful; explicit five bounds unit tests present in provenance log, but zero-coverage alpha and extreme denominator adversarial cases not yet exercised. New procedures require worst-case ABSTAIN, all three non-target backgrounds, no fill-level pseudoreplication, no source or owner identity claims. Design-only preregistration precedes any new code, market data or seeds; no statistical power/calibration implied. NEXT_ACTION: implement source-free guards and paired controls with honest CI and negative outcomes.


### 2026-11-22 — bounded exact confidence intervals and paired-world hard negatives (new source-free code)

After separate frozen preimplementation gate commit `54520189`, extended `public_evaluation_bounds.py` with 1..1000-world computational ceiling and alpha validation **even when all cases abstain**. Two new negative test methods target invalid alpha with zero eligible and huge integer n (`10**500`); legitimate 0/100 and n=1000 stay mathematically defined. New `public_paired_seed_inference.py` evaluates exactly four existing public-only cohort decision statuses per original world, worst-case abstention, Bonferroni one-sided CP bounds (alpha/4 for positive and three negative cohorts), and conditional paired one-sided McNemar/sign tail over discordant seed worlds; 10 source-free fake-fixture tests exercise periodic/momentum false positives, duplicate phase pseudoreplication, and private/oracle field rejection. **These are hypothesized engineering results; exact CI must be checked.** No independent seed-world source simulation, real market calibration, ownership or FDR. The conditional sign result is NOT real-market p-value; independence must be separately established. NEXT_ACTION: exact-source Python CI, repair, then independently review source resource/power and licenses before any new seeds.


### 2026-11-22 — exact CI confirms bounded binomial + source-free seed-world negative controls; independent power grid precommit

Original code/test commit `9777e50f` has exact [Python CI #45037801535](https://github.com/IskanderAbdullin/Analytics/actions/runs/45037801535) **SUCCESS 92/92**, including two numeric/coverage fail-closed tests and 10 paired original-world tests. These are hypothetical fixtures; cannot establish source independence or real-market FDR. To avoid selecting convenient sample size after inspecting power results, separately precommitted [6×3×4 source-free feasibility grid](PAIRED_INDEPENDENT_POWER_GRID_PREREG_20261122.md) **before any calculations**: four Bonferroni one-sided marginal gates, exact binomial pass probabilities, and a worst-case joint-power interval via union bounds under unknown within-world dependence. The earlier `>=100` worlds is proposal only; statistical power may be low. No source simulations, new seeds, actors or real-market p-values. NEXT_ACTION: deterministic complete grid computation + falsifiers, report all results including low-power scenarios.


### 2026-11-22 — fixed 6x3x4 hypothetical power grid source-free implementation (tests pending)

The [power grid prereg](PAIRED_INDEPENDENT_POWER_GRID_PREREG_20261122.md) was committed separately as `318ecb96` before code, thresholds, or results. New pure-Python `public_hypothetical_power_grid.py` computes six n sample sizes × three hypothetical positive rates × four worst-case hard-negative error rates, strict Bonferroni Clopper–Pearson gate cutoffs and **joint power lower/upper bounds** without assuming within-world cohort independence. Eight source-free unit checks include complete grid conservation, no hidden source identifiers, zero/100 negative upper risk, exact tail sanity and a deliberately low-power n=100 case. **No source data or new seeds; exact GitHub CI not yet verified.** NEXT_ACTION: confirm CI, archive full aggregate, audit whether proposed >=100 evaluation worlds is scientifically/financially feasible; do not claim joint power as a point estimate.


### 2026-11-22 — negative independent-world power feasibility and M2-residual precommit

[Exact Python CI #45038045732](https://github.com/IskanderAbdullin/Analytics/actions/runs/45038045732) PASS **100/100**, including eight 72-case power-grid integrity tests. The prospective [power feasibility audit](INDEPENDENT_POWER_FEASIBILITY_AUDIT_20261122.md) preserves the adverse result: at n=100 original worlds, hypothetical p_pos=.90 and any p_neg=.02, rigorous simultaneous-gate joint-power upper bound **.1326**; even at p_neg=.01 it is **.3660**, far below desired .80. These are not actual market or new-source probabilities; within-world cohort dependence is NOT assumed away. Source workflow 160 source cases ~92 seconds original GitHub wall but this is not a guaranteed performance forecast. Historical 6/40 and 7/40 Poisson/momentum false alarms are disqualifying methodological warnings, not sample-size problems. Also precommitted [M2 exact predictable integrated-gap design](CONDITIONAL_M2_RESCALED_GAPS_PREREG_20261122.md) before any new residual code or toy outcomes; no seeds/original source jobs. NEXT_ACTION: implement M2 integrated-residual causal tests, not expensive data collection.


### 2026-11-22 — strictly predictable M2 exact inter-cluster compensator implementation (CI pending)

After [prospective preregistration](CONDITIONAL_M2_RESCALED_GAPS_PREREG_20261122.md) commit `ac8d33df`, added `public_m2_rescaled_gaps.py` to analytically integrate M2 `mu+a Σexp(-lag/tau)` only between strictly ordered unique timestamp clusters, with each event's own jump affecting **future** intervals only. Nine source-free tests cover exact two-event integral, full-horizon compensator equality, M0 constant-rate limit, split-fill and future-suffix invariance, abstentions for missing event coverage/bad precision, train/eval overlap and unrelated periodic/momentum hard negatives. New exact GitHub CI **PENDING**. No new source/seed, p-value, owner or real-market FDR. NEXT_ACTION: verify CI and preserve any failed negative controls, then compare clearly non-target constructed tapes without tuning to evaluation outcomes.


### 2026-11-22 — M2 rescaled-gap CI green and independent M1-v2 dynamic lag precommit

[Exact source-free Python CI #45038410925](https://github.com/IskanderAbdullin/Analytics/actions/runs/45038410925) SUCCESS **109/109**, including nine M2 strictly causal intercluster compensator adversarial cases. The original M2 trained model, tau/grid and source gating are unchanged; mathematical integrals do not confer valid fitted-parameter KS p-values or market FDR. A separate prospective [M1-v2 dynamic lagged public L2 prereg](CONDITIONAL_M1_DYNAMIC_LAGGED_L2_PREREG_20261122.md) is frozen **before new code**: 1000ms delayed public BBO, source asserted continuity, strict one-ms timestamps, 10sec staleness fail-closed, exposure-duration-weighted *training-only* spread median and non-target negatives. This is deliberately separate from M1 stable BBO and may abstain extensively on real feeds. No new source, seeds, owner or false-discovery claims. NEXT_ACTION: implement M1-v2 and test causal exposure partition plus failed coverage negatives without selecting lag from old data.


### 2026-11-22 — dynamic M1-v2 source-free delayed L2 model implementation (CI PENDING)

After [fixed M1-v2 prospective prereg](CONDITIONAL_M1_DYNAMIC_LAGGED_L2_PREREG_20261122.md) commit `bc18b54f`, implemented a separate `public_m1_dynamic_l2.py` train-only duration-weighted spread-median with strictly delayed 1000ms public BBO transitions and complete time-tiling by L2 source-attested segments. Prediction accepts no evaluation prints or private/oracle labels; detects stale, absent, unsorted, duplicate, future or incomplete public books. Fourteen new unit/negative tests cover split fills, causal update timing, exposure conservation, source continuity, age/clock, leak prevention, zero strata and non-target hard negatives. Exact committed Python CI pending. 1ms clock and full feed continuity remain **unverified external assertions**, not proof of exchange-quality L2. Original frozen stable M1 stays intact; no real sources, seeds, market p-values or owner/FDR. NEXT_ACTION: verify exact tests then compare coverage/robustness and false abstentions before any independent source allocation.


### 2026-11-22 — M1-v2 exact-source CI negative findings and bounded correction

New [Python CI #45038676354](https://github.com/IskanderAbdullin/Analytics/actions/runs/45038676354) on `61475c4c` **FAILED 2 source-free test assertions + 1 error** (123 tests discovered): (1) a complete one-book 4.5s window was wrongly labelled stale in test, though frozen max age is 10s; (2) a training fixture with empty first world still had valid low and high events in the second world, so one-stratum ABSTAIN expectation was incorrect; (3) an extreme `10**500` ask quote raised raw OverflowError from `math.isfinite` instead of controlled ABSTAIN. The two test fixtures are corrected to truly stale / empty-stratum cases; numeric public quote validation now catches overflow and rejects it. This is a **necessary fail-closed engineering repair**, NOT posthoc tuning of the 1000ms model lag, 10s age limit, training median, source events, experimental seeds or outcome thresholds. Both failed assertions and the uncontrolled OverflowError remain in the science journal. Corrected exact GitHub CI pending. NEXT_ACTION: verify exact-source Python CI; then source-free dynamic-vs-stable quality comparison, no real market claims.


### 2026-11-22 — exact CI after M1-v2 failure and public-tape identifiability test precommit

Initial M1-v2 [CI #45038676354](https://github.com/IskanderAbdullin/Analytics/actions/runs/45038676354) failed 2 invalid fixture assertions and one unhandled `10**500` price overflow, all retained in the chronology; correction `5a32ebf9` has [exact Python CI #45038756426](https://github.com/IskanderAbdullin/Analytics/actions/runs/45038756426) **123/123 PASS**, including all 14 new M1-v2 tests without changing its preregistered L2 lag/age/median rules. Next frozen source-free [cross-model public-tape ambiguity and synthetic coverage prereg](CONDITIONAL_PUBLIC_TAPE_AMBIGUITY_PREREG_20261122.md) tests deterministic equality under identical public observations but different hidden stories for M0/M1-v2/M2, plus the older M1's known stable-book coverage abstention. This is a negative identifiability claim, not independent oracle validation or a market outcome. No fresh seed or source job. NEXT_ACTION: implement compact source-free cross-model panel and tests, then audit its limits.


### 2026-11-22 — source-free cross-model public-tape ambiguity panel (CI PENDING)

Per frozen [public-tape ambiguity prereg](CONDITIONAL_PUBLIC_TAPE_AMBIGUITY_PREREG_20261122.md) at prior commit `ebdf19ed`, added `public_m0_m1_m2_ambiguity_panel.py` with exactly three previously fixed tiny public tapes: regular unrelated period, non-target momentum, non-target irregular. All are scored after M0, M1-v2 and M2 were trained only on separate fixed constructed public training windows; output is aggregate compensator/log-likelihood/coverage, no oracle IDs, no original source events, no market p-values. Two different unobserved generating stories with identical public L2 and clusters must give *exactly identical* model outputs (falsifying ownership interpretation). Original M1 should ABSTAIN on 4.5s stale quote while new M1-v2 may cover two book-regime segments under externally ASSERTED continuity, not verified market L2. Eight source-free negative/unit tests added; exact GitHub CI pending. NEXT_ACTION: verify tests, preserve all negatives/unknown source completeness, do not claim actor count/FDR.


### 2026-11-22 — cross-model public ambiguity exact CI and frozen held-out LL design

[Source-free Python CI #45038996901](https://github.com/IskanderAbdullin/Analytics/actions/runs/45038996901) **131/131 PASS** after prereg `ebdf19ed`; all eight new cross-model toy cases passed, including identity of public-only M0/M1-v2/M2 outputs for identical observable tapes but different invented hidden stories, and old M1 quality abstention vs asserted complete changing-book M1-v2 segments. These are constructed public inputs, **not** new independent market worlds, real L2 completeness or actor evidence. Before coding, froze separate [full-window held-out fixed-intensity LL scorer](CONDITIONAL_FIXED_INTENSITY_HELDOUT_LL_PREREG_20261122.md) for M0/M1-v2, with exact exposure-time integration, split-fill invariance, causal upstream quality and M2 `a=0` cross-check. Its metrics are predictive source-free diagnostics only and do not establish formal goodness-of-fit p-values. NEXT_ACTION: implement and exact Python CI, then compare with M2 on frozen non-target tapes.


### 2026-11-22 — deterministic full-window heldout public point-process LL for M0/M1-v2 (CI PENDING)

Following separate [precommit LL protocol](CONDITIONAL_FIXED_INTENSITY_HELDOUT_LL_PREREG_20261122.md) at `64633828`, added `public_fixed_intensity_likelihood.py` with exact unique-event log-rate sum minus fully integrated public exposure on the complete observation window, strict sorted/positive/finite/source-complete causal segments, fail-closed external quality and no evaluation fitting. Ten adversarial tests cover split fills, delayed transition boundary, no-event legitimate LL, missing exposure, extreme invalid rates, timestamp integrity, M2-amplitude-zero analytical equivalence and non-target periodic/momentum. Exact GitHub CI pending. These are *predictive source-free* statistics only: no actual independent market labels, source completeness evidence, fitted-model KS p-values or physical owners. NEXT_ACTION: confirm CI and prospectively compare frozen hard-negative public tapes across M0/M1-v2/M2; keep all negative results.


### 2026-11-22 — exact heldout LL CI and prospective non-target model-comparison precommit

[Exact Python CI #45039198363](https://github.com/IskanderAbdullin/Analytics/actions/runs/45039198363) on `3b26412d` **141/141 PASS**, including ten source-free full-window M0/M1v2 log-likelihood controls. No market/source evaluation; this is engineering correctness of a mathematical score only. Before evaluating already-constructed non-target public tapes, froze [three-tape M0/M1v2/M2 held-out LL comparison](CONDITIONAL_CROSSMODEL_HELDOUT_LL_PREREG_20261122.md) with all three tapes, mandatory negative interpretations, fixed training code and no p-values/actor labels. This is prospective in methodology but tapes were already seen; not a fresh independent holdout. NEXT_ACTION: implement all-model panel, verify CI and save every outcome without cherry-picking.
