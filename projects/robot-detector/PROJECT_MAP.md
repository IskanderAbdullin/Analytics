# Market Robot Detector — короткая карта восстановления

**Единственный проект:** `IskanderAbdullin/Analytics/projects/robot-detector/`. **Рабочая ветка:** `agent/robot-detector-l2-binphase-20261121`. Не создавать проект-дубль в `Info` или второй исследовательский checkpoint.

| Когда нужен | Единственный актуальный источник |
|---|---|
| Цель / научный release gate | [GOAL.md](GOAL.md), [master issue #72](https://github.com/IskanderAbdullin/Analytics/issues/72) |
| Ограничения и алгоритм восстановления | [AGENTS.md](AGENTS.md), [операционное ТЗ](docs/AUTONOMOUS_RESEARCH_TZ.md) |
| План, пререгистрации, решения и хронология | [MASTER_RESEARCH_PLAN.md](docs/MASTER_RESEARCH_PLAN.md), секции 2–8 и датированные append-only исследовательские записи |
| Машинный checkpoint и **один** следующий шаг | [research/autonomy_state.json](research/autonomy_state.json), поля `current_stage` и `resume_instruction`; отдельный расходящийся `NEXT_ACTION` **не создавать** |
| Занятые seeds / отсутствие независимости | [seed_registry.json](research/seed_registry.json) |
| Подтверждения, отрицательные результаты, границы | [EVIDENCE.md](EVIDENCE.md), документы `docs/*NEGATIVE*`, provenance CI и issue [#97](https://github.com/IskanderAbdullin/Analytics/issues/97) |
| Текущая научная гипотеза M0/M1/M2 | [M0 prereg](docs/CONDITIONAL_M0_TRAIN_ONLY_PREREG_20261122.md), [M1 prereg](docs/CONDITIONAL_M1_LAGGED_L2_PREREG_20261122.md), [allocation gate](docs/CONDITIONAL_INTENSITY_ALLOCATION_GATE_20261122.md), [run-integrity prereg](docs/CONDITIONAL_SOURCE_RUN_ALLOCATION_INTEGRITY_PREREG_20261122.md) |
| Данные / разрешения / источники | [ARCHITECTURE](docs/ARCHITECTURE.md), [REAL_SOURCE_LICENSE_GATES](docs/REAL_SOURCE_LICENSE_GATES.md), [исследовательский обзор](docs/RESEARCH.md) |

**Восстановление после остановки:** проверить remote HEAD/CI, прочитать AGENTS → state → нужный раздел живого плана и stage issue, затем сверить committed source tests с CI. Старая запись `active_run_time_log` описывает прошлую сессию, **не** является действующим lock. При конкурирующем агенте не перезаписывать его checkpoint: отдельная ветка/PR либо дождаться непересекающегося сеанса.

**История:** большой хронологический журнал уже встроен в MASTER_RESEARCH_PLAN и GitHub issues/commits; подробная историческая версия прежнего AGENTS хранится в [архиве](docs/AGENTS_LEGACY_20261122.md). Сжатый контекст этого чата не представляет собой полную дословную стенограмму (`history_gap: full chat transcript unavailable`).