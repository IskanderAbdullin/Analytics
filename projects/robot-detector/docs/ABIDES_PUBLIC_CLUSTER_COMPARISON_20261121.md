# RD-CLUSTER-MARKET-13 — оригинальный ABIDES public timestamp-cluster перенос

**Заранее замороженный источник:** genuine ABIDES-NG revision `ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242`; четыре locally new seeds 3201–3204, 4 когорты и порог отношения 0,60, без оптимизации по новому исходу. [Протокол](../research/abides_clustered_grid_source_precommit_20261121.json) зафиксирован до source run.

**Оригинальный source-experiment:** [GitHub Actions #44938991772](https://github.com/IskanderAbdullin/Analytics/actions/runs/44938991772), 16 успешных отдельных matching-engine симуляций. Учитываются все случаи. Только aggregate результаты: [JSON](../fixtures/abides_clustered_grid_original_20261121.json). Полный короткий оригинальный source JSON находится в GitHub artifact **14720831681** с 7-дневным TTL; SHA256 *распакованного исходного JSON* `e75c089f023a12bddd19c2f4cf33a64470a29aeb79125024877fb4a9997885e2`. Не публикуем raw trades/quotes или private agent identifiers.

## Основные исходные числа

- **16 142** публичных частичных исполнений; **14 801** уникальное время исполнения; **1 341** дополнительных same-timestamp prints.
- **26 498** сохранённых постсобытийных публичных L2 snapshots (synthetic ABIDES).
- **61** приватно атрибутированное source-oracle исполнение TWAP — атрибуция прочитана **после** независимой публичной классификации и не входила в features.

| Сценарий | Сигналы per-print | Сигналы unique-timestamp | Ложные per-print / grouped | Abstain per-print / grouped |
|---|---:|---:|---:|---:|
| Poisson без TWAP | 1/4 | 1/4 | 1 / 1 | 0 / 0 |
| Периодический фон без TWAP | 0/4 | 0/4 | 0 / 0 | 0 / 0 |
| Momentum без TWAP | 0/4 | 0/4 | 0 / 0 | 0 / 0 |
| Внедрённый TWAP | 4/4 | 3/4 | 0 / 0 | 0 / 0 |

В исходной сравнительной матрице единственное
**ложное срабатывание в обеих методиках** —
Poisson-фон seed **3203**, без TWAP и без
контролируемых исполнений. Объединение одинаковых
timestamps не исправило этот исход.

На seed **3204** per-print ratio TWAP **0,61290323**
дал положительный сигнал, а unique-timestamp ratio
**0,41379310** пропустил внедрённый TWAP при
**13 фактически выполненных** source-oracle fills.
Следовательно, привязка score к уникальному
timestamp **потеряла 1/4 чувствительности** на
этих 4 положительных симуляциях.

### Согласованное сравнение на одних и тех же tapes

| Seed | Ложные background alarms per-print / grouped | TWAP per-print / grouped | Source TWAP fills |
|---|---:|---|---:|
| 3201 | 0 / 0 | TARGET_PATTERN / TARGET_PATTERN | 21 |
| 3202 | 0 / 0 | TARGET_PATTERN / TARGET_PATTERN | 11 |
| 3203 | 1 / 1 | TARGET_PATTERN / TARGET_PATTERN | 16 |
| 3204 | 0 / 0 | TARGET_PATTERN / NO_TARGET_PATTERN | 13 |

**Важная методология.** Это *парные* результаты
на одних и тех же исходных данных, не 32
независимых эксперимента. Точный timestamp
не доказывает один материнский ордер.
При этом искусственный контрпример с сотней
partial fills, где группирование отменяет
ложный сигнал, остаётся корректным, но он
**не репрезентативен** для всех ABIDES фонов.

### Научный вывод и ограничения

1. Нет подтверждённого преимущества grouped
   timestamp score по специфичности;
   в этом новом наборе его отрицательное
   влияние на чувствительность реально.
2. Четыре симуляции на сценарий не дают
   надёжных частот ошибок и не калибруют FDR.
   Даже `0/4` нельзя интерпретировать как
   доказанную высокую специфичность.
3. Источник — только synthetic matching engine,
   **нет** доказанных реальных владельцев
   или exchange-complete публичной ленты.
   Индивидуальные execution prints,
   timestamps и seeds нельзя считать
   независимыми real-world trade actors.
4. Все source-frozen thresholds, L2 coverage
   gates, исходы и отрицательные когорты
   сохранены без posthoc retuning.

**Следующий научный этап:**
[RD-MATCHED-UNCERTAINTY-14, issue #95](https://github.com/IskanderAbdullin/Analytics/issues/95) —
количественный аудит **малой мощности** и
парного сравнения двух решений на одной
симуляционной ленте, прежде чем выбирать
новый независимый source holdout.
Главный проект [#72](https://github.com/IskanderAbdullin/Analytics/issues/72)
остаётся открытым.
