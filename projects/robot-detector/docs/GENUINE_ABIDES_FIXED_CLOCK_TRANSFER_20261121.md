# RD-ABIDES-INDEPENDENT-07 — отрицательный перенос toy-clock детектора на genuine ABIDES-NG

**Оригинальный успешный эксперимент:** https://github.com/IskanderAbdullin/Analytics/actions/runs/44928306325

Перед запуском зафиксированы Git revision реального движка ABIDES-NG, исследовательский протокол, исходные seeds **2801/2802**, один и тот же 10-секундный clock-grid, допуск **250 мс**, порог **0,22**, три сценария на каждый seed. После анализа публичных prints отдельно прочитаны private simulated attribution метки, чтобы подтвердить присутствие target. Выполнено **6 отдельных прогона matching engine**; разные фазы одной ленты не выдаются за независимые эксперименты.

## Подтверждённые результаты (никакой posthoc перенастройки)

| Сценарий | Тревог | Интерпретация |
|---|---:|---|
| 60 Poisson noise agents | **0/2** | 0 ложных тревог |
| 60 fixed-cadence noise agents, без injected target | **2/2** | **2 ложные тревоги** |
| 60 Poisson noise + injected TWAP 45s | **0/2** | **2 пропуска**; real source-matched controlled TWAP executions: **13+16=29** |

Original public-only fraction near frozen 10s grid по двум seeds соответственно:

- Poisson noise: **0,03969595**, **0,04211557**.
- Fixed cadence noise: **0,70961887**, **0,67939815**.
- Injected TWAP: **0,04201681**, **0,05800464**.

Нулевая чувствительность к TWAP в этих **двух** искусственных рынках не означает, что TWAP в целом невидим. Исследованный признак специально фиксировал **10-секундную** сетку, а контролируемый TWAP работал с периодом **45 секунд**, поэтому отрицательный перенос — ожидаемая, но теперь эмпирически подтверждённая граница конкретного признака.

### Почему это важно

1. Хорошая детекция синтетического *ритма* в toy-world не гарантирует обнаружения физического источника данного ритма в реалистичном matching engine.
2. Регулярный фон способен дать сильный сигнал и **не содержит** отдельно injected TWAP. Отсюда false alarms нельзя переименовывать в true positives.
3. Абсолютное число публичных сделок, 5-уровневые ABIDES L2 snapshots и постфактум контролируемые исполнения проверены; **никакие личные agent IDs не поступали в признаки**.
4. Ни accuracy, ни precision/recall/FDR в настоящих биржевых данных не измерены. Класс фоновых симуляторов ограничен; всего два seeds на сценарий, нет известной независимой real-market ground truth.

Скрипт: [abides_fixed_clock_transfer.py](../tools/abides_fixed_clock_transfer.py). Негативные тесты: [test_abides_fixed_clock_transfer.py](../tests_background/test_abides_fixed_clock_transfer.py). Исходный компактный run artifact ID **14716637999**; исходные ленты не опубликованы. Workflow после успешного прогона переведён в manual-only.

**Следующая задача:** [RD-ABIDES-MULTISCALE-08 — public-only более устойчивые признаки с fixed-cadence/momentum hard negatives](https://github.com/IskanderAbdullin/Analytics/issues/89). Это исследование, а не объявление результата полностью готовым. Master issue #72 остаётся открытым.
