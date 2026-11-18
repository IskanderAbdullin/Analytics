# 06. Research / ML: расширяемая научная платформа

**Приоритет:** после M5/M7, начиная с M9. ML — надстройка над проверенной историей, не замена финансовой бухгалтерии.

## 1. Исследовательские вопросы

- RQ1: Какие комбинации инструмент/ликвидность/спред/волатильность/время дня/режим робота приводят к net P&L с достаточным статистическим запасом?
- RQ2: Как оценить вероятность исполнения пассивной заявки на конкретном уровне в заданном горизонте, с отдельно указанных допущений рынка и pro-rata?
- RQ3: Какие факторы предсказывают неблагоприятный сдвиг midprice после исполнения (adverse selection)?
- RQ4: Где проявляются переторговка, циклическая перестановка, агрессивное накопление позиции и сбои логики?
- RQ5: Изменение каких настроек (quote distance, order size, target level) реально улучшает net performance вне обучающей выборки?
- RQ6: Какие рыночные состояния увеличивают риск больших убытков, высокой комиссии или отсутствия ликвидности?
- RQ7: Есть ли характерные рыночные условия, когда робот A надёжнее робота B, с учётом размерности и калибровки?
- RQ8: Какие простые правила достаточны, а где сложные модели демонстрируют устойчивое преимущество?

## 2. Данные и каталог признаков

**Data lake zones:**
- Raw (immutable broker/API/robot raw JSON, snapshots and compressed market events).
- Curated (typed normalized events + mark & FX data, reconciliation evidence).
- Feature store (point-in-time feature partitions).
- Label store (future outcome labels, separately protected from feature retrieval).
- Evaluation datasets (immutable manifests with code/data/feature versions).
- Model registry (artifacts and metrics; local first).

Каждая строка feature data имеет:
`entity_id`, `decision_utc`, `event_time_utc`, `available_utc`, `source_version`, `feature_version`, `quality_status`, `missing_reason`, `market_regime_tag`.

**Признаки заявок:** side, requested volume, distance-to-best, spread, imbalance across L1–L100 (если реально доступно), quote lifetime, own inventory, time since prior cancel, market trade flow, realized volatility, level target size, queue proxy; источник и latency обязательны.

**Признаки роботов:** bot version/config hash, state, unmatched fills, risk budget, consecutive errors, repeated target shifts, decision reason, throttle utilization, time from market-data update.

**Признаки рынка:** best bid/ask, relative spread, order book slope, volume imbalance, cancelled/replenished book quantity, last-trade signed imbalance (estimation only), daily regime, price gaps, session calendar. Не создавать фиктивные L100 snapshots или latency из свечей.

**Признаки P&L:** historical realized cost and returns at decision time only; запрещены latest full-day outcome, realized fees after decision, post-trade mid when serving the model in live-time inference.

## 3. Targets/labels (определить заранее)

- `fill_within_1s_5s_30s` (binary/censored if order cancelled) — distinguish actual fill vs unfilled due to voluntary cancel; survival analysis preferable when censoring material.
- `post_fill_adverse_move_bps_5s_30s_5m` — side-aware future mid price change; **только label**.
- `net_pnl_episode_rub` or bps per unit traded, carefully defining exit and fees.
- `risk_event_next_10m` — predefined incident, no post-hoc relabeling.
- `cancel_fail_reason` — confirmed benign fill-race vs true failure.
- `expected_execution_cost` — realized shortfall benchmark.
- `market_regime_next_period` — not a feature at prediction origin.

Для каждого label: horizon, entity grouping, maturity timestamp, censoring, missingness. Прогнозирование результата стратегии по полностью реализованным сделкам может страдать selection bias — включать неисполненные решения/ордеры как наблюдения when studying execution decisions.

## 4. Point-in-time контракт и защита от leakage

- Определить `prediction_origin` и `information_cutoff` до создания features.
- Условие для каждого raw event: `available_utc <= prediction_origin`; event time alone недостаточен.
- Historical backfill не меняет модельное прошлое: use vintage revisions with available timestamps.
- Chronological grouped walk-forward, gap/embargo across overlapping horizon labels.
- Группировать связанные решения одного run/order/day, не разделять их случайно между train/test.
- Fit scaler/imputer/encoder/feature selection/threshold/calibrator **только на train**.
- Purged evaluation when targets overlap, no leakage from universe selection or future corporate action.
- Freeze untouched test period; version every retrain and dataset; model comparisons with baselines.

## 5. Baseline-first модельный pipeline

**ML-0 — без ML**: rolling average/net P&L / baseline fill probability by spread/level/size; прозрачные KPI и доверительные интервалы.

**ML-1 — anomaly detection**: robust z-score / rolling median / EWMA / isolation forest on cost, latency, missing data, P&L spikes. Targets may not be known; grade precision via labeled incidents. Не считать непонятный результат мошенничеством или ошибкой, пока не проверен.

**ML-2 — fill probability:** logistic regression / calibrated gradient boosting / survival models; evaluate log loss, Brier, reliability diagram, precision-recall and calibration by order size/venue/level/regime. Severe class imbalance handled by weighted metrics and PR curves.

**ML-3 — adverse selection/slippage:** regularized regression, monotonic constraints when justified, gradient boosting; evaluate MAE, quantile loss, interval coverage, out-of-sample net-cost reduction in offline policy comparison.

**ML-4 — strategy regime classifier:** group-wise risk/return/regime; no guaranteed market predictability. Evaluate stability, calibration and utility net of costs.

**ML-5 — constrained policy research:** offline rule search, Bayesian optimization, contextual bandits with pessimistic off-policy evaluation. Do not promote to live execution without separate approval, risk controls and forward paper validation.

Deep networks, LSTM, transformers and reinforcement learning допускаются только после успешных простых baseline и доказанного dataset volume; отсутствие независимых L2 event feeds/правдоподобной simulational execution model блокирует достоверный RL execution claim.

## 6. Эксперименты и воспроизводимость

`experiment.yaml` содержит:
- question/hypothesis, target, universe, instruments, selected bots;
- dataset manifest SHA256, source windows, coverage;
- available_time policy, feature definitions, label horizons, training cutoff;
- split plan, embargo, leakage tests, baseline, candidate models;
- hyperparameters, seeds, code SHA, Python lockfile/runtime;
- metrics + uncertainty, drift by instrument/regime, costs;
- artifact hashes, model card, limitations, approval status.

Стандарты отчёта: `reproducible=true/false`, performance vs baseline with CI; balanced reporting failures, no unverified «accuracy» claims. Optimization multiple comparisons: out-of-sample holdout and correction (Deflated Sharpe, SPA/Reality Check), no reuse untouched holdout for tuning.

## 7. Исследовательские модули как плагины

Контракты:
```text
IResearchDatasetProvider.Export(snapshot_id, query_spec) -> parquet + manifest
IFeatureBuilder.Build(dataset, feature_spec, cutoff_policy) -> features + lineage
ILabelBuilder.Build(events, label_spec) -> labels + maturity_dates
IExperimentRunner.Run(config, immutable_dataset) -> model_run + metrics
IModelRegistry.Publish(model_run, model_card, approval_state)
```

В Python: pandas/polars, pyarrow, DuckDB, scikit-learn, optional lightgbm/catboost; зависимостями управляет lockfile, всё ограничено resource quota и local permissions. Доменный C# API предоставляет snapshot export без торговых секретов. A/B comparison и backtests — отдельные исследовательские модули.

## 8. Data governance

- Personal trade history приватна; в GitHub только synthetic and anonymized fixtures.
- Лицензии T-Invest market data и правила обработки данных проверять до экспорта/публикации; ретрансляция запрещена без права.
- Notebook не имеет broker token; без сетевого доступа по умолчанию, импорт только экспортированных снапшотов.
- Модели и датасеты с финансовой историей не публиковать публично без явного разрешения.
- Логи доступа и экспортов, data retention, безопасное удаление локальных копий при запросе.

## 9. Оценка экономической полезности

Метрики модели отдельно от экономических:
- classification: Brier, log loss, calibration slope, AUC/PR-AUC, threshold utility;
- regression: MAE/Huber/quantile loss, interval coverage;
- strategy: net P&L, risk-adjusted return, drawdown, transaction costs, number of independent days, confidence bands;
- operational: model latency, CPU/RAM, false alerts, stability, retrain cost;
- sensitivity: by instrument, spread, session, book gap, volatility regime, period and bot version.

Особенно важно оценить **expected value net of fees/slippage and capital usage**. 95% прогнозирования направления не гарантируют прибыль. Counterfactual fill depends on execution constraints; non-observed fills cannot be used as if they were observed labels.

## 10. Acceptance criteria / этапы

- M9: reproducible Parquet export and immutable manifest; point-in-time join tests; data coverage dashboard; known gaps explicitly encoded.
- M10-A: 3 baseline models + exact chronological split + no-leakage automated tests + metrics by holdout.
- M10-B: one anomaly detector produces interpretable alert with source trace and false-positive measurement.
- M10-C: fill probability study includes censored order scenarios and calibration plot, no unverified execution assumptions.
- M10-D: compare with baseline on untouched out-of-sample and state *no statistically demonstrated benefit* when evidence insufficient.
- Promotion from experimental model to risk/advisory: frozen version + model card + shadow evaluation; execution control is out of scope.

## 11. Вдохновляющие исследовательские направления

- Transaction cost analysis/market microstructure: Joel Hasbrouck, *Empirical Market Microstructure*; market-impact literature (Almgren–Chriss), with caution applicability to maker/pro-rata strategies.
- Statistical pitfalls: Bailey & López de Prado, *Deflated Sharpe Ratio*; White's Reality Check; Hansen's SPA test; cross-validation with overlapping labels.
- Survival analysis for time-to-fill, censored orders; hypothesis testing under clustered intraday data.
- Биржевая microstructure документация и официальные matching rules используются при разработке симулятора; сам факт наличия крупного видимого уровня не доказывает намерения его владельца или существование уникального «робота».
