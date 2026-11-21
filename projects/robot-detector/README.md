# Market Robot Detector — самостоятельный проект внутри Analytics

**[Единый живой научный план и подробное ТЗ](docs/MASTER_RESEARCH_PLAN.md)** —
что уже доказано, что предстоит проверить, как выбирать,
пересматривать и обосновывать следующие исследования.
Обязателен для всех агентов и почасовых продолжений;
см. также [AGENTS.md](AGENTS.md) и
[текущий checkpoint](research/autonomy_state.json).

## Цепочка научных этапов: работа продолжена после checkpoints

- [Аудит малой мощности и парного сравнения двух классификаторов](
  docs/ABIDES_MATCHED_UNCERTAINTY_20261121.md):
  при четырёх синтетических seeds на одну
  когорту даже **0/4** ошибок допускает
  номинальную верхнюю 95% CP границу **0,6024**,
  а **4/4** удачных случаев — нижнюю **0,3976**
  (лишь под IID simulator assumptions). Один
  grouped TWAP miss; улучшения нет.
  Продолжение: [#96](https://github.com/IskanderAbdullin/Analytics/issues/96).

- [Новый genuine ABIDES 16-run эксперимент: по prints и по exact timestamp](docs/ABIDES_PUBLIC_CLUSTER_COMPARISON_20261121.md):
  **16 142** исполнений, **14 801** уникальных timestamps,
  61 posthoc TWAP fills. Naive print 4/4 TWAP, grouped
  3/4 TWAP, Poisson false alarm 1/4 у **обоих** методов.
  Нет специфичностного улучшения; следующий научный
  этап [#95](https://github.com/IskanderAbdullin/Analytics/issues/95).

- [Точный conditional toy-null размера timestamp-кластера](
  docs/PUBLIC_CLUSTER_SIZE_CONDITIONAL_NULL_20261121.md):
  при **13** неизменных публичных timestamps и
  мультимножестве размеров кластеров
  **12×1 + 1×100** наивное print ratio даёт
  **2/13 ложных тревог** в строго synthetic toy
  перестановках; grouped timestamps дают **0/13**.
  Это **не** реальная рыночная FDR.
  Следующий этап: genuine ABIDES [#94](
  https://github.com/IskanderAbdullin/Analytics/issues/94).

- [Фиксированные фазы и псевдорепликация частичных исполнений](
  docs/PUBLIC_PHASE_TIED_FILLS_NEGATIVE_20261121.md):
  **13** уникальных timestamps; после 100 prints
  с одним timestamp naïve ratio вырос
  **0,1667 → 8,4167** без target. Grouped
  timestamps возвращают исходный результат;
  ±300 ms нарушают 250 ms допуск (ABSTAIN).
  Следующий conditional null [#93](
  https://github.com/IskanderAbdullin/Analytics/issues/93).

- [16-run genuine ABIDES split-half momentum robustness](
  docs/ABIDES_SPLIT_HALF_MOMENTUM_20261121.md):
  **3/4 TWAP alarms** и 1/4 abstain, во всех
  трёх фонах 0 false alarms, но по одному abstain.
  По сравнению с исходным ratio на тех же
  seeds улучшение специфичности не показано;
  произошло **снижение покрытия**.
  Этап #92 подтверждён source-free CI, текущая задача — #93.

- [Новый независимый ABIDES 16-run ratio baseline и отрицательные momentum-контроли](
  docs/ABIDES_BACKGROUND_RATIO_HOLDOUT_20261121.md):
  **4/4 TWAP обнаружены** при 74 posthoc-fills,
  **0/8** ложных тревог на Poisson/fixed-20s,
  но **2/4 ложных тревоги** на momentum-фоне.
  Не real-market FDR. Следующий этап — #91.

- [Проверено математическое aliasing 20s фоновой стратегии с 45s clock grid](
  docs/PUBLIC_CLOCK_ALIASING_NEGATIVE_20261121.md):
  при полном отсутствии TWAP **1/9** фоновых событий
  попадает в «TWAP-подобную» 45s сетку; подмена
  detector specificity невозможна. Новый ratio
  baseline выбран **после** старых 2901–2903,
  предзарегистрирован **до** новых 3001–3004 и
  ждёт независимой симуляционной проверки.

- [ABIDES genuine 12-run multiscale и L2, отрицательная переносимость](
  docs/ABIDES_MULTISCALE_PUBLIC_L2_20261121.md):
  на seeds 2901–2903 **67** posthoc TWAP fills;
  fixed-20s фон без target дал **0,0820**
  доли на 45s сетке против **0,0302** у TWAP,
  а legacy 10s baseline **3/3** ложно сработал
  на fixed-noise и **3/3** пропустил TWAP.
  Следующий этап — анализ harmonic aliasing и holdout #90.

- [Независимый genuine ABIDES-NG тест переносимости](
  docs/GENUINE_ABIDES_FIXED_CLOCK_TRANSFER_20261121.md):
  заранее зафиксированный 10-секундный детектор дал
  **2/2 ложных тревоги** на регулярном фоне
  и **2/2 пропуска** на genuine injected TWAP
  (29 подтверждённых controlled executions).
  Это отрицательный результат: clock grid не
  идентифицирует целевого исполнителя.

- [Ключевой hard-negative результат публичной
  10-секундной регулярности](
  docs/TOY_PUBLIC_EXECUTION_RHYTHM_HARD_NEGATIVE_20261121.md):
  **4/4 ложных тревог** на периодическом
  синтетическом фоне без target, при **4/4**
  истинных срабатываниях в positive toy-case;
  публичные ленты отрицательных периодических
  и положительных случаев совпадают. Из одного
  ритма нельзя доказать наличие конкретного робота.

- [Воспроизводимость одним offline-командным запуском](
  docs/OFFLINE_REPRODUCIBILITY_20261121.md):
  **14 наборов / 113 synthetic/offline tests**
  по оригинальным исходникам плюс 8 агрегатных
  source/provenance fixtures без скачивания рынка.
  Отдельный network replay нужен только для
  оригинальных vendor файлов; offline CI не
  является независимой real-market валидацией.

- [Проверка качества source/L2 и запрет недоказанной полноты](
  docs/EXCHANGE_L2_COVERAGE_ABSTENTION_20261121.md):
  абсолютная нумерация сообщений требуется для покрытия;
  без неё реальный источник остаётся **UNKNOWN**, а
  пропуски или несогласованные snapshots — **ABSTAIN**,
  не «роботов нет». Пример 5/5 vs 4/5 синтетических
  событий отличает полный oracle source от разрыва.

- [Исторический 10-уровневый NASDAQ L2 event-time replay](docs/LOBSTER_EVENT_TIME_FEATURES_20261121.md):
  **269 748** настоящих пар событий/стакана,
  исходный source-анализ успешно подтверждён.
- [Ретроспективное время vs количество событий](docs/LOBSTER_CLOCK_VS_EVENT_WEIGHTING_20261121.md):
  event-weighted spread **1308,62**, clock-weighted
  **1284,85** в единицах цены ×10000. Ошибка выбора
  знаменателя реальна; контрольные тесты исключают
  lookahead и фиктивное время вне наблюдения.
- [Контрпример неидентифицируемости владельца](docs/SYNTHETIC_L2_OWNER_NONIDENTIFIABILITY_20261121.md):
  две синтетические реальности с одинаковыми
  шестью публичными событиями и всеми 10 уровнями
  стакана, но **одним и тремя приватными
  владельцами**. Следовательно, уникальное
  число владельцев не восстанавливается по
  публичному order reference без дополнительных меток.
  Это не препятствует исследованию наблюдаемых
  алгоритмических паттернов.

После каждого этапа агент выбирает и начинает
следующий, а master issue #72 остаётся открытым.
Текущий этап определяется **только** актуальным
[checkpoint](research/autonomy_state.json), а не историческим
списком выше. Пререгистрированный 12-run ABIDES multiscale
эксперимент [#89](https://github.com/IskanderAbdullin/Analytics/issues/89)
**успешно выполнен**, его **отрицательные результаты**
подтверждены. Источник #90 теперь успешно проверен на исходных
16 matching-engine runs. Исходные проверки #90 и #91 завершены с сохранением
отрицательных результатов. Следующий этап —
[public phase/split-fill robustness #92](
https://github.com/IskanderAbdullin/Analytics/issues/92).
Фактический current_stage всегда в checkpoint.

## Постоянная исследовательская программа и автоматическое продолжение

**Конечная цель:** открытая воспроизводимая научная система
обнаружения наблюдаемых алгоритмических торговых паттернов
в публичных сделках и L2 с честными negative controls,
проверкой устойчивости и явной неопределённостью.
Число коммитов, зелёный CI и успешная проверка одной
гипотезы не означают завершения проекта.

- [ТЗ автономного многоэтапного выполнения](docs/AUTONOMOUS_RESEARCH_TZ.md)
- [Checkpoint: фактическое состояние и NEXT_ACTION](research/autonomy_state.json)
- [Открытый контрольный issue #72](https://github.com/IskanderAbdullin/Analytics/issues/72)

После каждого этапа агент фиксирует результат, тесты и commit/push,
пересматривает приоритеты и **сразу начинает следующий этап**
в пределах активного запуска, без временного отчёта.
При завершении запуска оставляет воспроизводимый checkpoint:
следующий агент не должен выяснять заново, на чём остановилась работа.
Исследование может продолжаться отдельными **почасовыми
запусками планировщика**. Каждый запуск восстанавливает
актуальный GitHub state; между запусками программа
не обязана физически исполняться. Не выдавать
сам факт расписания за подтверждённый результат.

## Historical NASDAQ real 10-level L2 format validation — demo only

[Original official LOBSTER public AMZN 10-level sample
format test](https://github.com/IskanderAbdullin/Analytics/actions/runs/44922750898)
successfully audited **269,748** event-aligned NASDAQ
historical AMZN limit-order book state pairs for
**2012-06-21**, with 6-field event messages and
40-field post-event L2 quotes. Sample includes
**8,974 visible resting-order executions**, **2,445 hidden
executions**, **27,557 best-quote changes**, and
**8,483 adjacent events with equal exchange timestamps**.

**The completed stage is structural and format QA only, not
a robot-detector performance test.** The vendor
[explicitly publishes demonstration samples](
https://php.lobsterdata.com/info/DataSamples.php) and research
examples. Its separate [contractual academic subscription terms](
https://php.lobsterdata.com/termsAndConditions.php) do not, by
themselves, prohibit **noncommercial scientific experiments
with publicly downloadable sample files**. Further exploratory
research with these demos and publication of OUR code,
aggregate statistics and figures is therefore **not blocked
solely for lack of a paid subscription**. We do not claim
that raw source redistribution, commercial use or additional
subscription datasets are openly licensed. The original
**4.8MB compressed** demo ZIP was NOT committed to GitHub
or uploaded as a workflow artifact, only compact metadata.
We calculated a local original ZIP SHA-256 but the
vendor does **not** provide a published/signed checksum
for independent authentication. The 2012 data are
historic reconstruction with only **10 occupied price
levels per side**, not full-depth current L2.

The [source contracts and full original event-type counts
are documented](docs/LOBSTER_AMZN_PUBLIC_SAMPLE_FORMAT_AUDIT_20261121.md).
The paired event/book structural validator
`tools/lobster_public_sample_format_audit.py`
runs on Python stdlib, with synthetic no-network negative
tests. The once-successful public CI source fetch is
**manual-only** thereafter, while cheap parser tests run on push.

## Extended source-verified real spot print panel: 776,007 public executions

The project has verified **8 independent exchange daily SPOT public trade
source archives** from Binance Vision: **LTCUSDT and BCHUSDT** on
**each UTC day 2026-11-17 through 2026-11-20**, totalling **776,007
public executions** (LTC 581,371; BCH 194,636). The four observed
daily public trade-ID ranges are exactly consecutive for each symbol,
and every original provider ZIP passed its published SHA-256 check.
This is **provider dataset continuity**, not independent proof every
matching-engine event was captured, and not full L2.

The frozen stronger null preserves whole equal-timestamp-side-vector
execution groups inside one-minute shuffle controls and separately
conditions on **>=5 public trades per complete 30s bin**.
Results are **not transferable uniformly across markets**.
For BCHUSDT, original phase-0 five-print minimum source days
Nov17/18/19/20 observed one-sided counts **504/610/541/334**,
versus strong-null eight-shuffle maximums **519/626/539/343**:
only **Nov19** exceeds the eight-controls envelope.
The two new BCH Nov18–19 sources were fixed before inspection:
one failed and one narrowly passed. A selected 20s alternative
phase must **not** replace the fixed primary 0s outcome.

[Four-day BCH panel, original source links, full per-origin stats,
licensing and negative results](docs/BCH_FOUR_DAY_OCCUPANCY_PANEL_20261121.md)
· [Exact 17 Nov five-print occupancy protocol](docs/REAL_SPOT_OCCUPANCY_TRANSFER_20261117.md)
· [Earlier LTC/BCH real 20 Nov transfer](docs/REAL_SPOT_PRECOMMITTED_TRANSFER_20261120.md).

**No actual robot owner truth, real-market accuracy/FDR, independent
complete historical L2 or commercial trading entitlement.** Binance
Vision source data is noncommercial research use only under
CC BY-NC-SA 4.0/provider terms. All original source-acquisition
GitHub Actions were converted to **manual-only** after their
successful original runs, with tiny aggregate-only artifacts.
The authorized Windows PC-Agent was not needed for these small,
bounded experiments.

## Real-public-trade negative controls: clock and partial-fill preservation

**Executed twice on the same two inspected real LTCUSDT UTC days.**
Research-only per-print within-minute side shuffling initially left
observed one-sided 30s intervals far above its weak background.
A second, more conservative control shuffled whole equal-size,
equal-timestamp execution side-vector clusters instead. With the
original 30-second origin, the **eight-control medians** rose from
**74 to 136.5** (2026-11-18) and from **58.5 to 105**
(2026-11-19), while real counts were **173 and 135**.
This demonstrates the importance of preserving split-fill
clustering before interpreting time-series concentration.
Eight permutations of two previously inspected days are **not**
calibrated significance, FDR, causal inference or physical
owner detection. [Frozen source provenance, all six clock offsets
and limitations](docs/REAL_PUBLIC_SPOT_TRADE_ARCHIVE_2026-11-21.md).

[Weak control original CI #44918585645](https://github.com/IskanderAbdullin/Analytics/actions/runs/44918585645)
and [stronger cluster-preserving original CI #44919058627](https://github.com/IskanderAbdullin/Analytics/actions/runs/44919058627)
both succeeded. The original source ZIP checksums match both
original providers' audited archives. All expensive repeated
source-fetch workflow schedules are now **manual-only**; only
small deterministic source/tests auto-run on push.

## New REAL public trade evidence — November 2026, research only

**New live-provider archive downloads succeeded** through public GitHub
Actions, not the Windows PC. Exactly **278,403 real exchange executed
spot prints** were verified with the original provider ZIP SHA-256 files:
LTCUSDT **116,446 on 2026-11-18 UTC** and **161,957 on 2026-11-19 UTC**.
The observed trade IDs are strictly sequential even across the
consecutive-day boundary; that is not independent proof of market
archive completeness. [Scientific provenance and original actions runs](docs/REAL_PUBLIC_SPOT_TRADE_ARCHIVE_2026-11-21.md).

The second predeclared UTC session was used for *descriptive*
30-second clock-origin binning at **0/10/20 seconds**. Changing
only the analytical bin offset changes counts of buy/sell-dominant
and one-sided intervals; none of this identifies physical robots.
All three phase views are correlated. **Historical full L2 is not
included** and quote-based detection remains BLOCKED_BY_L2_DATA.

The source dataset is restricted to **non-commercial CC BY-NC-SA 4.0
research** under Binance Vision terms, not authorized for trading
execution or commercial deployment. Raw trades are **never** committed
or uploaded as workflow artifacts. The original source workflows
were made manual-only immediately after successful first runs.


**Версия проекта:** 0.3 (исследовательская) · **Обновлено:** 2026-11-21 · **Статус:** исторический прототип с импортом 121 920 обезличенных сделок SBER (17.11.2026), симуляциями настоящего ABIDES-NG и 134 автоматическими проверками. Точность распознавания роботов на реальном рынке не установлена.


## New controlled TWAP versus background genuine ABIDES L2 experiment

The preregistered development-only `tools/abides_l2_twap_phase_contrast.py`
adds exactly **one known TWAP execution strategy** to a Poisson background
and compares its public depth-five L2/print timing against a background-only
configuration at fixed 0/10/20s origins. Two source-registered development
seeds (2401/2402), two scenarios and three **correlated** views per
simulated market imply **4 genuine market runs, not 12 independent markets**.
The instrument is synthetic ABM, not MOEX or SPB; real market owner count
and accuracy remain unknown. Both the contrast and the new
`abides_l2_phase_fragility.py` use only public analytics; simulated
controlled agent IDs are inspected *after* features, only to check
execution actually occurred.

[Exact frozen experimental protocol, failure gates and provenance](docs/ABIDES_L2_TWAP_PHASE_CONTRAST.md).
The `public_tape_fingerprint.py` now verifies **ordered full L2 snapshots
plus executed prints** under known clock shifts. Earlier ABIDES phase
archives fingerprinted only prints, so historical book content equality
cannot be independently reconstructed from those aggregate-only results.

The executed controlled TWAP-versus-background study provides a
**phase-choice overfitting counterexample**: the two synthetic cohorts
are perfectly separated by observed rho ranges at **10s and 20s**,
but **not at 0s** and not across all origins. No threshold is fitted,
no real-market recognition accuracy follows.
[Observed data and scientific limitations](docs/ABIDES_L2_TWAP_PHASE_CONTRAST.md).

## Genuine ABIDES public L2 30-second clock-origin sensitivity

The new **pre-registered** `tools/abides_l2_binphase_sensitivity.py` evaluates the same anonymous ABIDES depth-five book/trade tape at three **30-second clock origins (0, 10 and 20 seconds)**. Exactly **four new genuine market simulations** (seeds 2101/2102 × Poisson/fixed-cadence backgrounds) produce twelve **correlated** views. Relative public event times, quantities and reported sides are conserved; no phase is selected as a best model and no private execution actor is identified. The two new seeds are registered as spent in the research provenance ledger.

[Precommitted source, genuine ABIDES results and scientific limits](docs/ABIDES_L2_BINPHASE_SENSITIVITY.md). [Successful CI #44912441330](https://github.com/IskanderAbdullin/Analytics/actions/runs/44912441330) found Poisson-background two-seed median rho **−0.014/−0.161/−0.181** and fixed-cadence **−0.218/−0.195/−0.493** for offsets **0/10/20s**. This is clock-origin sensitivity, **not** owner recognition or a real-market trading signal.

## Reproducible public-feed invariant stress tests

Added a cheap **read-only** deterministic metamorphic suite for lagged public L2/trade analytics. It checks that appending future public events cannot rewrite completed past observations, that more source book/trade gaps cannot increase eligible intervals, that an earlier exclusive watermark only removes a future tail, and that complete-bin accounting conserves every observed public trade bin. Generated tapes are **software fixtures, not real ABIDES experiments, new blind research holdouts or market performance evidence**.

[Metamorphic correctness protocol and limits](docs/L2_PUBLIC_METAMORPHIC.md).

## Public aggregated L2 book: unique prices per side

The public depth-five order-book parser now requires **strictly descending bid price levels** and **strictly ascending ask price levels** within each L2 snapshot. Previously the input checker could accept repeated prices on the same side and double-count displayed quantity in imbalance calculations. Repeated *snapshot timestamps* remain preserved, as they represent potentially distinct book events. This applies only to aggregated L2 data, not L3 per-order books.

[Price-level validation and scope](docs/L2_UNIQUE_PRICE_LEVELS.md).

## Strict public market scalar integrity (timestamps, prices, lots)

The L2 and anonymous execution pipeline now validates discrete exchange timestamp, price and quantity fields with a lossless integer-only `__index__` check rather than `int(...)`, which previously could silently truncate fractional inputs. Noninteger floats (even `100.0`), booleans, decimal/string masquerades and nonpositive sizes/prices are rejected before any model statistic is calculated. Valid integer-only ABIDES fixtures retain the same results.

[Exact source type rules, test cases and limitations](docs/L2_PUBLIC_NUMERIC_INTEGRITY.md). No real source attestation or trading permission is inferred.

## Independent L2-book and trade-feed coverage claims (read-only)

Added a conservative optional **two-stream metadata gate**: the previous completed L2 clock bin and the next observed trade bin must each be covered by their own **caller-declared** feed time range, with explicit non-overlapping missing-data intervals. Declared instrument, venue and session must match across book and trade metadata; absent or mismatched coverage causes a recorded abstention rather than filling gaps. A raw ABIDES book/trade tuple **cannot verify the caller's provider identity or coverage claim**, so the output continues to explicitly report real-market completeness as **unverified**.

[Source-coverage specification and limitations](docs/L2_DUAL_STREAM_COVERAGE.md). No broker API, secrets, execution orders or new bot classifier.

## Research seed provenance / known-holdout reuse guard

The new **read-only** `research/seed_registry.json` records already inspected ABIDES and deliberately constructed toy seeds, including explicit **non-independent replays**. `tools/research_seed_registry.py` checks the historical seed list against four frozen experiment scripts using Python AST, **without importing or running those experiments**, rejects source-plan drift and flags any proposed seed that has already been spent. A previously *unlisted* seed is **not automatically proven globally new or a valid blind holdout**. A lightweight Python-only CI audit runs when relevant source constants or ledger entries change.

[Known seed list, provenance, successful source CI #44903479712 and limits](docs/RESEARCH_SEED_REGISTRY.md). The lightweight audit verified **31 known spent seeds across 12 canonical studies**, **5 pinned seed constants**, **1 explicitly non-independent replay**, and passed **7/7 pure-Python tests**. It cannot certify any new seed as globally unused. No private agent truth, real market data, GUI or orders.

## Genuine ABIDES public-L2 time-bin robustness experiment

A new controlled **read-only** `tools/abides_l2_binwidth_sensitivity.py` study fixes **two previously unused development seeds × two background regimes = four genuine matching-engine simulations**, each analyzed at three preregistered UTC-bin durations (**10, 30 and 60 seconds**) from the **same anonymous public tape**. It verifies identical source fingerprints/lot counts across widths and records the descriptive lagged public L2 imbalance versus later reported BUY-share correlation. The three widths are **not independent experiments**, a best width is **not chosen**, and no physical VWAP/POV agent or real-market p-value can be inferred.

[Reproducible frozen study and verified ABIDES evidence](docs/ABIDES_L2_BINWIDTH_SENSITIVITY.md). In [successful pinned matching-engine CI #44903121650](https://github.com/IskanderAbdullin/Analytics/actions/runs/44903121650), Poisson-background two-seed median rho changed from **−0.243 (10s)** to **−0.127 (30s)** to **+0.206 (60s)** on the same generated public source tapes. Fixed-cadence two-seed medians were **−0.278/−0.428/−0.193**. This is evidence of **bin-width sensitivity**, not proof of a real-market predictor or bot identification.

## Optional completed-archive watermark gate

The strictly read-only public previous-bin book monitor now accepts an optional exclusive `complete_through_ns` watermark: a trade bin whose **end** is later than the supplied watermark is **excluded** from the statistic and recorded as a separate abstention. This prevents a truncated terminal archive bin from being silently interpreted as complete **when a trustworthy watermark is available**. The algorithm **cannot independently certify a source-provided watermark**; with no watermark, all existing descriptive results remain available but terminal archive completeness is explicitly **unverified**. Six deterministic tests cover boundary equality, null/partial bins, future-append invariance and malformed watermarks.

[Source completeness specification](docs/L2_ARCHIVE_WATERMARK.md). No new robot classifier, live feed collection or trading.

## Genuine matching-engine background-only public L2 nulls

Added `tools/abides_l2_background_nulls.py` with **six frozen genuine ABIDES-NG simulations**: two new development seeds across a baseline Poisson background, fixed-cadence noise-agent background, and heterogeneous noise-plus-momentum background. **No separately injected TWAP/VWAP/POV parent execution agent** is introduced. This is not a claim that these markets have no other algorithmic participants.

The output compares the last valid L2 state of a *fully completed previous* 30-second bin against the next completed bin's aggregate public BUY fraction. Exact-time fill/quote joins remain intentionally unclassified. The study reports only public counts, source fingerprints and *descriptive* correlation, without physical owner labels, real-market statistical significance or live trading. Seeds, parameters and study cohorts were frozen before running any results; no tuning on these seeds.

[Methodology, executed six-case ABIDES results and scientific limits](docs/ABIDES_BACKGROUND_L2_NULLS.md). In [successful CI #44902051089](https://github.com/IskanderAbdullin/Analytics/actions/runs/44902051089), 60 Poisson background agents produced **median rho −0.509** (39 lagged pairs over two seeds), 60 fixed-cadence background agents **−0.361** (41 pairs), and 50 noise + 10 momentum agents **−0.201** (41 pairs). The change with market background illustrates confounding, **not** independent physical robot identification or calibrated real-market specificity.

## Adversarial common-market public-book null controls

The new strictly synthetic, read-only `tools/l2_common_factor_null.py` demonstrates that **market-wide common conditions** can generate very high correlation between previous book imbalance and later aggregate directional trades **without identifying any single parent execution order**. Four transparent families—common factor, independent flow, synchronized quote/trade clock and broad market regime shock—are tested in an inexpensive, no-ABIDES Python CI. The results are **educational counterexamples, not realistic calibrated market nulls**; do not convert a high public `rho` to a bot count or real false-positive probability.

[Protocol, actual CI results and limitations](docs/L2_COMMON_FACTOR_NULLS.md). [Lightweight CI #44896188923](https://github.com/IskanderAbdullin/Analytics/actions/runs/44896188923) passed all five tests: two constructed common-state/shock backgrounds yielded **Spearman rho=1.000 with no identified parent order**, while independently permuted flow yielded **−0.195**; clock synchronization forced **144/144** strict-event join abstentions. **These are deliberately synthetic counterexamples, not market FDR estimates.** No trading APIs, account access or hidden actor labels.

## Lagged completed-book L2 versus next-bin public executions

The new **read-only** `tools/lagged_l2_bin.py` describes depth-five order-book imbalance in an **entirely completed previous 30-second bin** versus BUY share in the **next completed** bin of anonymous executed prints. It avoids the intra-timestamp sequencing impossibility seen in the strict per-fill join (all 2,630 prints were ambiguous) and explicitly abstains if the prior clock bin has no valid fresh two-sided book. Five or more eligible observations with changing ranks are needed to report a *descriptive*, ties-aware Spearman correlation; otherwise the coefficient is undefined. It **cannot** identify VWAP/POV agents, infer queue position or supply a calibrated market FDR. The public-bin outcome is retrospective, not a forecast available at bin open.

[Method, genuine ABIDES evidence and strict limits](docs/L2_LAGGED_BIN.md). [CI #44895877902](https://github.com/IskanderAbdullin/Analytics/actions/runs/44895877902) passed 15 public-only tests and yielded 13 valid lagged bins in the agent-free background, 10 in POV and 13 in VWAP. Their descriptive Spearman coefficients were **−0.341 / 0.152 / 0.104**, respectively: **not an independently validated VWAP/POV discriminator**. No real broker L2 archive or user order account is accessed.

## Public executed-print / prior L2 context — experimental, no attribution

A new strictly **read-only** public-only audit (`tools/l2_trade_context.py`) pairs anonymous ABIDES executed prints with the **last strictly older** simulated L2 book snapshot. Executions sharing a timestamp with any quote mutation are explicitly **unclassified**, never ordered arbitrarily; one-sided, stale, crossed and missing quotes cause abstention. It conserves all prints and lots and reports at/through-previous-opposite-best only as a **descriptive quote compatibility**, not a detected VWAP/POV bot or execution-cost estimate. The runner also compares an agent-free background to POV/VWAP and a transparent **rotated public-print placebo**; the latter is **not** a valid market-conditional statistical null. In the [genuine ABIDES CI #44895496910](https://github.com/IskanderAbdullin/Analytics/actions/runs/44895496910), **all 2,630 fills** across null/POV/VWAP shared exact timestamps with L2 updates; the strict join **abstained on all**, so neither natural nor rotated results can measure execution compatibility. This is a necessary negative finding: a clock-bin-lagged L2 study, or a verified exchange event sequence, is required.

[Full data and causality contract](docs/L2_TRADE_CONTEXT.md). No broker account/API, live alerts, private agent IDs or changed OS Engine code.

## Simulated public L2 order-book feasibility (2026-11-21)

The new strictly **read-only**, optional `tools/l2_probe.py` checks whether the genuine, pinned ABIDES-NG matching engine can export timestamped public depth-five order-book updates without participant IDs. In [successful L2 CI #44894589485](https://github.com/IskanderAbdullin/Analytics/actions/runs/44894589485), a five-minute simulation exported **1,152** L2 snapshots (**661** two-sided, **457** one-sided, **34** empty), **709** executed trades, and **434** extra book snapshots sharing timestamps. **Do not deduplicate snapshots solely by exchange timestamp.**

The official T-Invest historical archive documents trade and candle files, **not a downloadable historical depth-of-book archive**; separate GetOrderBook / MarketDataStream methods provide current/ongoing quotes, not retroactive L2 proof. [Method, data contracts and source evidence](docs/L2_FEASIBILITY.md). This is synthetic L2 *data feasibility*, not a validated market bot detector.

## Public-only directional regime shifts — experimental Stage 2

Added additive, read-only `direction-shift` to inspect abrupt changes in publicly reported BUY share after a contiguous, qualified six-bin *past-only* reference window. A missing clock bin, too little known-side volume or many UNKNOWN-side prints reset the baseline. No private maker/taker labels or broker order APIs are referenced.

```powershell
dotnet run --project src/RobotDetector.Cli -- direction-shift `
  --input fixtures/synthetic_activity_episode.csv `
  --bin-seconds 30 --reference-bins 6 --min-share-shift 0.25 `
  --output data/results/directional-shifts.json
```

[Full methodology, ABIDES experiments and scientific limits](docs/DIRECTIONAL_REGIME_SHIFT.md). The result counts **unvalidated market-wide change windows**, not individual robots. In [real ABIDES-NG CI #44893601107](https://github.com/IskanderAbdullin/Analytics/actions/runs/44893601107), a pre-registered four-seed independent replication yielded candidate windows **null 1, VWAP 0, POV 1** (216 evaluated bins per cohort). The earlier exploratory results did **not** replicate; this public share-shift feature is **not** an independently verified VWAP/POV detector. No calibrated real-market false alarm probability, trading signal or physical identity is established.

## Public-only lagged volume response — experimental Stage 2

The new **read-only** `volume-response` command examines whether reported BUY/SELL volume in bin `t` is associated with observable market volume in the **preceding completed** UTC clock bin `t-1`. It does not access ABIDES private labels or identify VWAP/POV orders or their owners. Missing populated bins break the lag; uniform side volume yields an undefined (null) rank correlation; source/session/data-kind boundaries are isolated.

```powershell
dotnet run --project src/RobotDetector.Cli -- volume-response `
  --input fixtures/synthetic_variable_clip_5s.csv `
  --bin-seconds 5 --min-pairs 8 --output data/results/volume-response.json
```

[Method, safety, scientific references and reproducibility](docs/VOLUME_RESPONSE_PUBLIC.md). [Full ABIDES simulation validation #44892179775](https://github.com/IskanderAbdullin/Analytics/actions/runs/44892179775) ran a separate nine-case public-only survey: median lagged rho for BUY/SELL **null 0.510/0.548, POV 0.538/0.501, VWAP 0.511/0.596**. These overlapping correlations, and a stronger single null than TWAP development case, demonstrate that this public volume feature **does not discriminate identified agents** in the observed toy exchange cases. Existing fixed-q and variable-q detectors are unchanged; no VWAP/POV bot flag was invented. The feature does not establish predictive edge or significance.

## Genuine ABIDES-NG exchange execution — blind validation

A new **optional** research pipeline uses the genuine ABIDES-NG exchange/order-book matching engine with controlled TWAP, VWAP or POV execution, independent background agents and a matching-engine null scenario. Only the anonymous public CSV is shown to either detector; maker/taker agent IDs stay in a separate private manifest used **after detection** for exact print-level scoring. Source pinned to upstream commit `ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242`.

```powershell
# Python 3.12 with pinned ABIDES-NG installed, from this subproject directory
python tools/abides_export.py --mode twap --seed 41 --public data/raw/abides-public.csv --truth data/raw/abides-truth.json
dotnet run --project src/RobotDetector.Cli -- benchmark-abides-blind --public data/raw/abides-public.csv --truth data/raw/abides-truth.json --output data/results/abides-score.json
```

[Full setup, data contract, null protocol and limitations](docs/ABIDES_GENUINE_REPLAY.md). [Verified ABIDES CI #44890937246](https://github.com/IskanderAbdullin/Analytics/actions/runs/44890937246) includes **123/123** offline C# checks, four frozen-seed TWAP/null simulations each, and real VWAP/POV execution tests. In four frozen TWAP runs the fixed-q detector recovered 101 of 197 controlled prints; the variable-q screen recovered none. On single VWAP (50 controlled) and POV (14 controlled) runs **both screens recovered zero**. A **new pre-registered, unchanged-screen 16-case baseline** on independent synthetic seeds 1301–1304 ([successful real ABIDES CI #44894042225](https://github.com/IskanderAbdullin/Analytics/actions/runs/44894042225)) found, for the fixed-quantity screen: **TWAP 98/183 controlled fills recovered (53.55%), VWAP 6/191 (3.14%), POV 0/66**; the variable-quantity screen recovered **0 controlled fills in all three strategies**. The agent-free null (13,773 public fills) produced no attributed prints from either baseline. This demonstrates strong *synthetic* dependence on execution strategy, not a real-market precision estimate or actual number of physical bots. The real simulator ran in GitHub Actions without touching any trading account. **Stage-2 scientific gate remains CLOSED.**

## Adversarial common-clock null experiment — 2026-11-21

New read-only command `benchmark-clock-null` constructs market-wide periodic **background** prints (zero controlled execution agents) with opaque IDs and private independent producer labels. Both detectors see only the identical public tape; any claimed controlled-execution evidence is counted as a synthetic false attribution. Two independent profiles are available: fixed 100-lot prints and variable 25/50/75/100-lot market-wide clocked prints (`--clip-mode variable`). Both have **zero** controlled program ground truth. Aggregated per-trial alarms are **not** calibrated real-market FPR or proof of physical robot identities.

```powershell
dotnet run --project src/RobotDetector.Cli -- benchmark-clock-null `
  --trials 20 --background-prints 120 --cycles 12 --period-ms 5000 `
  --output data/results/clock-null.json
```

[Protocol, limitations and acceptance](docs/CLOCKED_NULL_STRESS.md). In the [verified 120-check CI smoke](https://github.com/IskanderAbdullin/Analytics/actions/runs/44888523166), each detector falsely attributed 81/180 independent prints from its matching adverse 3-seed clocked-null profile; this does **not** establish a real-world market false-positive rate. The prior four-scenario blinded benchmark remains available and unchanged. **Stage-2 scientific release gate remains CLOSED.**

## Научная проверка с приватной синтетической разметкой — 19.11.2026

Добавлен независимый `benchmark-blind` на четырёх сценариях: кластеризованный фон без контролируемого агента, TWAP с фиксированным объёмом, TWAP с переменным объёмом и TWAP с двумя отпечатками на один временной срез. **116 из 116 тестов пройдены**: [CI #44577833225](https://github.com/IskanderAbdullin/Analytics/actions/runs/44577833225).

Метки реальных генераторов **не передаются** детекторам: публичные `EventId` непрозрачные, оценки TP/FP считаются отдельно, уже после работы алгоритмов. В небольшом синтетическом тесте фиксированный алгоритм обнаружил 24/24 событий с постоянным объёмом и 0/24 с переменным; второй алгоритм, наоборот, 0/24 и 24/24. При расщеплённых исполнениях оба теряют часть доказательств. **Реальное количество независимых биржевых роботов по открытым сделкам не определяется**; принципиальная неидентифицируемость проверена на двух разных приватных разметках одной публичной ленты.

```powershell
dotnet run --project src/RobotDetector.Cli -- benchmark-blind `
  --seeds 5 --background-prints 120 `
  --output data/results/blind-research.json
```

[Подробный протокол](docs/BLIND_EXECUTION_BENCHMARK.md). Это мини-симуляция для тестирования, **не** полноценный ABIDES-NG, не калибровка на рынке и не торговый сигнал.

## Текущее состояние: локальная панель и API (19.11.2026)

**Проверено: 108/108 автоматических тестов.** Реализованы `dashboard` (один архив), `compare-archives` (2–20 архивов) и отдельный локальный сервер `RobotDetector.Server`. Проверки [сравнения SBER/MOEX](https://github.com/IskanderAbdullin/Analytics/actions/runs/44573901868) и [защищённого HTTP API](https://github.com/IskanderAbdullin/Analytics/actions/runs/44575738794) успешно прошли. История и локальный интерфейс работают без токена брокера и без торговых функций.

```powershell
# Из projects/robot-detector/
dotnet run --project src/RobotDetector.Server -- `
  --input fixtures/synthetic_activity_episode.csv --port 8765
# Открыть http://127.0.0.1:8765/
# Агрегированные данные: http://127.0.0.1:8765/api/v1/summary
```

Без сервера: `compare-archives --inputs "data/raw/SBER.csv;data/raw/MOEX.csv" --html comparison.html`. Подробности в [локальном API](docs/LOCAL_READ_ONLY_API.md) и [сравнении архивов](docs/MULTI_ARCHIVE_RESEARCH_COMPARISON.md). Сервер слушает **только 127.0.0.1**, отклоняет POST и внешние Host/Origin; HTML без скриптов и внешних ресурсов.

**Не готово:** аутентифицированный live T-Invest MarketDataStream, отдельный OsEngine клиент и статистически валидированный подсчёт физических роботов. На исторических holdout-данных старый прогноз регулярного q не обошёл placebo. Панель показывает рыночные наблюдения, а не подтверждённые роботы.

## Replay на исторической ленте — проверен на реальном SBER

Реализована команда `replay-audit` с ограниченным буфером событий и event-time watermark. В проверке [GitHub Actions #44572400620](https://github.com/IskanderAbdullin/Analytics/actions/runs/44572400620) воспроизведены **121 920** сделок SBER и **19 769 931** лот, без потерь и принудительного сброса очереди. **100/100 тестов пройдены**; [реализация в PR #23](https://github.com/IskanderAbdullin/Analytics/pull/23) объединена с `main`.

```powershell
dotnet run --project src/RobotDetector.Cli -- replay-audit `
  --input data/raw/sber.csv --receipt-order archive_row `
  --lateness-ms 500 --max-pending 10000 `
  --output data/results/replay.json
```

**Предупреждение:** `archive_row` — порядок строк архивного файла, **не реальное время доставки через API**. Он дал 11 394 нарушения хронологии и 54 429 событий старше watermark; искусственно отсортированный эталон `exchange_time_ideal` дал нули, не измеряя сетевые задержки. [Методика и ограничения](docs/BOUNDED_EVENT_REPLAY.md). Живой T-Invest Stream и настоящий streaming receiver пока не подключены, торговые команды отсутствуют.

## Локальный HTML-отчёт — готов к использованию

Добавлена команда `dashboard`, объединяющая профиль потока, всплески активности и диагностику качества временных меток. Она создаёт **автономный HTML**, открываемый на Windows без сети и сервера, и необязательный агрегированный JSON. **91/91 автоматический тест пройден**, на реальном SBER за 17.11.2026 обработаны **121 920** обезличенных сделок и **19 769 931** лот без потери исходных событий. [Проверка архива и панели](https://github.com/IskanderAbdullin/Analytics/actions/runs/44570331435).

```powershell
# Из каталога projects/robot-detector/
dotnet run --project src/RobotDetector.Cli -- dashboard `
  --input fixtures/synthetic_activity_episode.csv `
  --html data/results/research.html `
  --json data/results/research.json
start data/results/research.html
```

[Полное руководство по панели](docs/OFFLINE_RESEARCH_DASHBOARD.md). HTML не содержит скриптов, отдельных записей сделок и обращений к внешним сайтам. Результат **не** устанавливает владельцев заявок и не является торговым сигналом; достоверность обнаружения реальных роботов пока не подтверждена.

## Новые независимые методы и проверки источника — 19 ноября 2026

**Текущий проверенный код:** .NET 10, **83/83 офлайн-тестов**, [GitHub Actions](https://github.com/IskanderAbdullin/Analytics/actions/runs/44554682245). Проект остаётся исследовательским read-only инструментом: **подтверждённое число физических роботов/владельцев неизвестно; прогностическая точность не подтверждена**.

- `clock-phase-audit` — десять 100-миллисекундных фаз секунды, исторически заданная первая фаза и контроль максимума из десяти фаз по 99 сдвигам времени **целых минутных кластеров**. [Метод, литература, SBER/MOEX 17–18 ноября](docs/MARKET_CLOCK_PHASE_AUDIT.md), [проверка максимума на другой дате](docs/MAX_BIN_PHASE_AUDIT.md). Небольшая концентрация near-second у одного инструмента может исчезнуть на следующей дате, поэтому **это не доказательство конкретного робота**.
- `timestamp-quality` — количество уникальных времён, совпадающих timestamps, совпадающих времён и цен, доля кратных 1 мс и минимальный наблюдаемый интервал без удаления исходных сделок. На 18 ноября в группах одинаковых timestamp находились **32 311 из 83 515** сделок SBER и **5 902 из 10 584** MOEX. [Результаты](docs/TIMESTAMP_QUALITY_AUDIT.md).
- `cluster-compare` — отдельно создаёт **прослеживаемые аналитические группы** совпадающих по полному времени/цене/направлению/источнику/режиму/сессии сделок и сравнивает исторические кандидаты регулярности с оригинальными записями. На 18 ноября: SBER **57 → 64** кандидата, MOEX **6 → 6**, без потери лотов. **Группы не равны родительским заявкам или владельцам**. [Описание и тесты](docs/OBSERVABLE_PRINT_CLUSTERS.md).

```powershell
dotnet run --project src/RobotDetector.Cli -- clock-phase-audit --input data/raw/market.csv --trials 99 --output data/results/clock.json
dotnet run --project src/RobotDetector.Cli -- timestamp-quality --input data/raw/market.csv --output data/results/quality.json
dotnet run --project src/RobotDetector.Cli -- cluster-compare --input data/raw/market.csv --output data/results/clusters.json
```

[Проверка на реальных архивах](https://github.com/IskanderAbdullin/Analytics/actions/runs/44554682105) · [объединённые изменения PR #18–21](https://github.com/IskanderAbdullin/Analytics/pulls?q=is%3Apr+is%3Aclosed+robot+detector). Автоматические выставления заявок, онлайн-подключение, подтверждённая идентификация ботов и окончательная калибровка качества **не реализованы**.

## Альтернативные методы — доступны отдельно (19 ноября 2026)

Чтобы не подгонять один плохо предсказывающий регулярный алгоритм, в проекте реализованы **несколько независимых исследовательских вариантов**:

- **Фиксированный объём + периодичность** (`detect`) и **переменный объём + периодичность** (`variable-cadence`): только кандидаты последовательностей, а не доказанные торговые роботы.
- **Простой профиль потока** (`flow-footprint`): объёмы, reported BUY/SELL imbalance, лаг-1 по направлениям, межсделочные интервалы, Fano по секундным корзинам и доля сделок около круглой секунды. Испытан на 121 920 реальных сделках SBER, **203 групповых пятиминутных окна**, медианный Fano **8,883**. Данные показали неравномерность, но **не подтвердили** владельцев. [Описание](docs/TRADE_FLOW_FOOTPRINT.md), [реальный прогон](docs/FLOW_PUBLIC_PILOT.md).
- **Простые эпизоды высокой активности** (`activity-episodes`): сравнение с четырьмя **предыдущими** соседними окнами того же источника и сессии по числу сделок, лотам и перевесу reported side. **Не является детектором физических роботов** и не использует будущие сделки при формировании текущего наблюдения. [Метод и границы](docs/SIMPLE_ACTIVITY_EPISODES.md).

```powershell
dotnet run --project src/RobotDetector.Cli -- flow-footprint --input fixtures/synthetic_variable_clip_5s.csv --output data/results/flow.json
dotnet run --project src/RobotDetector.Cli -- activity-episodes --input fixtures/synthetic_activity_episode.csv --output data/results/activity.json
```

Проверка [GitHub Actions (62/62)](https://github.com/IskanderAbdullin/Analytics/actions/runs/44543220045) подтвердила сборку и офлайн-тесты второго простого детектора. Новые методы **read-only** и независимы от IPO-проекта. Логи реального рынка не позволяют идентифицировать отдельных владельцев алгоритмов. Исторический прогноз фиксированного объёма **не показал преимущества** перед контрольным сдвигом (14/983 против 14/983); не использовать кандидатов как торговые сигналы.

[Исследование альтернатив и открытые исходники](docs/ALTERNATIVE_APPROACHES.md). Реальное подключение T-Invest MarketDataStream, полноценный GUI, расширенный учёт стакана L2 и валидированный счёт физических роботов по-прежнему не завершены.

## Запускаемый прототип (Milestone 0.1)

Требуется **.NET SDK 10**. Запускайте команды из `projects/robot-detector/`. Проект **не** зависит от Python-пакета IPO, торговых API или установленного OsEngine.

```powershell
# Только синтетические сделки из репозитория
dotnet run --project src/RobotDetector.Cli -- detect --input fixtures/synthetic_twap_5s.csv

# Осцилляции best ask в синтетическом стакане (без биржевых сделок)
dotnet run --project src/RobotDetector.Cli -- quote --input fixtures/synthetic_quote_oscillation.csv

# Набор детерминированных офлайн-тестов
dotnet run --project tests/RobotDetector.SelfTests

# Иллюстративная статистика false positives / recall в синтетике
dotnet run --project src/RobotDetector.Cli -- benchmark --seeds 20 --noise-trades 200 --output data/results/benchmark.json

# Проверка одного прогноза на будущих событиях, не использованных при поиске
dotnet run --project src/RobotDetector.Cli -- walkforward --input fixtures/synthetic_twap_5s.csv --cutoff 2026-11-18T07:00:20.020Z --min-matches 4

# Второй независимый алгоритм — частотные кандидаты (FFT по UTC)
dotnet run --project src/RobotDetector.Cli -- spectrum --input fixtures/synthetic_twap_5s.csv --bin-ms 500
```

Чтобы скачать **публичный архив** с реальными обезличенными сделками, сначала проверьте нужный UID/тикер с кодом режима и день в официальном [T-Invest archive browser](https://developer.tbank.ru/invest/services/history-md/head-history-md). Команда скачивает **ровно один** файл, не запрашивает токен и не выставляет заявок:

```powershell
dotnet run --project src/RobotDetector.Cli -- fetch --date 2026-11-17 --instrument-id SBER_TQBR --output data/raw/sber_2026-11-17.csv
```

Укажите реальную дату/инструмент с доступным архивом. Фактически сервер возвращает **gzip-сжатые байты**, даже при имени `.csv`. Импортёр определяет GZip/ZIP по сигнатуре файла и распаковывает автоматически; расширение `.csv` для такого ответа корректно. Запись идёт в новую папку `data/raw/`, которая игнорируется Git. Ограничение провайдера: **не более 30 файлов в минуту с IP**; не запускайте массовые параллельные загрузки. Данные могут быть неполны/недоступны. Одна скачанная история не доказывает полноту потока и может не раскрывать сторону пассивной заявки.

**Семантика первых результатов:** поле `candidatePatternCount` — количество *кандидатов на различимые повторяющиеся потоки* в наблюдениях; `physicalBotCountKnown=false`, `confidenceCalibrated=null` и `state=candidate` должны сохраняться, пока нет проверенной калибровки. Анализ выполняется независимо в часовых UTC-окнах (параметр `--window-minutes`), поэтому один и тот же алгоритм в двух окнах может учитываться дважды как *эпизод*, а не как уникальная программа. Слишком плотные отдельные окна делятся на последовательные непересекающиеся части с предупреждением `SPLIT_DENSE_GROUP` — истинный единый паттерн может разделиться между ними.

См. [текущий статус реализации и ограничения](docs/IMPLEMENTATION_STATUS.md). GitHub Actions workflow [robot-detector-ci.yml](../../.github/workflows/robot-detector-ci.yml) компилирует и запускает синтетические регрессии без токенов брокера. **Сборка подтверждена:** [CI 44278450065](https://github.com/IskanderAbdullin/Analytics/actions/runs/44278450065) — .NET сборка, офлайн-тесты (18 проверок), CLI smoke успешно. [Реальный архив 44278450117](https://github.com/IskanderAbdullin/Analytics/actions/runs/44278450117): 121 920 сделок, 0 ошибок импорта, 209 предварительных кандидатов-эпизодов, без утверждения о числе физических роботов. [Методика и TLS](docs/PUBLIC_ARCHIVE_VALIDATION.md).

## Стадия исследования после двухдневной проверки (18 ноября 2026)

**Обновление:** самостоятельный .NET 10 проект собирается в GitHub Actions; 32 офлайн-теста пройдены. [Проверенный двухдневный протокол](docs/MULTIDAY_NULL_PROTOCOL.md): SBER 16.11.2026 (143 929 сделок, 126 отдельных эпизодов, 120 консервативно сгруппированных потоков) и 17.11.2026 (121 920 сделок, 209 эпизодов, 206 групп). Исходные наблюдаемые кандидаты превышают результаты 12 перестановок объёмов и 12 циклических сдвигов на каждой дате; это только предварительное, **не откалиброванное** наблюдение, не число независимых торговых роботов.

Реализован [консервативный алгоритм группировки эпизодов](docs/EPISODE_FUSION.md), не смешивающий источники, стороны и торговые режимы. Две различные контрольные модели доступны через CLI. Целая лента сделок не сохраняется в репозитории; отчёты по реальной истории содержат только агрегированные данные и SHA-256.

```powershell
# Дополнительные команды к основному историческому экрану:
dotnet run --project src/RobotDetector.Cli -- fusion --input data/raw/sber.csv --max-gap-cycles 12 --output data/results/fusion.json
dotnet run --project src/RobotDetector.Cli -- null-shuffle --input data/raw/sber.csv --mode permute --trials 12 --output data/results/null-permute.json
dotnet run --project src/RobotDetector.Cli -- null-shuffle --input data/raw/sber.csv --mode rotate --trials 12 --output data/results/null-rotate.json
```

Последняя самостоятельная проверка на данных двух торговых дней: [GitHub Actions #44295820963](https://github.com/IskanderAbdullin/Analytics/actions/runs/44295820963). До полноценного релиза остаются более реалистичные контрольные модели, оценка прогноза на будущих данных, живой T-Invest MarketDataStream и UI/OsEngine read-only adapter. Никакие торговые команды программа не посылает.

## Ограничение достоверности прогнозов

**Отдельная строго хронологическая проверка не показала преимущества перед контрольным прогнозом.** На ранее не использованных датах 12 и 13 ноября 2026 года детектор проверил 983 будущих окна: 14 совпадений с прогнозами и 14 совпадений с прогнозами, сдвинутыми на половину периода (в обоих случаях 1,42%). Это **не подтверждает** практическую прогностическую ценность текущих правил. Не использовать найденные кандидаты как готовые торговые сигналы.

Результаты с зафиксированными параметрами: [ROLLING_REAL_PILOT.md](docs/ROLLING_REAL_PILOT.md). Методика: [ROLLING_FORECAST.md](docs/ROLLING_FORECAST.md). Новый CLI-режим: `rolling-forecast --input file.csv --warmup-minutes 60 --stride-minutes 30 --max-cutoffs 12`.

## Назначение

Бесплатно выявлять по доступным публичным биржевым данным повторяющиеся алгоритмические торговые **паттерны** в инструментах MOEX/СПБ. Первый сценарий: одинаковые или сходные объёмы покупок/продаж через регулярные интервалы. Дальше — переменный TWAP, зависимость от рыночного объёма, повторное пополнение стакана, сетки, вероятные маркет-мейкеры и скрытые крупные поручения (*metaorders*).

**Не утверждать, что алгоритм показывает истинное число независимых программ или участников.** У обезличенных сделок нет идентификаторов конечного трейдера. Система считает *различимые потоки/гипотезы* с подтверждением и неопределённостью: один робот может породить несколько потоков, несколько — один неразличимый поток. Отдельно показывать «периодическую рыночную активность» и «выделенный поток сделок».

## Изоляция от IPO Analytics

Этот каталог — независимый проект, **не модуль IPO-прогнозирования**. Не менять существующие `src/ipo_forecast`, его зависимости, модели, CLI и данные. В дальнейшем использовать собственный `src/`, `tests/`, `data/`, `config/`, CI и сборку. Требуемый стек основного приложения — C#/.NET (совместимость с Windows и OsEngine); Python допустим только как **необязательный исследовательский инструмент** в отдельном окружении. Общий с IPO Analytics только Git-репозиторий; общего runtime нет.

## Дорожная карта и отдельные ТЗ

| Этап | Документ | Выход |
|---|---|---|
| 0. Основание | [Архитектура](docs/ARCHITECTURE.md) · [научные источники и примеры](docs/RESEARCH.md) | Проверяемые определения, интерфейсы, факты и гипотезы |
| 1. Исторический TWAP | [STAGE_01_HISTORICAL.md](docs/STAGE_01_HISTORICAL.md) | Архивы сделок, реконструкция потоков, CSV/JSON отчёты |
| 2. Валидация | [STAGE_02_VALIDATION.md](docs/STAGE_02_VALIDATION.md) | Синтетика, реалистичный фон, blind walk-forward и метрики |
| 3. Онлайн | [STAGE_03_REALTIME.md](docs/STAGE_03_REALTIME.md) | Stream-подписки, read-only сканер, web/UI, экспорт в OsEngine |
| 4. Расширение | [STAGE_04_ADVANCED.md](docs/STAGE_04_ADVANCED.md) | Стакан, условные классы стратегий, metaorder research, ML |

Релизный порядок: **1 → 2 → 3 → 4**. Внеочередное внедрение ML до измерения точности базового детектора запрещено.

## Принципы

- Начинать с официального сервиса [истории сделок T-Invest](https://developer.tbank.ru/invest/services/history-md/head-history-md) и [MarketDataStream](https://developer.tbank.ru/invest/api/market-data-stream-service-market-data-stream); сначала проверить наличие полей и реальное покрытие каждого рынка. Не подменять историю сделок свечами.
- Разделять биржевой и дилерский источники, сессии, тикеры и UID; не суммировать лоты из разных инструментов.
- Не путать сторону агрессора в сделке со стороной пассивной лимитной заявки.
- Реплей должен быть детерминированным, без доступа к будущим событиям.
- Базовые детекторы — прозрачные, с математически определяемыми признаками и объяснениями; сложные методы сравнивать с базовым.
- Для вероятности/уверенности использовать **эмпирическую калибровку**, а не произвольные проценты в UI.
- Все реальные запросы read-only. Ни токен с правами торговли, ни торговые команды приложению не нужны. Секреты только из переменных окружения/безопасного хранилища; без логирования и коммита.
- Источники, лицензии, ограничения хранения и распространения данных проверять до загрузки и публикации.
- В тестах различать реальные лицензированные данные, синтетические последовательности и неподтверждённые предположения.
- Все изменения — небольшими коммитами; без force-push; не разрушать существующий IPO-проект.

## Целевые сценарии пользователя

1. «Покажи, какие различимые регулярные продавцы работают в SBER сейчас: объём, интервал, фаза, общий оборот, последний/следующий прогноз».
2. «Сравни число подтверждённых потоков вчера и сегодня; укажи степень достоверности и покрытие данных».
3. «Проанализируй неликвидный инструмент: отличай один повторяющийся алгоритм от одной заявки, разбитой на несколько исполнений».
4. «Подключи аналитический сигнал к Babid Demo/другим OsEngine-роботам без открытия торговых полномочий в детекторе».
5. «Реплей одной и той же истории с одинаковым конфигом выдаёт побитово сопоставимые результаты».

## Что не является обещанием

Нельзя бесплатно гарантировать получение полных MBO-данных с order ID, истинных идентификаторов участников, скрытых поручений и каждой промежуточной модификации стакана. Сканер должен возвращать `unknown`/качество покрытия, а не выдумывать данные. Торговая прибыль и прогноз цен не входят в критерии приёмки.

## Справочные материалы

Научная и инженерная база с прямыми ссылками, формулами и воспроизводимыми примерами: [docs/RESEARCH.md](docs/RESEARCH.md). Отдельные технические проверки до подключения: [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md). Правила работы ИИ-агентов: [AGENTS.md](AGENTS.md). Первый воспроизводимый синтетический тест: [fixtures/](fixtures/). Точные квоты и состав полей T-Invest проверять по официальной документации перед разработкой и повторять проверки в интеграционных тестах; спецификация не фиксирует неподтверждённые лимиты как вечную истину.


## Дополнительный обзор реальных открытых реализаций (2026-11-18)

[**RESEARCH_EXPANSION_2026-11-18.md**](docs/RESEARCH_EXPANSION_2026-11-18.md) — конкретные репозитории/файлы: Crypto Lake `twap_detection.ipynb`, `binance_l3_est/src/engine/twap.rs` (500мс bins, FFT), Flowdepth L2 refill, BOCPD, Hawkes simulators, FlowForge и научные исследования. В каждом этапе ниже новые требования ссылаются на этот обзор. **Документы — ТЗ, а не заявление о готовой программе.**

## Третье расширение исследований: от периодических сделок к пассивным алгоритмам

Новый обзор [**Quote Volatility, ABIDES с известной разметкой и Matrix Profile**](docs/RESEARCH_EXPANSION_2026-11-18_PART2.md) (18.11.2026): опубликованная метрика осцилляций best bid/ask Bogoev–Karam, исходники TWAP/VWAP/POV агентов ABIDES-NG, контрфактическая проверка обнаружения, STUMPY motifs и различие event/UTC time. Добавлены критерии пригодности данных T-Invest и метрики невозможности идентификации конкретных владельцев.

**Приоритетное изменение roadmap:** stage 2 должен включать blinded симуляцию известных execution-агентов, а stage 4 — независимый детектор котировочных осцилляций, который может видеть активность без сделок. Оба направления остаются исследовательскими до воспроизводимых измерений.
