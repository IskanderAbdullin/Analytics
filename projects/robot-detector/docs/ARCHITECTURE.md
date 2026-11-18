# Архитектура Market Robot Detector

**Версия:** 1.0 · **Scope:** независимый C#/.NET проект в `projects/robot-detector/`.

## 1. Принципиальные допущения

1. Публичный `trade print` — отдельное наблюдение сделки, не доказательство отдельного торгового решения. Возможны пакетные/частичные исполнения, задержки, исправления и дубли.
2. Наличие ценовой/временной регулярности не идентифицирует владельца. Обязательные сущности: `PatternHypothesis`, `Evidence`, `Coverage`, `Prediction`; слово `robot` только в интерфейсе с пояснением.
3. Источник `EXCHANGE`/ `DEALER` не объединять. Следить за торговым режимом, timezone, перерывами, аукционами, точностью timestamps.
4. Данные `L2` — агрегированные объёмы по уровням; `MBO` с индивидуальными ID не предполагать, пока отдельно не доказан доступ.

## 2. Техническая схема

```text
HistoryTradeArchive      TInvest MarketDataStream       OsEngine read-only adapter (optional)
        |                           |                                  |
        +---------------------------+----------------------------------+
                                    v
                   Ingestion / data-quality / replay log
                                    |
                          Normalized MarketEvent
                                    |
                     Symbol + venue/source + session
                                    |
                  Event assembler / batch split policy
                                    |
                    Candidate generation (multi-period)
                                    |
                  TWAP / phase / residual / validation
                                    |
                Hypothesis fusion / de-duplication / state
                                    |
             Immutable results + calibration + predictions
                                    |
                 CLI / JSON / UI / read-only localhost API
                                    |
                   OsEngine consumers (read only)
```

## 3. Целевая структура репозитория после реализации

```text
projects/robot-detector/
  README.md
  docs/                 # эти ТЗ + будущие ADR
  src/RobotDetector.Core/
  src/RobotDetector.Data.TInvest/
  src/RobotDetector.Data.OsEngine/   # опционально
  src/RobotDetector.Detection/
  src/RobotDetector.Storage/
  src/RobotDetector.Cli/
  src/RobotDetector.Service/
  src/RobotDetector.Ui/              # интерфейс только после этапа 2
  tests/RobotDetector.UnitTests/
  tests/RobotDetector.PropertyTests/
  tests/RobotDetector.IntegrationTests/
  tests/RobotDetector.ReplayTests/
  tests/RobotDetector.Benchmarks/
  config/defaults.json
  data/raw/              # в .gitignore в рамках проекта
  data/normalized/       # в .gitignore
  data/results/          # в .gitignore
```

Таргет: .NET LTS, поддерживаемый OsEngine и целевой Windows; конкретную версию зафиксировать в ADR после проверки ABI/зависимостей. Для автономной аналитики не требовать WPF или работающего OsEngine. Для тестов Linux CI может использовать Core/CLI без Windows GUI.

## 4. Data contracts

### 4.1 MarketEvent

Обязательные поля:
- `event_id`: детерминированный идентификатор (не биржевой order ID); строится из канонических полей + порядкового номера при коллизии.
- `source_system`: `t_invest_history | t_invest_stream | osengine`.
- `venue`, `trade_source` (`EXCHANGE | DEALER | UNKNOWN`), `instrument_uid`, `ticker`, `trading_mode`, `session_id`.
- `exchange_time_utc` и `receive_time_utc` (когда доступно), `timestamp_precision`, `arrival_sequence`.
- `price_decimal`, `quantity_lots` (64-bit positive), `lot_size` и `currency` если известны, `reported_direction` и `direction_semantics`.
- `is_reconstructed` (false для сырых prints), `quality_flags[]`, `raw_reference`.

Принцип: `reported_direction` не переименовывать автоматически в `buyer_owner` или `seller_owner`.

### 4.2 PatternHypothesis

`pattern_id`, `instrument_uid`, `venue/source`, `model_family`, `direction_assumption`, `quantity_model`, `period_ms`, `phase_utc`, `jitter_model`, `first_observed`, `last_observed`, `evidence_event_ids[]`, `matched_count`, `expected_count`, `missed_cycles`, `observed_lots`, `estimated_lots_range`, `holdout_prediction_hits`, `null_p_value`, `confidence_calibrated` (nullable), `coverage_summary`, `state` (`candidate | confirmed | stale | stopped | insufficient_data`), `detector_version`, `config_hash`.

Суммарный объём — сумма **только однозначно отнесённых print-событий**; пересекающиеся гипотезы не должны удваивать объём. Оценка количества покупателей/продавцов — количество подтверждённых непересекающихся групп, с явно обозначенной неопределённостью.

### 4.3 Prediction

`pattern_id`, `forecast_origin_utc`, `target_window_start/end`, `expected_lots_range`, `probability` (только после калибровки), `resolved_at`, `outcome`, `data_coverage_at_resolution`. Прогноз создавать **до** появления оцениваемого события.

### 4.4 Пример результата (синтетика)

```json
{
  "schema_version": "1.0",
  "instrument_uid": "SYNTH-1",
  "trade_source": "EXCHANGE",
  "data_kind": "SYNTHETIC",
  "coverage": {"complete": true, "timestamp_resolution_ms": 1},
  "active_patterns": 1,
  "patterns": [{
    "pattern_id": "sample-A",
    "model_family": "fixed_quantity_periodic",
    "reported_direction": "SELL",
    "quantity_lots": 100,
    "period_ms": 5000,
    "matched_count": 6,
    "missed_cycles": 0,
    "observed_lots": 600,
    "state": "confirmed",
    "confidence_calibrated": null
  }]
}
```

## 5. Интерфейсы модулей

```csharp
public interface IMarketEventSource
{
    IAsyncEnumerable<MarketEvent> ReadAsync(
        MarketDataQuery query, CancellationToken cancellationToken);
}

public interface IPatternDetector
{
    IReadOnlyList<PatternHypothesis> Detect(
        IReadOnlyList<MarketEvent> events, DetectorConfig config);
}

public interface IPredictionEvaluator
{
    EvaluationResult Evaluate(Prediction prediction, IReadOnlyList<MarketEvent> future);
}
```

Методы и типы — контракт-предложение; их окончательная версия принимается на этапе 1. Источники не должны зависеть от UI. Точные decimal и целые лоты обязательны; double допустим внутри статистического ядра, но не для цен и исходных объёмов.

## 6. Replay, порядок событий и консистентность

- Хранить *raw immutable* до нормализации: `source_version`, hash, время получения, provenance, права доступа.
- Сортировка по `exchange_time_utc`, затем `arrival_sequence`; одинаковые timestamps могут содержать разные сделки.
- При повторном подключении (stream): watermarks, idempotency cache, журнал gap/late/out-of-order; **не считать отсутствие сообщения отсутствием сделки**.
- Если нет доверенного trade ID, дедупликация по `time+price+quantity+side` **может удалить законные отдельные prints**. Поэтому дубли исключать только при доказанной повторной доставке с идентификатором/пересечением диапазонов, иначе оставлять и помечать.
- Полностью детерминированный replay по идентичным данным/настройкам; версия нормализации и алгоритма входит в результат.
- Время биржи — для статистики, время получения — для измерения задержки. Не интерполировать искусственно отсутствующие события.

## 7. Контроль качества и безопасность

Дашборд качества: `missing_fraction_estimate` (nullable), `timestamp_precision`, `data_age_ms`, `reconnect_count`, `out_of_order_count`, `source_status`, `session_calendar_version`. На перерывах/потере покрытия — `insufficient_data`, не ложное завершение алгоритма.

Read-only по дизайну: никаких методов выставления, модификации, отмены заявок, получения портфеля или права на операции. Токены через environment/DPAPI/другой защищённый secret store. Нельзя писать токены, HTTP headers, пользовательские идентификаторы, сырые лицензированные ленты в git или публичные артефакты. Только явно разрешённые read-only endpoints; локальная UI API по loopback с auth при выходе за loopback.

## 8. Перфоманс и ограничения

Начальные SLO — инженерные **целевые критерии, не результаты измерений**:
- Историческая обработка 1 млн prints до 120 с на контрольном ПК (процессор/конфигурацию зафиксировать).
- RAM до 2 GiB для окна 1 млн prints за счёт потоковой обработки/индексов (настраиваемый буфер).
- Онлайновая P95 задержка появления события на экране: до 2 с после *получения* без сети/биржи в измерении.
- 100 подписанных инструментов в пилоте без торговых команд; проверять действующие лимиты провайдера.
- При сбое источника — отсутствие ложных `stopped` и работающих прогнозов с фиктивно полными данными.

## 9. Границы этапов

Этап 1 — только history/CLI; этап 2 — только научная проверка и quality gates; этап 3 — live/UI/API; этап 4 — L2/научная разработка. Изменения архитектуры оформлять ADR с аргументами и миграцией контрактов.


## 10. Новые научно обоснованные компоненты (дополнение 18.11.2026)

См. [подробный анализ с конкретными ссылками и кодом](RESEARCH_EXPANSION_2026-11-18.md).

Предусмотреть **несколько независимых сигналов**, не меняющих базовый контракт `PatternHypothesis`:
- `ClockTimeBinner`: формирует временную шкалу по **реальным UTC timestamps** и нулям только в известных здоровых рыночных интервалах; event count, lot volume, notional — разные ряды.
- `FftPeriodCandidateGenerator`: detrend/Hann/FFT/PSD/top peaks, возвращает только `period candidate` и спектральную неопределённость; **не физическое число роботов**.
- `MinutePhaseBaseline`: сравнивает `timestamp modulo 60s` и общий секундный ритм, демонстрирует пользу/ошибку тривиальных фильтров.
- `PhaseAndQuantityMatcher`: event-level реконструкция разных q/T/phase с one-to-one matching; единственный модуль может продвинуть кандидата в confirmed после stage-2 validation.
- `NullMarketRhythmModel`: естественная активность на границах секунды/минуты и Hawkes clustered control.
- `ChangePointComparator` (этап 3/4): EWMA/CUSUM/BOCPD на честной истории, режимный сигнал **отдельно** от регистрации робота.
- `L2ReplenishmentDetector` (этап 4): состояние bid/ask по цене с подтверждением сделок, инвалидация на gaps/resync.

Зафиксировать `bin_ms`, `window_s`, `effective_nyquist_hz`, `cycles_in_window`, `source_precision_ms` в конфиге и результатах. Версии сторонних репозиториев указывать как provenance/референс, **не скрытые production dependencies**. Все optional-модули реализовать в собственном .NET core или отдельной research-утилите, без внесения Python в C# runtime.

## 11. Дополнение 18.11.2026: разные классы доказательств, clock model, внешняя эталонная симуляция

[Обзор с исходным кодом и формулами](RESEARCH_EXPANSION_2026-11-18_PART2.md).

### Event-time против wall-clock time

Добавить к каждому свидетельству `clock_type = exchange_utc | receive_utc | event_index | operational_volume`, `sampling_resolution_ms`, `coverage_status`; запрещено выводить период `T=5 секунд` из FFT по индексу trade без привязки UTC. Отдельно сравнивать расписание **подачи ордера** и **исполнения**: публичные принты дают преимущественно второе. Частота сделок в volume-time не является частотой в секундах.

### Новые интерфейсы

```csharp
public interface IQuoteOscillationDetector {
    IReadOnlyList<QuoteBehaviorEpisode> Detect(
        IReadOnlyList<BestQuoteObservation> quotes, DataCoverage coverage);
}
public interface IBenchmarkTapeProjection {
    PublicMarketTape Project(
        SimulatorGroundTruth truth, ProjectionConfig config);
}
public interface IBehavioralMotifDetector {
    IReadOnlyList<BehavioralMotif> Detect(
        IReadOnlyList<MarketFeatureBin> history, CoverageSummary coverage);
}
```

`QuoteBehaviorEpisode` = time window, bid/ask flags, oscillation total variation, net move, tick size, read-only evidence, observed book coverage. Не относится автоматически к `PatternHypothesis`, пока не доказан устойчивый, различимый event stream. `BehavioralMotif` = recurring shape with nearest-neighbor distance, repeated-segment count, conditional-null significance; также не равен конкретному участнику.

### Подкаталог исследовательских тестов в будущем

```text
projects/robot-detector/
  research/abides/     # isolated simulator env, pinned repo SHA, scenario manifests
  research/stumpy/     # optional Python comparison, not C# runtime
  benchmarks/          # deterministic public projections + private truth (ignored)
```

ABIDES truth labels никогда не подмешивать в detector input: нужны отдельные форматы `internal_truth`, `public_trades_only`, `public_trades_and_l2`, `score_report`. Обработка book event source failures — status unknown, а не «исчез робот».

### UI/API терминология

Показать отдельно:
- `distinguishable_execution_patterns`: уникальные подтверждённые потоки исполнений;
- `quote_behavior_episodes`: эпизоды частой перестановки best bid/ask, без счётчика владельцев;
- `behavioral_motifs`: повторяемые последовательности рыночных событий;
- `physical_agent_count_known`: true только на симуляторе с privileged truth, во всех публичных данных false/unknown.
