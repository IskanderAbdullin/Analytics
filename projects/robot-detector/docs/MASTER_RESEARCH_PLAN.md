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

**Правило:** каждый существенный методологический поворот дополняет эту таблицу. Не переписывать историю, не удалять неожиданные отрицательные выводы и не называть собственное предположение полученным результатом.


### RD-CLUSTER-MARKET-13 — source execution verification checkpoint (2026-11-21)

Commit [`902fdeb`](https://github.com/IskanderAbdullin/Analytics/commit/902fdeb30e1548ab3722aa97718947cd9a9468fd) adds a **precommitted** original ABIDES 16-case source workflow for local seeds 3201–3204, four cohorts, threshold 0.60 and minimum 8 hits20. At this checkpoint the two observed HEAD workflow runs [44938997233](https://github.com/IskanderAbdullin/Analytics/actions/runs/44938997233) and [44938997239](https://github.com/IskanderAbdullin/Analytics/actions/runs/44938997239) passed provenance/.NET checks, **not** the new original ABIDES 16-case job. Therefore **no original source results or negative-control outcomes are yet verified**. Next action: execute the already-frozen original source workflow once, collect the short aggregate-only artifact, account for all 16 cases and abstentions, and only then update the scientific conclusion. Do not alter frozen seeds or threshold to fit outcomes.
