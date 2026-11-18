# 10. Научные исследования и реализуемая программа экспериментов

**Аудит:** 18.11.2026. Дата написания, публикация/версия и статус peer-review различаются. Методы из NASDAQ, FX и crypto **нельзя автоматически считать доказанными для MOEX/SPB**: market matching, pro-rata, tick size, latency, доступная глубина и состав потока могут отличаться.

Цель документа: из каждого академического результата получить **конкретную измеряемую гипотезу**, метрику, требование к данным, тест против тривиального baseline и критерий отбраковки. Анализ собственных роботов и P&L от брокера остаётся отдельной truth source; paper не заменяет финансовую сверку.

## 1. Матрица исследований: что именно добавить в продукт

| ID / статус | Исследование (прямая ссылка) | Идея и результат работы | Практическое применение в Analytics | Данные / ограничения | Этап |
|---|---|---|---|---|---|
| **P01 [peer-reviewed, 2014]** | Rama Cont, Arseniy Kukanov, Sasha Stoikov, **The Price Impact of Order Book Events**, Journal of Financial Econometrics, DOI [10.1093/jjfinec/nbt003](https://doi.org/10.1093/jjfinec/nbt003), [arXiv](https://arxiv.org/abs/1011.6402) | Order flow imbalance (OFI) на лучшем bid/ask объясняет короткий price impact лучше грубого signed volume в изученных данных | Собирать OFI и его связь с последующим движением цены, adverse selection после passive fills | Нужны event-level bid/ask, quotes/orders/trades; после определённой частоты snapshots OFI становится приближением | M7/M9 |
| **P02 [peer-reviewed, 2015]** | Weibing Huang, Charles-Albert Lehalle, Mathieu Rosenbaum, **Simulating and Analyzing Order Book Data: The Queue-Reactive Model**, JASA, DOI [10.1080/01621459.2014.982278](https://doi.org/10.1080/01621459.2014.982278) | Потоки limit, cancel и market orders зависят от состояния очередей; LOB можно моделировать state-dependent jump process | Event intensity features по уровню, восстановление объёма/исчезновений больших заявок, feed gap detectors | Биржевые правила matching важны; snapshot-only data не всегда позволяют идентифицировать интенсивности отдельных типов событий | M7/M10 |
| **P03 [peer-reviewed, 2001]** | Robert Almgren, Neil Chriss, **Optimal Execution of Portfolio Transactions**, The Journal of Risk, DOI [10.21314/JOR.2001.041](https://doi.org/10.21314/JOR.2001.041) | Trade-off volatility risk vs execution cost / temporary and permanent impact | Cost-vs-risk frontier, TWAP/POV arrival benchmark, большой parent order | Большие metaorders и price-impact предположения не равны пассивному маркетмейкингу с pro-rata | M7/M10 |
| **P04 [1988, классический TCA]** | André Perold, **The Implementation Shortfall: Paper versus Reality**, [переиздание](https://www.degruyterbrill.com/de/document/doi/10.1515/9781400829408-014/html) | Разница между желаемой сделкой по decision price и реально полученным исполнением с учётом неисполненного остатка | Execution shortfall: delay, spread/impact, opportunity, explicit fees; per order и per bot | Определить decision/arrival time и valuation of unfilled remainder; без этих цен метрика неполная | M7 |
| **P05 [peer-reviewed, 2022]** | Maglaras et al., **A deep learning approach to estimating fill probabilities in a limit order book**, Quantitative Finance, DOI [10.1080/14697688.2022.2124189](https://doi.org/10.1080/14697688.2022.2124189) | Time-to-fill как случайная величина, зависит от состояния LOB, RNN оценивает время/вероятность исполнения | Начать с эмпирических Kaplan-Meier / Cox и простой логистической модели; затем нейросеть при наличии данных | Цензурированные заявки (cancel/expiry) нельзя маркировать «точно не исполнились бы» | M9/M10 |
| **P06 [peer-reviewed, 2023/24]** | Alvaro Arroyo, Alvaro Cartea, Fernando Moreno-Pino, Stefan Zohren, **Deep Attentive Survival Analysis in Limit Order Books**, [arXiv 2306.05479](https://arxiv.org/abs/2306.05479), [журнал DOI 10.1080/14697688.2023.2286351](https://doi.org/10.1080/14697688.2023.2286351) | Dynamic time-to-fill survival model, proper scoring rules, attention/convolution; right-censoring | Собирать `time_to_first_fill`, `time_to_complete`, censoring reason, rolling LOB features. Считать integrated Brier/log-likelihood/calibration, не только ROC AUC | В статье используются Nasdaq и price-time priority; pro-rata requires refit/specific data | M9/M10 |
| **P07 [preprint; arXiv 2024, rev 2026]** | Felix Lokin, Fenghui Yu, **Fill Probabilities in a Limit Order Book with State-Dependent Stochastic Order Flows**, [arXiv 2403.02572](https://arxiv.org/abs/2403.02572) | Semi-analytical fill probabilities на лучших котировках и глубже в книге до сдвига mid | Baseline probability by depth, size, imbalance; compare with empirical survival, test on actual own resting orders | Статус публикации проверить отдельно; paper uses FX spot data; не переносить параметры непосредственно | M10 |
| **P08 [peer-reviewed, 2019]** | Zihao Zhang, Stefan Zohren, Stephen Roberts, **DeepLOB: Deep Convolutional Neural Networks for Limit Order Books**, [arXiv 1808.03668](https://arxiv.org/abs/1808.03668), [авторский код](https://github.com/zcakhaa/DeepLOB-Deep-Convolutional-Neural-Networks-for-Limit-Order-Books) | CNN/Inception/LSTM для краткосрочного midprice direction из LOB | Отдельный optional benchmark классификации рыночного направления/режима, сравнить с OFI logistic baseline | У части backtest в самой статье упрощающая цена исполнения mid и gross returns до fees: не доказательство исполнимой прибыли | M10 |
| **P09 [peer-reviewed, 2023]** | Petter N. Kolm, Jeremy Turiel, Nicholas Westray, **Deep Order Flow Imbalance: Extracting Alpha at Multiple Horizons from the Limit Order Book**, [Mathematical Finance DOI 10.1111/mafi.12413](https://doi.org/10.1111/mafi.12413), [SSRN](https://doi.org/10.2139/ssrn.3900141) | OFI features на разных горизонтах + sequence models для short-horizon forecasts | Multi-horizon features (1s/5s/30s/1m) с embargo и блокированным time-split, сравнить модели | Horizon-dependent leakage, stale books, много коррелированных горизонтов | M9/M10 |
| **P10 [preprint, 2023/rev 2024]** | **Tackling the Problem of State Dependent Execution Probability**, [страница исследования](https://ideas.repec.org/p/hal/wpaper/hal-04161957.html), [arXiv 2307.04863](https://arxiv.org/abs/2307.04863) | State-dependent execution probability via high-frequency features/survival, passive vs aggressive placement trade-off | Decision policy research: probability of fill vs cost after fees; model interpretation | Версию и точное название сверять по версии рукописи; исполнение в данном режиме рынка отличается от СПБ | M10 |
| **P11 [preprint/SSRN]** | David H. Bailey, Marcos López de Prado et al., **The Deflated Sharpe Ratio**, [SSRN DOI 10.2139/ssrn.2460551](https://doi.org/10.2139/ssrn.2460551) | Sharpe после многочисленных тестов завышен из-за selection bias, non-normality | Каждый перебор параметров робота записывать в experiment registry; отчёт DSR/number of trials | Показатель не заменяет независимую live validation; estimator depends on effective number of trials | M9/M10 |
| **P12 [peer-reviewed, 2017]** | Bailey, Borwein, López de Prado, Zhu, **The Probability of Backtest Overfitting**, [университетская публикация](https://escholarship.org/uc/item/4w1110bb), [авторская версия](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) | CSCV / PBO: вероятность того, что выбранная стратегия переоптимизирована | Controlled parameter sweeps and out-of-sample rank degradation; report false-discovery risk | CSCV с последовательными time segments требует careful time dependency and embargo | M10 |
| **P13 [peer-reviewed, 2024]** | **Backtest overfitting in the machine learning era: A comparison of out-of-sample testing methods in a synthetic controlled environment**, Knowledge-Based Systems, DOI [10.1016/j.knosys.2024.112477](https://doi.org/10.1016/j.knosys.2024.112477) | Сравнение методов OOS-проверки в контролируемой синтетике; CPCV показывает преимущества в исследованных условиях | Сравнивать rolling/purged/CPCV, не объявлять один splitter универсально лучшим | Результаты на синтетических контролируемых данных не гарантируют такого же поведения на собственной истории | M10 |

Для документов с `peer-reviewed` проверен журнал/DOI, для preprint отдельно указан статус; новые редакции arXiv не следует путать с первоначальной датой.

## 2. Подтверждённые репозитории исследовательских инструментов

| Назначение | Реализация | Конкретный пример/вход | Ограничение |
|---|---|---|---|
| OFI / влияние потока на цену | [sjmagill01/ofi-price-impact](https://github.com/sjmagill01/ofi-price-impact) | Репликация Cont–Kukanov–Stoikov на TAQ, OOS alpha search | Исследование на американских данных; никакого API учёта брокерских денег |
| Ещё один OFI пример | [bhardwaj-kunal/order-flow-imbalance](https://github.com/bhardwaj-kunal/order-flow-imbalance) | Расчёт признаков и linear price impact | Проверить raw input и качество данных перед доверием к результатам |
| Книга/очередь/latency | [nkaz001/hftbacktest](https://github.com/nkaz001/hftbacktest) / [Order Fill models](https://hft.readthedocs.io/en/latest/order_fill.html) | L2/ L3 replay, queue models, exchange/order latency | FIFO models не являются реализацией pro-rata; missing queue data |
| Synthetic LOB / TCA | [crollila/execution-microstructure-lab](https://github.com/crollila/execution-microstructure-lab) / [metrics.py](https://github.com/crollila/execution-microstructure-lab/blob/main/src/executionlab/metrics.py) | Пять сценариев execution и implementation shortfall | Dataset синтетический, корректность на бирже не доказана |
| Shortfall/impact | [DaniyalMlk/slippage](https://github.com/DaniyalMlk/slippage) / [shortfall.py](https://github.com/DaniyalMlk/slippage/blob/main/src/slippage/shortfall.py) | `ShortfallBreakdown`, spread/trading/delay/opportunity | Конвенция декомпозиции должна быть версионирована |
| Multi-agent simulation | [abides-sim/abides](https://github.com/abides-sim/abides) / [Wiki](https://github.com/abides-sim/abides/wiki/) | Agent-based market simulation и counterfactual | Синтетическая causal модель не подтверждает реальную fill ratio |
| Deep LOB model | [авторский DeepLOB notebook](https://github.com/zcakhaa/DeepLOB-Deep-Convolutional-Neural-Networks-for-Limit-Order-Books) | FI-2010 order book benchmark | Не ML на собственных данных, пока нет point-in-time book store |
| Research pipeline | [microsoft/qlib](https://github.com/microsoft/qlib) / [high frequency test](https://github.com/microsoft/qlib/blob/main/tests/backtest/test_high_freq_trading.py) | Train/backtest/analysis and nested execution workflows | Не источник достоверного реального P&L брокера |
| Statistic reports | [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats) / [stats.py](https://github.com/ranaroussi/quantstats/blob/main/quantstats/stats.py) | Sharpe/Sortino/max drawdown | Только по корректной time-series доходности |
| OOS / purge | [DaniyalMlk/holdout](https://github.com/DaniyalMlk/holdout) / [splits.py](https://github.com/DaniyalMlk/holdout/blob/main/src/holdout/splits.py) | `purged_kfold`, `walk_forward`, DSR/PBO | Молодая реализация; аудит тестов и лицензии перед применением |

## 3. Программа экспериментов: конкретные hypothesis cards

### EXP-01. Влияет ли OFI на adverse selection по нашим пассивным заявкам?

**Вопрос:** при одинаковом инструменте/режиме/времени, после нашего passive fill, коррелируют ли уровни OFI до исполнения с side-adjusted future markout и чистым spread capture?

**Данные:** bid/ask event stream, sell/buy signed flow, собственные fills, timestamps, observation gaps, quote bid/ask at decision and after fill, associated bot ID. **Неполный L2 -> feature coverage flag.**

**Признаки:** OFI на 0.5/1/5/30 сек, spread ticks, normalized imbalance, relative order size, target level, time since last quote update.

**Цель:** future signed markout 1/5/30 секунд, минус комиссии; negative adverse selection labeling must use consistent sign.

**Baseline:** unconditional mean markout by instrument/hour and simple OFI linear regression. Candidate: ridge, gradient boosting.

**Валидация:** chronological walk-forward grouped by day, embargo max label horizon, quality gating for gaps. Compare MAE and classification utility net costs; false discovery adjustment for many horizons.

**Pass:** OOS improvement with CI and stable sign across days/instruments. **Fail:** нестабильность, нет independent observations, low quote coverage.

### EXP-02. Вероятность исполнения заявки для разных уровней (плита 50 vs 100)

**Вопрос:** насколько глубина, размер собственного ордера и размер крупного чужого уровня влияют на `P(fill within T)`?

**Данные:** *все выставленные*, а не только исполненные заявки, order lifecycle, size, price, book snapshot, cancel reason, event times. Включать disabled/unfilled orders; не обучать только на победителях.

**Survival sample [DESIGN]:**
```text
order_id, decision_time, observed_t_end, event_occurred, event_type,
requested_qty, partial_filled_qty, price_level, relative_spread_ticks,
level_displayed_qty, target_large_order_qty, venue_matching_rule_version,
bot_version, book_gap, features_available_at
```
`event_occurred`: first fill/full fill in зависимости от отдельного target. Cancel/expiry -> censoring; cancel по решению алгоритма может быть **informative censoring**, поэтому baseline sensitivity. Partial fills — отдельная competing-event модель или volume-weighted estimation с явной интерпретацией.

**Baseline:** empirical fill ratio в bin(time,spread,level,qty), Kaplan-Meier или Cox, logistic per horizon. Candidate: survival forest, gradient boosting hazard, Transformer только при достаточном OOS и стабильном live feed.

**Метрики:** IPCW Brier / integrated Brier (при валидной модели censoring), log-likelihood, calibration by decile, error by depth, coverage/missingness. Не использовать только ROC AUC: он не проверяет временную калибровку.

**Ограничение:** pro-rata settlement и скрытый состав стакана не позволяют считать публичный объём полной информацией о вероятности собственного исполнения.

### EXP-03. Качество выставления/перестановки собственной заявки

**Вопрос:** сколько spread capture теряется из-за многократных cancel/repost, сколько реально связано с исполненной отменой и stale book?

**Данные:** decision, requested cancel, broker ack/reject, full/partial fills, reconnect state, quote age, own best-level movement, bot parameters.

**Метрики:** cancels per filled unit, quote life, request→ack latency, canceled-then-filled race rate, average net P&L by target-level and configuration, per active trading minute.

**Baseline:** режим без перестановки (только counterfactual with conservative fill model); real observed revenue separately. Заблокировать claims о гипотетических fills без данных о реальном matching.

**Pass:** статистически и экономически заметная экономия cost при равных условиях, без ухудшения риска; иначе только descriptive analytics.

### EXP-04. Зависимость прибыльности роботов от состояния рынка

**Гипотеза:** робот A лучше B при определённых spread/volatility/liquidity, но эффект остаётся при сопоставимых торговых днях, версиях роботов и капитале.

**Данные:** paired day/instrument/venue, bot run/config SHA, exposure, VM/fees, chosen risk basis, offline market features.

**Baseline:** per-day net P&L / gross exposure; volatility-normalized; within-day paired difference. Candidate: hierarchical mixed effects, gradient boosting conditional expectancy.

**Валидация:** block bootstrap by day, OOS by time and instruments, PBO/DSR for parameter search; report count of *independent days* not just execution count.

**Pass:** positive OOS difference after cost and CI, no cherry picking across configs.

### EXP-05. Результат адаптации параметров как задача с множественным тестированием

**Дано:** десятки/сотни конфигураций target-level, spread threshold, min other volume, replace cooldown, max order size.

**Требование:** регистрировать **каждый** запуск конфигурации, seed, date range, data version, # trials; замораживать holdout; отчёт PBO/DSR/robustness. Даже лучшая in-sample стратегия — лишь кандидат.

**Baseline:** fixed parameters from production robot; variants compare under same costs/latency/market simulation assumptions.

**Pass:** OOS result better by economically meaningful margin with uncertainty; при отсутствии — reject or shadow only.

### EXP-06. Anomaly detection в учёте брокера

**Дано:** необычная комиссия, FX jump, ставка VM, внезапный отрицательный остаток, несвязанные операции, дублирование aggregate margin.

**Baseline:** детерминированные ledger conservation and control assertions — **приоритетнее ML**. ML anomaly detection поверх них для «необычно, но формально валидно» (robust rolling median, isolation forest).

**Pass:** high precision manual triage, explainable source trace and low false positive; не блокировать отчёты, не объявлять нарушение по одиночному алерту.

## 4. Дорожная карта по данным (чтобы исследования были возможны)

| Уровень данных | Можно честно делать | Нельзя заявлять |
|---|---|---|
| Только сделки/операции | realized P&L, комиссии, FIFO, дневной денежный VM, без полноценного mark-to-market | точный arrival-price shortfall, шансы исполнения не выставленных заявок |
| + исторические котировки | mark-to-market as-of (при наличии подходящей цены), approximate slippage and regime stats | очередь, точное время попадания в стакан |
| + собственные заявки/ACK/decision logs | fill ratio, cancellation races, attributable P&L, decision-to-fill latency | контрфактический fill с 100% уверенностью |
| + L2 с event gaps и синхронизацией часов | OFI-like indicators, imbalance, spread capture, conditional fill estimates | индивидуальные очереди участников, скрытые заявки |
| + L3/order-by-order feed и matching spec | более точный event replay, queue modeling и causal studies | гарантированная точность, если exchange latency или hidden order rules неизвестны |
| + многолетняя качественная история | out-of-sample ML с достаточными событиями | универсальная успешность на новых режимах рынка |

## 5. Протокол воспроизводимого эксперимента

```yaml
id: EXP-02-2026-11
hypothesis: "pre-fill book imbalance predicts 30s fill probability"
entity: own_limit_order
prediction_origin: order_submit_utc
features_available_at_max: order_submit_utc
target: first_fill_within_30_seconds
censoring: cancel_or_expiry
data_sources:
  - own_bot_logs
  - broker_order_events
  - l2_snapshots
venue_matching_rule: versioned_external_reference
split: grouped_chronological_walk_forward_with_purge
baseline: empirical_bin_fill_probability
candidate: calibrated_gradient_boosted_survival
metrics:
  - integrated_brier_score
  - calibration_by_depth
  - log_likelihood
  - effective_trading_days
quality_gates:
  - minimum_book_coverage
  - no_future_feature
  - resolved_order_ids_or_unknown_flag
output:
  - dataset_manifest_sha256
  - model_card
  - out_of_sample_report
  - failure_cases
```

Это **шаблон**, не выполненный опыт. Конкретные thresholds для coverage и sample-size подбираются до запуска в pre-registration, не после просмотра результатов.

## 6. Правила научной корректности

1. Не смешивать `observed_fill`, `model_predicted_fill`, `hypothetical_fill`: в финансовом ledger попадают только наблюдаемые/сверенные экономические события.
2. Разделять данные в момент решения (`available_at`) и то, что стало известно позже (`event_time`, `observed_at`, `settled_at`).
3. Документировать selection bias: исполнившиеся заявки, только прибыльные закрытые позиции, игнорирование отменённых и неисполненных заявок.
4. Не использовать срезы будущего рынка при выборе features: `future_midprice` — label, а не feature.
5. Не обучать на данных одной версии робота и оценивать на другом без сведения account/venue/config/lot sizes.
6. Для временных рядов использовать блоки/группы независимости; сотни partial fills в один день не равны сотне независимых наблюдений.
7. Указывать gross/net, комиссии и проскальзывание; полезность классификации цены не равна полезности торговли.
8. Не считать model-fit и paper-replication доказательством продакшен-доходности.
9. Перед публикацией данных/кода соблюдать правила лицензий биржевых котировок и PII конфиденциальность.
10. Каждая ML-гипотеза имеет простую baseline, заранее заданный holdout, требования к качеству и сценарий «влияние не обнаружено».

## 7. Новые обязательные задачи для roadmap

- **SCI-01 [M7]**: сохранить *собственные* submit/cancel/ACK/fill события, а не только executed fills; без этого EXP-02 запрещён.
- **SCI-02 [M7]**: feature extractor OFI/imbalance с quality flags и tests на gaps.
- **SCI-03 [M7]**: shortfall decomposition per parent order (decision/arrival/unfilled/fees).
- **SCI-04 [M9]**: label intervals и right-censoring registry, не обучать fill predictor без него.
- **SCI-05 [M9]**: experiment manifest и immutable dataset snapshot с `available_at`.
- **SCI-06 [M10]**: baseline fill probabilities по времени, ликвидности и размеру с калибровкой.
- **SCI-07 [M10]**: PBO/DSR и отчёт обо всех перебранных настройках.
- **SCI-08 [M10]**: microstructure simulator matching rules as configurable policy; pro-rata отдельно, no FIFO substitution.
- **SCI-09 [M10]**: paper replication optional only after local data; validate live/offline differences.
- **SCI-10 [M10]**: field tests with conservative shadow mode, без отправки торговых приказов из Analytics.

Связанные инженерные файлы/алгоритмы — [09-open-source-implementation-audit.md](09-open-source-implementation-audit.md), приёмка — [07-roadmap-and-acceptance.md](07-roadmap-and-acceptance.md).
