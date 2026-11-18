# Этап 3 — online-сканер, прогнозы, UI и интеграция с OsEngine

**Предусловие:** детектор этапа 1 с измеренной точностью этапа 2. **Цель:** следить за потоками в реальном времени без вмешательства в торговлю.

## 1. Источники

**Приоритет:** официальный T-Invest `MarketDataStream`: https://developer.tbank.ru/invest/api/market-data-stream-service-market-data-stream . Проверять текущие лимиты https://developer.tbank.ru/invest/intro/intro/limits и формат https://developer.tbank.ru/invest/services/quotes/marketdata . Архив этапа 1 — офлайн-реконструкция/восполнение после разрыва, но **не считать**, что архив всегда доступен в тот же момент и полностью идентичен live feed.

Разработать `TInvestStreamAdapter`: список инструментов UID, источник `EXCHANGE/DEALER`, тип подписки на обезличенные сделки; response statuses; auth scope; keepalive; session calendar; stream health. Никаких вызовов `OrdersService`, получения портфелей и trade POST. По возможности отдельный токен с минимальными правами.

Подписки: менеджер бюджета с ограничением на connections/subscriptions по официальным лимитам; динамический `add/remove` без беспорядочного переподключения; распределение по connections; retry с jitter/backoff и circuit breaker; не снимать рабочие подписки из-за одной ошибки; зависимые ресурсы и лимиты учитывать в отчёте.

## 2. Корректность live

- Stream может переподключаться и приходить out-of-order. Поддержать event-time watermark и небольшой configurable grace window; поздние данные подхватываются с пометкой `late` и пересчётом только затронутого окна. Никогда не утверждать exactly-once без ID.
- Разделить `market_time`, `received_time` и `display_time`; измерить clock skew. Статистика периодов строится по `market_time` при достаточной точности.
- Во время реконнекта/неизвестного gap помечать `coverage=degraded`; прогнозы временно выключаются или сопровождаются явной низкой надёжностью. Не объявлять робота остановившимся из-за сбоя данных.
- Периоды с отсутствующими prints при достаточном coverage учитывают пропущенные циклы; hard stop только после `N` ожидаемых окон и на основании смоделированной вероятности, а не фиксированного magic timeout.
- На полной загрузке — ограниченная очередь, backpressure, disk spill или drop с **флагом частичной потери**, а не тихий loss.
- Idempotent publication: стабильные `pattern_id`, `event_id`, `revision`; после перегрузки UI не создавать двойные карточки.
- Сопоставление live и replay на записи одного session: одинаковое состояние после watermark при фиксированном конфиге; различия из-за latency документировать.

## 3. State machine

```text
unseen → candidate → confirmed → stale → stopped
                 ↘ rejected     ↘ confirmed (при повторном сигнале)
connected → degraded → reconnecting → recovering → connected
```

`candidate`: есть статистический сигнал, но нет независимых holdout подтверждений. `confirmed`: достигнуты валидационные пороги. `stale`: ожидали события, не наблюдали при здоровом feed. `stopped`: достаточно здоровых пропущенных периодов по заранее заданному правилу. Для деградировавшего источника — `insufficient_data`, без автоматической классификации остановки.

Новые данные должны пересчитывать не всю историю, а скользящие окна. `T`, `q`, `phase` обновлять осторожно; резкое изменение создаёт версию гипотезы/смену режима, а не бесконечное число новых роботов. Дедуп cross-detection/global fusion обязателен.

## 4. UI (read-only)

### Главный список

Фильтры: инструмент UID/ticker, MOEX/СПБ, источник, направление *в терминах провайдера*, модель, состояние, minimum matches, статистическая значимость, ликвидность, дата/сессия, время последнего подтверждения. Таблица: `pattern_count`, `confirmed`, `buy-like/sell-like/unknown`, `data_quality`; не путать total pattern count с количеством физических роботов.

### Детальная карточка

Обязательные поля: `q` лотов, `T` мс/с, фаза, диапазон разброса, время начала/последнего события, `observed_lots`, включённые события, ожидаемые/пропущенные циклы, ссылка на события и график, next predicted **window** (не обещать точную секунду), accuracy holdout, null-model comparison, CI/calibrated probability только при наличии. Кнопка replay → выбранный срез истории.

### Визуализации

- scatter timeline: сделки с размером/стороной, наслоение predicted ticks, matched/unmatched;
- histogram `time mod T` и periodic candidate peaks;
- отдельный график качества feed и latency;
- сравнение обнаруженного объёма с рынком; итоговая доля не может превышать 100% из-за двойного счёта;
- badges `SYNTHETIC / LIVE / DELAYED / INCOMPLETE` — только значимые статусные метки.

Не показывать ложную точность `98%` без stage-2-calibration.

## 5. API для клиентов OsEngine

Локальный read-only сервер (например ASP.NET Core):

```text
GET /api/v1/health
GET /api/v1/instruments
GET /api/v1/instruments/{uid}/patterns?state=confirmed
GET /api/v1/patterns/{patternId}
GET /api/v1/patterns/{patternId}/evidence
GET /api/v1/patterns/{patternId}/predictions
GET /api/v1/replay/{id}
WS  /api/v1/events  (pattern_created/updated/stopped; coverage_changed)
```

Схемы JSON версионируемые, определять устойчивую совместимость `major.minor`, client reconnect cursors и `snapshot+delta`. Локальный bearer/OS ACL либо named pipe; по умолчанию bind **127.0.0.1**. Если внешняя сеть — explicit config + TLS/auth/rate limit. Нет торговых команд даже в hidden endpoints.

OsEngine adapter: отдельный потребитель, который подписывается на подтверждённые паттерны/события и может выставлять их в параметрах **своего** робота. Аналитический сервис никогда напрямую не посылает приказы. Игнорировать неподтверждённые и stale сигналы, проверять broker/account mapping по UID. Сами заявки и риск-правила — вне scope детектора.

## 6. Пилот и сценарии ручной проверки

Пилот: 5–10 ликвидных/неликвидных инструментов MOEX и (если покрытие доказано) СПБ, несколько сессий, отдельная метрика полноты feed. Запуск только в наблюдательном режиме.

Тесты: 24h synthetic stream; 100 кратких disconnect/reconnect; 1e6 replay events; duplicate bursts; 1s timestamp resolution; переход торговой сессии; горячая смена подписки; смена UID/тикера; out-of-order; gaps; переполнение очереди; ротация auth; отсутствие прав; пересечение детекторов; частичное отставание UI.

## 7. Нефункциональные требования и приёмка

Целевые, а не доказанные значения:
- P95 processing latency < 500ms от поступления на локальную машину до обновлённого snapshot при выбранной пилотной нагрузке; P95 UI display <2s (указать устройство/нагрузку).
- Нулевые запросы торгового типа; compile-time feature isolation; статический тест запрета `PostOrder/Cancel/Replace` в проекте.
- Нет «robot stopped» при coverage gap, ни silent drop, ни двойного учёта prints.
- Восстановление от разрыва с журналом и явным `unknown` для необратимых пропусков.
- Прогнозы offline/live parity; state machine unit + property tests; integration streaming sandbox с fake server.
- Токены не отображаются в UI и логах; нет сетевых портов наружу по default.
- CLI, UI и API поддерживают экспорт референсных synthetic data и не публикуют лицензированные live feed dumps.

**Гейт:** релиз online только после повторения stage-2 benchmark на действительно полученном feed; при низком покрытии — ограничить доступные фичи с честным указанием причин.

## 8. Отдельные коммиты

`01-stream-adapter` → `02-ingestion-watermarks` → `03-state-machine` → `04-service-api` → `05-ui` → `06-osengine-client` → `07-reconnect-stress` → `08-pilot-and-ops-runbook`.


## 9. Дополнение: детектор смены режима + правильная временная шкала (18.11.2026)

**Научный источник:** [Tsaknaki–Lillo–Mazzarisi, BOCPD](https://arxiv.org/abs/2307.02375) (публикация Quantitative Finance 2025); [пример Rust online engine](https://github.com/OctopusTakopi/bocpd), MIT. См. [расширенный обзор](RESEARCH_EXPANSION_2026-11-18.md).

Сделать отдельный `RegimeChangeDetector` как optional read-only эксперимент, сравнивающий `EWMA`, `CUSUM`, `Bayesian Online Change Point Detection`. Вход: `signed_trade_count`, `signed_volume`, `event_rate`, текущий поток `data_quality`; выход `change_point_probability` (калибровать) или uncalibrated `score`, `regime_start`, `latest_state`. Нельзя напрямую выводить count bots из number_of_regime_changes.

Live-проверки: 500ms baseline bins, более длинные окна для 60s TWAP; относительная латентность ClockTimeBinSeries; транзакционное сохранение FFT state; backfill без создания фальшивых циклов; reset только affected symbol. Во время `degraded` или неполного event-time coverage posterior/состояние гипотез временно фиксируется или помечается invalid, а не объявляет «робот остановился».

Отдельная UI строка: **«Режим рыночной активности изменился»** и **«Различимый регулярный поток подтверждён»**, чтобы пользователь не спутал общий burst со стороной исполнения конкретного алгоритма. Smoke-тест переключения режима без единого истинного робота не должен породить новый confirmed pattern.

Acceptance: одинаковая история в offline replay и online stream даёт сопоставимые posterior change points после согласования watermark; BOCPD имеет реальный out-of-sample прирост над EWMA/CUSUM или остаётся выключенным.

## 10. Новая диагностическая панель: активность котировочных роботов без исполнений

Подход Bogoev–Karam (2017), [первичный источник](https://durham-repository.worktribe.com/output/1358815/); подробная спецификация [Research Part 2](RESEARCH_EXPANSION_2026-11-18_PART2.md).

- UI раздельно показывает **Regular trade streams**, **Quote oscillation episodes** и **Behavior motifs**. Эти значения не суммировать в число независимых роботов.
- Quote snapshot: venue, UID, event time, bid/ask price, best-level quantities, tick_size, age, source coverage, latency. Только book updates, доступные по API; запрет заполнения недостающих событий.
- Для `QUOTE_OSCILLATION` выводить side (bid/ask/both), `oscillation_count`, `CarryBid/CarryAsk`, `BigBid/BigAsk`, tick-normalized ratio и ненулевой baseline. Не показывать процент уверенности до калибровки.
- При недостаточной частоте наблюдений, резком разрыве, halt/auction или resync → `INSUFFICIENT_BOOK_SAMPLING`; не донаблюдать «осцилляции» через интерполяцию и не классифицировать манипуляции.
- Отдельный флаг `passive_activity_only`, когда котировки меняются, но подтверждённых prints нет. Это наблюдение **не** означает absence of trades in venue, если feed degraded.
- Read-only интерфейс к OsEngine передаёт `episode type, start/end, scope, coverage`, не персональные ID и не инструкцию на торговлю.
- Проверить UI при 100ms book throttle: короткие эпизоды быстрее 100ms недоступны, в интерфейсе показывается ограничение разрешения.
