# Implementation status — Market Robot Detector

Date: 2026-11-19. Branch: `main`. Milestone: experimental research `0.3`, read-only, no calibrated owner identity.

## Implemented source files

| Area | Path | Actual scope |
|---|---|---|
| Core contracts | `src/RobotDetector.Core/Models.cs` | MarketTrade, rejected rows, configuration, hypotheses, evidence IDs, report |
| Historical CSV/GZip/ZIP importer | `src/RobotDetector.Core/CsvTradeReader.cs` | Strict T-Invest-shaped headers, invariant decimal/lot parsing, deterministic sorting, source SHA-256, rejected rows |
| Periodic screen | `src/RobotDetector.Core/PeriodicDetector.cs` | Same quantity/side/source/session grouping; bounded UTC analysis windows; candidate T and phase; missed cycles; no double attribution |
| Quote diagnostic | `src/RobotDetector.Core/QuoteOscillation.cs` | Best bid/ask quote travel, reversals, tick-normalized oscillation; not an owner detector |
| Spectral analysis | `src/RobotDetector.Core/SpectralCandidates.cs` | Clock-time UTC binning, detrend, Hann, radix-2 FFT, heuristic spectrum peaks (not bot IDs) |
| Synthetic evaluation | `src/RobotDetector.Core/SyntheticBenchmark.cs` | Seeded synthetic public tape, private injected-event truth, null versus injected screening metrics |
| Chronological check | `src/RobotDetector.Core/WalkForward.cs` | Discover candidate from history at or before cutoff, test only a future event |
| CLI | `src/RobotDetector.Cli/Program.cs` | Commands: `detect`, `fetch`, `quote`, `benchmark`, `walkforward`, `spectrum` |
| Offline tests | `tests/RobotDetector.SelfTests/Program.cs` | Deterministic checks without NuGet test packages |
| CI | `.github/workflows/robot-detector-ci.yml` | Isolated .NET 10 compile + offline regressions, no broker secrets |

## Exact current validation status

**GitHub Actions compilation and offline regression SUCCEEDED on 2026-11-18.** Confirmed run: https://github.com/IskanderAbdullin/Analytics/actions/runs/44276050349 — build of Core, CLI and SelfTests: success; 32/32 offline self-tests: success; CLI golden fixture: success; read-only order API sentinel: success. The separate existing IPO CI also succeeded in PR #2. The available local execution container itself lacks `dotnet`; GitHub hosted runner provided the verified build. This is **not** a live-market accuracy validation.

Real public T-Invest archive `SBER_TQBR` for `2026-11-17` was downloaded and parsed via an isolated GitHub Actions runner: **121,920 prints, zero invalid records**. The fixed-volume screen found **209 preliminary candidate episodes**, not 209 verified bots. Data SHA-256 `0af872b1c9c861e7af40a1c40e5bbdf565f9161dd997337c08da584c4dafc782`; log https://github.com/IskanderAbdullin/Analytics/actions/runs/44278450117 . The GZip format and TLS additional Russian Trusted Root CA were verified. Completeness, side semantics, and actual bot identity are still unknown. No live gRPC T-Invest stream connection has been tested or implemented.

## What's done versus remaining stage gates

- **Stage 1, partial:** data contract, ZIP/CSV import, T-Invest public one-day downloader, explainable fixed-volume candidate detector, windowed processing, independent UTC FFT peaks, synthetic golden fixture, CLI. **Remaining:** validate more instruments/days, reconcile candidates across event-count chunks, robust burst assembly, exchange session calendars, full performance metrics and quality stats, more sophisticated candidate fusion.
- **Stage 2, initial:** synthetic injected/null trials with hidden IDs, reproducibility regressions, one-step chronological matching. **Remaining:** ABIDES-NG controlled truth, realistic Hawkes/common-clock null, statistical multiple-testing corrections, held-out calibration, quantitative research report, blind parameters.
- **Stage 3, partially operational:** offline HTML dashboard and secure loopback-only static snapshot service are implemented and tested. No actual `MarketDataStream` subscription, true incremental live state or OsEngine adapter yet. Historical endpoint is **not** a substitute for real-time book/trade streaming.
- **Stage 4, experimental only:** one top-of-book quote oscillation **diagnostic** implemented; no proven iceberg, VWAP/POV, MM, motif, metaorder, or ML detector.
- **OsEngine integration:** no runtime integration; Core is independent by design.

## Known limitations needing action

1. Detector processes **independent bounded UTC time windows** (default 60 minutes); if any individual window exceeds `MaximumEventsPerGroup` (default 5000 events with the same q/source/side), it splits into contiguous event-count chunks and emits `SPLIT_DENSE_GROUP`. Counts across windows and chunks are **episodes**, not deduplicated unique participants across a day; future work should merge persistent hypotheses across boundaries.
2. A period whose timestamp bins alias, source rounding, market-wide clock synchronicity, and harmonics can cause false candidates. No p-values, confidence or FDR control yet.
3. Quote snapshots do not establish feed continuity; quote movement classifier is an observed feature and is **not** an iceberg/spoofing claim.
4. Direction is provider-reported and not identified as passive-order owner. `UNKNOWN` excluded from directional classifications.
5. Session ID defaults to UTC calendar date unless supplied in input. This is not a substitute for MOEX/SPB trade session calendars and halts.
6. Downloader refuses overwritten files and large payloads; archive URL and output extension must agree; archive coverage varies by instrument.
7. CSV reader is line-based with quoted fields but no embedded multi-line quoted records; trade-history file format per official source is single-line records.
8. The single-screen outcome check is not a calibrated probability, nor proof that matched prints belong to the same agent.
9. Import quarantine stores up to 1,000 bad-row **examples**; a detailed count of all rejected rows and full audit output need further refinement.
10. Do not release a claimed number of *actual* physical robot programs or owners from public data.

## Next tasks, in order

1. **DONE (initial build):** GitHub Actions compiled all .NET projects and passed 32 self-tests. Continue adding CI as code grows.
2. **DONE (data parsing only):** verified one real T-Invest SBER archive, file hash, 121,920 prints, 0 rejected; actual bot detection quality and coverage remain unverified.
3. Add sliding windows, phase harmonics/dedup, session-aware calendar, and single-source attribution tests.
4. Add null controls, walk-forward scoring across days, ABIDES realistic truth and blind calibration.
5. Only then implement and verify live gRPC streaming, replay parity, read-only API/UI and OsEngine adapter.
6. Quote-oscillation and advanced categories stay research-only until measured on observed adequate L2 coverage.

## Safe use

No trade endpoints or trade API dependencies in this project. Do not put broker tokens, account data or licensed raw market data in Git. Each result must label `SYNTHETIC`, `HISTORICAL_PUBLIC`, or unknown. Do not publish uncalibrated scores as probabilities.

Official historical trade archive: https://developer.tbank.ru/invest/services/history-md/head-history-md
Official stream API: https://developer.tbank.ru/invest/api/market-data-stream-service-market-data-stream

## Real-data verification log

See [PUBLIC_ARCHIVE_VALIDATION.md](PUBLIC_ARCHIVE_VALIDATION.md) for exact GitHub Actions evidence, GZip detection, pinned CA and one-day SBER result (209 *candidate episodes*). No market data or credentials were checked into Git. Current read-only code does not access private trading accounts. The single-day result is **not a statistically validated number of bots**.

## Stage 2 evidence and live-release gate — updated 2026-11-18

- Dual-null real-data experiment for SBER 16/17 November: 265,849 prints, 126/209 candidate episodes, 120/206 conservatively linked groups. Full conditional-size permutation and circular-shift nulls (12 each per day) returned smaller aggregate counts; their minimum possible Monte Carlo global tail estimate is 0.0769 per null/date and cannot confirm actual bots. Evidence: [MULTIDAY_NULL_PROTOCOL.md](MULTIDAY_NULL_PROTOCOL.md).
- **32/32 self-tests passed** on the rolling-forecast branch, plus CLI goldens and independent original IPO CI. [CI run 44297948977](https://github.com/IskanderAbdullin/Analytics/actions/runs/44297948977).
- Frozen chronological forecast evaluation on **unseen Nov 12/13**: 245,727 public prints, 983 forward-only target windows, **14 hits versus 14 at the T/2-shifted placebo**, both 1.424%. Detailed [ROLLING_REAL_PILOT.md](ROLLING_REAL_PILOT.md), [CI run 44298537864](https://github.com/IskanderAbdullin/Analytics/actions/runs/44298537864).
- **Stage 2 forecasting gate NOT PASSED:** no observed predictive edge with current fixed-volume screen under this test; do not promote candidates to `confirmed`, do not assign owner identities and do not use as automated trading signals. Source feed completeness and session calendars also remain unverified.
- Core module `RollingForecast.cs` and CLI command `rolling-forecast` remain read-only research interfaces. They never execute trades.
- Next work: diagnose phase drift/size changes and common market-clock artifacts on a *separate development set*, calibrate stronger nulls/ABIDES-truth, then evaluate untouched instruments/dates before considering live alerts.

## Nov 19, 2026 — independent alternatives and source-quality gates

**Latest confirmed validation:** 83/83 standalone .NET 10 self-tests, existing main CI remains isolated from IPO code. [Verified Robot Detector CI 44554682245](https://github.com/IskanderAbdullin/Analytics/actions/runs/44554682245). Four additional merged PRs [#18](https://github.com/IskanderAbdullin/Analytics/pull/18), [#19](https://github.com/IskanderAbdullin/Analytics/pull/19), [#20](https://github.com/IskanderAbdullin/Analytics/pull/20), [#21](https://github.com/IskanderAbdullin/Analytics/pull/21) are all read-only.

- `ClockPhaseAudit.cs` — market clock first100ms and **maximum-over-10-bin** statistics, 99 shared-minute rotations, source/mode/session isolation. Real 2026-11-18 SBER peak 200–300ms with descriptive max-tail 0.06; MOEX peak 0–100ms with descriptive max-tail 0.01. The null is approximate and these are NOT calibrated p-values or physical bot counts. [MAX_BIN_PHASE_AUDIT.md](MAX_BIN_PHASE_AUDIT.md).
- `TimestampQualityAudit.cs` — no-dedup collision/resolution diagnostics. 2026-11-18 SBER 83,515 prints, 57,624 distinct timestamps, 32,311 prints in same-time groups; MOEX 10,584 prints, 6,163 distinct timestamps, 5,902 prints in same-time groups. Observed minimum 2µs/1µs gap, not verified source clock precision. [TIMESTAMP_QUALITY_AUDIT.md](TIMESTAMP_QUALITY_AUDIT.md).
- `ObservablePrintClusters.cs` — derived exact timestamp/price/side/source/mode/session grouping with original EventId traces and **exact lot conservation**. SBER row-level 57 fixed-volume candidate episodes versus 64 in a derived-cluster view; MOEX 6 versus 6. Neither is a confirmed real-robot count and the two event definitions are not directly comparable. [OBSERVABLE_PRINT_CLUSTERS.md](OBSERVABLE_PRINT_CLUSTERS.md).
- Full read-only public archive workflow [44554682105](https://github.com/IskanderAbdullin/Analytics/actions/runs/44554682105) processed the same SBER/MOEX 2026-11-18 source tapes and purged raw data after use. This reused development data rather than independent validation of parent-order inference.
- **Key scientific finding:** timestamp collisions and inconsistent clock-phase concentrations across two instruments/dates can cause false impressions of repeated algorithm activity; therefore model choice must use separate event definitions, stronger clustered controls, known-agent ground truth and untouched-date prospective outcomes.

**NOT COMPLETE:** real-time T-Invest MarketDataStream, continuous replay parity, quote/L2 quality and venue-level provenance, UI, production OsEngine client, ABIDES blind truth, calibrated FDR, sustained forecast improvement and reliable physical bot counting. These cannot be claimed successful merely because offline and public-history CI passed.

## Stage 3 engineering progress — verified on 2026-11-19

- [PR #22](https://github.com/IskanderAbdullin/Analytics/pull/22): `ResearchDashboard` aggregates `FlowFootprint`, `FlowActivityEpisodes`, `TimestampQualityAudit` with exact print/lot conservation and HTML escaping. Standalone offline `dashboard --html ... [--json ...]` has no scripts/network or raw event IDs. Real SBER archive 121,920 prints checked in [CI #44570331435](https://github.com/IskanderAbdullin/Analytics/actions/runs/44570331435).
- [PR #23](https://github.com/IskanderAbdullin/Analytics/pull/23): bounded watermark replay `replay-audit` preserves prints and logs queue pressure/late archive-record order. On SBER [CI #44572400620](https://github.com/IskanderAbdullin/Analytics/actions/runs/44572400620), all prints and 19,769,931 lots conserved. 54,429 apparent late records result from **archive row order** and do NOT measure actual network delay; ideal exchange-time sorting returns zero.
- [PR #24](https://github.com/IskanderAbdullin/Analytics/pull/24): `compare-archives` creates source-comparable standalone HTML for 2–20 files; refuses duplicate SHA or inconsistent window width. [CI #44573901868](https://github.com/IskanderAbdullin/Analytics/actions/runs/44573901868): SBER 121,920 and MOEX 15,208 prints processed, no physical bot identity inferred.
- [PR #25](https://github.com/IskanderAbdullin/Analytics/pull/25): separate `RobotDetector.Server` .NET 10 Web application serves immutable historical snapshot on **127.0.0.1 only**. Read-only `GET /, /api/v1/health, /api/v1/summary`; non-GET/HEAD rejected, forged Host/Origin rejected; no trading endpoints or broker account API. CI [#44575738794](https://github.com/IskanderAbdullin/Analytics/actions/runs/44575738794) confirmed HTTP security checks and **108/108 SelfTests**. Original IPO CI also successful.
- **Stage 3 snapshot/UI engineering gate: PASSED.** **Stage 3 live market-data integration gate: NOT PASSED.** No authenticated MarketDataStream, real network receive clock, reconnect/reconciliation, true incremental streaming through the whole pipeline, or OsEngine client application yet. Bounded replay currently preloads the whole archive before it limits the pending queue.
- **Stage 2 scientific bot-identification and forecast gates remain NOT PASSED.** The fixed-clip prospective SBER sample had 14/983 hits, identical to placebo. All visible patterns and high-activity indicators are observable data, not IDs or trade signals.

See [OFFLINE_RESEARCH_DASHBOARD.md](OFFLINE_RESEARCH_DASHBOARD.md), [BOUNDED_EVENT_REPLAY.md](BOUNDED_EVENT_REPLAY.md), [MULTI_ARCHIVE_RESEARCH_COMPARISON.md](MULTI_ARCHIVE_RESEARCH_COMPARISON.md) and [LOCAL_READ_ONLY_API.md](LOCAL_READ_ONLY_API.md).


## Stage 2 blind generator evaluation — executed 2026-11-19

- [PR #26](https://github.com/IskanderAbdullin/Analytics/pull/26): no-NuGet `BlindExecutionBenchmark` with four stylized scenarios, opaque public event identifiers, hidden producer truth excluded from both detectors, exact event-level TP/FP and controlled partial fills.
- [GitHub Actions #44577833225](https://github.com/IskanderAbdullin/Analytics/actions/runs/44577833225): **116/116 deterministic tests**, .NET server/Core/CLI compiled and all integration smokes green; separate legacy IPO CI also passed.
- Small **2 seeds/scenario and 35 background prints/case**: fixed-q TWAP yields 24/24 synthetic controlled prints for fixed-q detector versus 0/24 for variable-clip; variable-q TWAP yields 0/24 for fixed versus 24/24 for variable; split two-print child fills yield 32/48 for fixed versus 24/48 for variable. No TP on clustered null, but zero false positives on two easy toy null seeds **does not** establish real market precision. Details: [BLIND_EXECUTION_BENCHMARK.md](BLIND_EXECUTION_BENCHMARK.md).
- Same public tape was evaluated with 1 vs 2 different hidden controlled producer assignments and detector outputs remained identical. **Number of actual independent physical robot programs is not generally identifiable from anonymous prints.**
- **Scientific Stage-2 release gate remains CLOSED.** The benchmark is not ABIDES matching/queue simulation and has no market-calibrated null, per-pattern p-values, real future edge, identified owners or trading recommendations.
- Next priority: genuine controlled ABIDES-NG public projection with independently hidden execution-agent truth and large stratified nulls, then frozen held-out data; live T-Invest connection remains a separate engineering task requiring scoped user-supplied access.


## 2026-11-21 — adversarial market-clock negative controls (Stage 2)

- [PR #28](https://github.com/IskanderAbdullin/Analytics/pull/28) on `agent/robot-detector-clock-null-20261121`: standalone synthetic public-clock negative controls with *zero* repeated controlled producers, two periodic background quantity profiles (fixed / cycling clip sizes), and a CLI `benchmark-clock-null`. Producer truth is held outside both detectors.
- [Successful CI #44888523166](https://github.com/IskanderAbdullin/Analytics/actions/runs/44888523166): **120/120** original no-NuGet deterministic checks and new fixed/variable-clock CLI smokes passed. Local Windows .NET 10.0.402 solution build and `dotnet test` adapter also succeeded without warnings/errors.
- With 3 seeds and 60 independent background prints per case: fixed-q detector attributed **81/180** events in 3/3 constant-q clocked nulls; variable-q detector attributed **81/180** events in 3/3 changing-q clocked nulls. Neither source had a controlled execution agent. These are **toy-model false attributions**, not calibrated exchange FPR or unique robot IDs; the complementary screens missed the other profile's adversarial signal.
- Validated report interpretation and reproduction: [CLOCKED_NULL_STRESS.md](CLOCKED_NULL_STRESS.md); [LOCAL_WINDOWS_TESTING.md](LOCAL_WINDOWS_TESTING.md).
- **Stage-2 scientific identity/accuracy gate remains CLOSED**. Next validation requires real matching/queue simulation with hidden independent producer truth, calibrated source-specific nulls, frozen out-of-sample dates/instruments and source timestamp/coverage checks. Do not connect to live trading or call any inferred count a physical robot count.

## 2026-11-21 — genuine ABIDES-NG blind execution and frozen seeds

- New **real ABIDES-NG exchange matching-engine** simulation importer and post-hoc private-truth scorer: `AbidesBlindEvaluation.Score`, CLI `benchmark-abides-blind`, Python `tools/abides_export.py`. Upstream pinned at [ac7a2a7](https://github.com/GabrieleDiCorato/abides-ng/tree/ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242). Verified simulator actions in [GitHub CI #44890937246](https://github.com/IskanderAbdullin/Analytics/actions/runs/44890937246) with **123/123 C# self-tests**, Python exporter tests and actual controlled positive/null fill reconciliation.
- Initial ABIDES seed 41 TWAP: 3,923 prints, 44 controlled executions; fixed-q true positives 30, false positive 0, missed 14. Null seed 42: 3,060 prints, no attributed patterns; these are descriptive observations, not real-world precision or calibrated FDR.
- Frozen seeds **901,902,903,904**: four TWAP exchange runs gave 14,761 public fills and 197 controlled TWAP prints; fixed-q detected 101, missed 96, no false attributed prints in these runs; variable-q detected 0. Four negative-control matching runs gave 14,639 public fills and no model attributions. No real-market FDR or predictive edge established.
- Two additional, separate ABIDES controlled execution regimes: VWAP seed 43 had 50 controlled prints (3,788 total) and POV seed 44 had 14 (3,702 total). Both current detectors missed all controlled prints in those runs. These are important falsifiable limitations, not evidence of absent algorithms.
- Post-hoc controlled execution size/time diagnostics added to the score schema; they use privileged synthetic labels **only after detector output** and are never allowed as model inputs during this test. Complete details: [ABIDES_GENUINE_REPLAY.md](ABIDES_GENUINE_REPLAY.md).
- Local Windows PC-Agent .NET build and `dotnet test` remained successful; the Python genuine matching engine itself ran in isolated GitHub Actions (not installed on MYPC). Local workspace remains a source snapshot, not a Git clone. No real accounts/orders/GUI touched.
- **Research Stage-2 accuracy / actual bot-identity gates remain CLOSED.** Next: diagnose VWAP/POV missed prints, design candidate model only on development data, and freeze entirely new independent real-simulator and future-market holdouts before any sensitivity/specificity claims.

## 2026-11-21 — public-only volume lag research, issue #31

- Added `VolumeResponseResearch` and CLI `volume-response` to study relationship between **previous completed public-market volume** and current reported BUY/SELL volume. Every observation remains anonymous and separated by UID/ticker/source/mode/session/data-kind; missing populated bins are not zero-filled; same public event ID cannot be double counted. Unlike private ABIDES post-hoc diagnostics, this module **never consumes hidden agent attribution**.
- Added five deterministic tests for arithmetic, public lot accounting, past-only observation stability under later prints, gap handling, source/session isolation, constant signals, input bounds and duplicate IDs. [GitHub .NET CI #44891939160](https://github.com/IskanderAbdullin/Analytics/actions/runs/44891939160): **128/128** C# internal checks and CLI public-only fixture smoke passed.
- First genuine ABIDES spent *development* cases (seeds 41 TWAP, 42 null, 43 VWAP, 44 POV, 30-second bins): null showed **rho BUY 0.695 / SELL 0.765**, which exceeds TWAP (**0.394 / 0.240**) for both sides. Association alone cannot identify a robot.
- Implemented an independent development seed survey (`tools/volume_response_dev_survey.py`), public-only, explicitly refusing previously evaluated 901–904 seeds. [Successful genuine ABIDES CI #44892179775](https://github.com/IskanderAbdullin/Analytics/actions/runs/44892179775): nine actual matching-engine simulations (null/POV/VWAP × 61, 62, 63). Median lagged Spearman rho BUY/SELL: **null 0.510/0.548; POV 0.538/0.501; VWAP 0.511/0.596**. These values overlap and cannot justify any standalone actor detection claim.
- Verified versioned GitHub artifact `abides-public-volume-development` preserves only public fingerprints and summary coefficients, without private maker/taker labels, expiring 2026-12-05. Full methodology and scientific references: [VOLUME_RESPONSE_PUBLIC.md](VOLUME_RESPONSE_PUBLIC.md).
- Current research outcome: a reproducible **negative finding** for standalone volume-lag identification in these simulated samples. No candidate threshold, owner count, calibrated significance, real-market accuracy or automated trading functionality was created. **Stage-2 scientific release gate CLOSED.** Existing fixed-q, variable-q, historical validation and ABIDES execution workflows remain unchanged in their logic.
- Windows local PC-Agent source sync was temporarily restricted by `HTTP 429` during this stage; do **not** claim this latest branch was built locally. Its code was compiled/tested on GitHub runners. The prior Windows snapshot/build was successfully tested in the previous stage.

## 2026-11-21 — public-only directional regime-shift research

- Added `DirectionalRegimeShiftResearch` and CLI `direction-shift` as a new **public-only retrospective** windowed reported BUY-share change monitor. Different from periodic clip screens and the previous volume-lag rho descriptor: it compares current qualified known-side volume against exactly six **earlier** contiguous eligible bins; unknown-side contamination, missing bins and oversized source groups fail closed.
- Added six deterministic no-NuGet C# tests for exact 50/50→90/10 shift arithmetic, stable source null, independence from future appended prints, session/UID isolation, unknown/gap handling, cooldown and invalid settings. Test adapter threshold raised from 128 to **134** checks, verified on [.NET CI #44893110208](https://github.com/IskanderAbdullin/Analytics/actions/runs/44893110208).
- Added source-agnostic CLI fixture smoke, and a new real ABIDES-NG null-first exploratory survey on **new development seeds 71–73**, across null/VWAP/POV. All features and outputs use **public data only**, never the private maker/taker manifest. Previously evaluated 901–904 and development 41–44,61–63 are excluded from the new survey.
- New [documentation](DIRECTIONAL_REGIME_SHIFT.md) covers no future leak, unknown-side quality threshold, multiple-testing limitations and explicit non-equivalence to BOCPD/CUSUM. The new 0.25 share threshold is *not statistically calibrated*. If market-wide null produces the same shift, label remains an unvalidated market observation **not a robot**.
- **Stage-2 real-world scientific/identity gate remains CLOSED**. No real-order API calls, no live alerts, no modifications to OsEngine or physical actor identification.

- The nine **genuine** ABIDES development simulations passed in [CI #44893110253](https://github.com/IskanderAbdullin/Analytics/actions/runs/44893110253). At fixed defaults each cohort had 162 eligible bins: no-controlled-agent null **1** candidate, VWAP **4**, POV **2**. Actual exchange prints totaled 9,526 (null), 9,796 (VWAP), 9,448 (POV). Candidate counts are merely descriptive public group-level changes; **null also emitted**, proving no unique actor attribution. A terminal archive bin may not be complete absent a separate watermark.
- A **pre-registered synthetic replication** cohort of four untouched seeds (1101–1104), the same three modes and unchanged thresholds has been committed as `directional_shift_frozen_replication.py`, together with a locked-plan Python test and an aggregate-only Actions artifact. Its outcomes must be collected strictly without subsequent parameter fitting and never represented as calibrated market specificity.
- The source snapshot on Windows MYPC was resynchronized using MCP after the earlier HTTP 429; .NET 10 **local build 0 warnings/errors** and **local `dotnet test` successful** using the 134-check adapter. The standalone ABIDES matching engine ran on GitHub Actions, not on this machine. The local `.git` workflow remains policy-denied; GitHub connector handles commits/push.

- **Outcome of pre-registered untouched-seed replication:** [Successful real ABIDES CI #44893601107](https://github.com/IskanderAbdullin/Analytics/actions/runs/44893601107), matching engine seeds 1101–1104, three modes each, **12 simulations** total, exactly the prior 30-second/6-reference-bin/0.25-share threshold unchanged. At 216 evaluated public clock bins per cohort: agent-free null **1** candidate shift window from 13,798 public prints (1/4 scenarios), VWAP **0** candidates from 14,007 prints (0/4), POV **1** candidate from 13,753 prints (1/4). The earlier exploratory pattern (null 1, VWAP 4, POV 2 on three development runs) **did not reproduce**. Thus this simple public directional share-shift is **not a reliable standalone VWAP/POV detector** in these ABIDES backgrounds; no fill-level attribution, calibrated market FDR, predictive edge or identified bot is established. Frozen 1101–1104 are now **spent** and must never be treated as unused for model selection.
- The summary-only `abides-public-direction-shift-frozen` artifact from CI #44893601107 is available on GitHub Actions with retention until 2026-12-05. No private maker/taker attribution data is included. A separate background-only null produced an observed public shift even without an injected controlled execution agent. **Do not deploy live alerts or promote this candidate to a physical actor classifier.**

## 2026-11-21 — frozen genuine ABIDES executed-fill strategy baseline

- Pre-registered **unmodified** original fixed-q and variable-q C# screener defaults against genuine ABIDES-NG synthetic matching-engine executions: **16 scenarios** (four new seeds 1301–1304 × null, TWAP, VWAP, POV). Strict SHA-256 one-to-one public/private event mapping, private maker/taker labels for scoring only *after* detection. [Successful CI #44894042225](https://github.com/IskanderAbdullin/Analytics/actions/runs/44894042225), 134/134 C# self-tests plus Python frozen-plan/accounting tests.
- **Fixed-q:** TWAP **98 TP / 0 FP / 85 missed** out of 183 controlled fills (**53.55%** synthetic event recall); VWAP **6 TP / 0 FP / 185 missed** out of 191 (**3.14%**); POV **0 TP / 0 FP / 66 missed** (0%). Agent-free null had 13,773 public fills, **zero** candidate attributions; true positive recall undefined.
- **Variable-q:** zero attributed prints, and hence zero controlled-print recovery, across all 16 scenarios (including 183 TWAP + 191 VWAP + 66 POV controlled fills). Event precision **undefined**, not 0% or 100%, when nothing is predicted. This is a strategy-dependent weakness of the current synthetic baseline; *not* an exchange-calibrated real-market failure probability.
- Exactly **4/4 TWAP**, **1/4 VWAP**, **0/4 POV**, **0/4 null** fixed-q cases had any attribution. No source, confidence or participant ownership identified. Neither screen was trained or tuned using this newly spent 1301–1304 evaluation cohort.
- Reproducible research code: `tools/abides_execution_baseline_holdout.py`, `tests_python/test_abides_execution_baseline_holdout.py`, [ABIDES_GENUINE_REPLAY.md](ABIDES_GENUINE_REPLAY.md). GitHub Actions aggregate-only artifact `abides-frozen-executed-strategy-baseline` expires 2026-12-05; private maker/taker manifests never included.
- **Scientific decision:** the two original periodic screens, the public volume-lag rho and directional-shift features are not reliable validated VWAP/POV detectors in the tested synthetic market regimes. Future work requires explicit alternative public observables, independent null families and fresh untouched holdouts. **Stage-2 market identity, statistical accuracy, live alert and trading release gates remain CLOSED.**

## 2026-11-21 — genuine simulated L2 order-book feasibility, no real market history

- Verified [ABIDES L2 CI #44894589485](https://github.com/IskanderAbdullin/Analytics/actions/runs/44894589485): pinned genuine ABIDES-NG `ResultProfile.QUANT` and `ExchangeConfig(book_capture='l2', book_log_depth=5)` produced **1,152** depth-5 update snapshots from a five-minute simulated exchange session and **709** executed trade prints; 661 two-sided, 457 one-sided, 34 empty snapshots. Unique snapshot timestamps **718**; **434 additional updates shared a timestamp**, therefore deduplicating solely by exchange time would lose public quote transitions. All 661 two-sided snapshots had positive best spread; three zero-dependency schema tests passed.
- The new optional `tools/l2_probe.py`, `tests_l2/test_l2_probe.py` and separate no-secrets CI create/upload only aggregate data; no source owner IDs, trading accounts or raw level events in the artifact.
- Current public T-Invest [historical instrument archive](https://developer.tbank.ru/invest/services/history-md/head-history-md) documents **anonymous executed trades and minute candles**; it does **not document retrospective L2 book archives** in that service. Current [GetOrderBook](https://developer.tbank.ru/invest/api/market-data-service-get-order-book) and [MarketDataStream](https://developer.tbank.ru/invest/api/market-data-stream-service-market-data-stream) provide a distinct **live/current** data path, which has not been connected or measured here. Do not mislabel simulated ABIDES L2 as real T-Invest L2.
- Method [L2_FEASIBILITY.md](L2_FEASIBILITY.md) includes source provenance, schema validation, known timestamp collision risk, data accessibility limits and new conditional-null gate. Public L2 depth has no private identity, therefore **no physical robot count or calibrated real VWAP/POV performance** follows. Stage-2 scientific gate CLOSED.

## 2026-11-21 — new public-only L2-to-trade context audit

- Added `tools/l2_trade_context.py` to join actual ABIDES matching-engine fills to only **strictly previous** depth-five L2 snapshots; same-time snapshots force abstention, multiple same-time quote mutations remain preserved. No causality from row ordering, private maker/taker agent fields, or future quotes.
- Added six no-ABIDES dependency regression tests in `tests_l2/test_l2_trade_context.py`: exact-time abstention, future append independence, observed lot/count conservation, prior-book quality categories, placebo marginal preservation and false identity/probability claims. No existing C# bot model changes.
- Separate real ABIDES three-mode **development-only** run at seed 1501 (null/POV/VWAP) and a clearly invalid-for-FDR public print/side/size rotation placebo are included in the L2 CI workflow. The experiment's purpose is public quote/print data sensitivity, **not** statistical confirmation of agent detection. Raw book/trade files or agent IDs are not published.
- Scientific method: [L2_TRADE_CONTEXT.md](L2_TRADE_CONTEXT.md). Synthetic-only public context, no known historic T-Invest L2; release gate CLOSED.

## 2026-11-21 — genuine L2-to-fill timing and abstention

- [ABIDES L2 CI #44895496910](https://github.com/IskanderAbdullin/Analytics/actions/runs/44895496910): the new public-only strict prior-book quote/print audit and **9** Python tests passed. Genuine simulation seed 1501: null **1,443** L2 updates and **917** prints, POV **1,266** updates and **797** prints, VWAP **1,440** updates and **916** prints.
- **All 2,630 executed fills exactly matched some book mutation timestamp and were therefore correctly unclassified as `same_timestamp_ambiguous`; 0 eligible strict prior-quote price comparisons.** 1,440 additional L2 snapshots shared existing update timestamps. No natural-versus-rotated alignment could be evaluated (undefined denominator). Exact timestamps are insufficient to establish intra-time event sequence; do not fabricate ordering by row or quote index.
- Existing model sensitivity or false-positive statistics **must not** be revised from this dataset. New methodology must use a **previous completed clock-bin public-book exposure** and describe subsequent public whole-bin print outcomes with independent nulls; source event sequence would be required for within-timestamp causal alignment. Seed 1501 is spent. Research gate remains CLOSED.

## 2026-11-21 — previous-completed-clock-bin L2/public-print view

- Added `tools/lagged_l2_bin.py` with a *strictly previous completed bin* depth-five L2 imbalance versus current observed reported-buy share; do not infer causal same-time book/print order or physical owners.
- Clock-bin source gaps, stale quotes, one-sided/empty and locked/crossed books abstain explicitly; original L2 repeated timestamps are preserved. Ties-aware Spearman returns null for under five eligible bins or constant values. A bin-share rotation is only a descriptive sensitivity control, **not** a valid market null/p-value.
- Added six no-ABIDES-dependency tests for monotone lag associations, missing bins and stale data, future snapshot independence, same-time previous-bin preservation, constant backgrounds and invalid input; integrated into the existing L2 workflow's genuine null/POV/VWAP simulations **without increasing simulated run count**, reusing same public tapes.
- See [L2_LAGGED_BIN.md](L2_LAGGED_BIN.md). Earlier seed 1501 is development-only and spent. No physical robot attribution, real L2 coverage, traded order or accuracy claims. Stage-2 scientific release gate CLOSED.

- **Executed previous-bin L2 study:** [successful actual ABIDES CI #44895877902](https://github.com/IskanderAbdullin/Analytics/actions/runs/44895877902), **15/15 Python L2 integrity tests** and .NET CI passed. Across spent development seed 1501, valid previous-bin quote/next-bin trade pairs were **13 null, 10 POV, 13 VWAP**. Descriptive rank correlation between previous depth-five imbalance and next-bin public BUY fraction: **null −0.341, POV 0.152, VWAP 0.104**; rotated-bin placebo **0.159/0.115/0.247**, respectively. These cannot support market-wide specificity, calibrated significance or hidden-parent-order attribution. Exact-timestamp individual execution join remained 100% abstention. No threshold tuning on seed 1501.

## 2026-11-21 — adversarial public L2 common-factor nulls

- Implemented `tools/l2_common_factor_null.py`, four **non-ABIDES** synthetic public-book/next-trade null families: common market state, independently shuffled next-flow, a market-wide synchronized directional shock, and exact quote/fill clock synchronization. No private actor label or individual parent order is generated. The purpose is structural non-identifiability: public book/flow correlation alone is insufficient to identify a trader.
- Added five deterministic pure-Python unit tests and a lightweight standalone [no-ABIDES GitHub workflow](../../.github/workflows/robot-detector-public-l2-nulls.yml) with seven-day aggregate-only artifact, avoiding excessive ABIDES simulation runtime. Do not call these real conditional market nulls or calibrated FDR evidence.
- Method [L2_COMMON_FACTOR_NULLS.md](L2_COMMON_FACTOR_NULLS.md); no user trading account, GUI, real orders or OsEngine runtime. Stage-2 market identity release gate CLOSED.

- **Executed public common-factor counterexample:** [Successful lightweight GitHub CI #44896188923](https://github.com/IskanderAbdullin/Analytics/actions/runs/44896188923), five pure unit tests. Synthetic seed 1701, 24 bins and 144 public prints/2,400 lots per scenario. Constructed common-market-factor and market-wide shock backgrounds yielded `rho=1.000` between completed previous-book imbalance and next-bin reported BUY share **without generating any identified parent order**. Independently shuffled flow rho −0.195; synchronized quote/fill clock caused 144/144 strict event joins to abstain. This proves a **logical non-identifiability counterexample**, not realistic market likelihood or false discovery calibration. No actual ABIDES matching or user market data used in this cheap CI.

## 2026-11-21 — pre-registered genuine ABIDES public L2 background null family

- Added `tools/abides_l2_background_nulls.py` with genuine pinned ABIDES-NG matching, six fixed source-controlled cases: previously unused seeds 1801/1802 × three **background-only** variants: 60 Poisson noise agents, 60 fixed-cadence noise agents, and 50 Poisson noise + 10 momentum agents (all no injected TWAP/VWAP/POV execution program). This is *not* an agent-free market, and cannot identify real physical owner counts.
- Previous completed bin's depth-five L2 imbalance is compared strictly with later completed public trade-bin direction. Private maker/taker IDs are never features; full aggregate print/lot counts and eligible/abstained pairs are checked. No future leak, no threshold training, no real account orders or GUI.
- Added five fast frozen-plan/aggregate-invariant Python tests and a separate seven-day aggregate-only genuine-ABIDES GitHub workflow, using the exact pinned upstream revision. Document [ABIDES_BACKGROUND_L2_NULLS.md](ABIDES_BACKGROUND_L2_NULLS.md).
- These new development seeds are used to **describe the null family only**. After the experiments, they are spent and must not be used as fresh independent holdouts. Stage-2 calibration and actor-identity release gates remain CLOSED.

- **Executed frozen genuine ABIDES background nulls:** [success #44902051089](https://github.com/IskanderAbdullin/Analytics/actions/runs/44902051089), **5/5 Python frozen-contract checks**, exactly 6 genuine exchange simulations across 1801–1802, 3 no-injected-TWAP/VWAP/POV background cohorts. Poisson noise 3,210 prints / 5,345 L2 updates / 39 lagged eligible bins, **median rho −0.5094**; fixed-cadence noise 3,150 / 5,113 / 41, **−0.3607**; noise plus momentum agents 2,932 / 4,964 / 41, **−0.2008**. All six case correlations evaluable. [.NET CI #44902050995](https://github.com/IskanderAbdullin/Analytics/actions/runs/44902050995) also passed.
- All negative coefficients in this tiny synthetic sample indicate **background-dependent public association**, **not** a calibrated market failure/false-alarm rate or participant count. Momentum agents are automated participants; the only exclusion is *named separately injected TWAP/VWAP/POV parent execution agents*. Frozen seeds 1801/1802 are now spent. Seven-day aggregate artifact: `abides-genuine-l2-background-nulls`. Stage-2 research/real-trading release gate CLOSED.

## 2026-11-21 — safe terminal-bin watermark for public lagged L2 analysis

- Added optional `complete_through_ns` to `summarize_lagged_book` for **explicit caller-attested exclusive archive completion**. Bins ending *after* watermark are unscorable (`current_bin_not_closed_by_watermark`), not counted as real complete 30-second trade outcomes. The caller's attestation is not independently verified by the function; default historical behavior is preserved but marked terminal-bin completeness UNVERIFIED.
- Six new pure-Python regression tests in `tests_l2/test_lagged_l2_watermark.py` assert terminal abstention, closed-interval edge conditions, append-only stability, missing coverage and strict invalid input. No changes to original .NET detector, real market accounts or OsEngine.
- See [L2_ARCHIVE_WATERMARK.md](L2_ARCHIVE_WATERMARK.md). The feature is only a guard for future trustworthy public data archives; **previous ABIDES coefficients are not retroactively a full-source-coverage proof**. Physical bot identification/market FDR/trading gate CLOSED.

## 2026-11-21 — new frozen genuine ABIDES bin-width sensitivity cohort

- Added `tools/abides_l2_binwidth_sensitivity.py`: fresh development-only seeds `1901,1902`, `poisson` versus `fixed_cadence` 60-agent background, 12-minute genuine matching-engine sessions, four **actual** runs total and three prespecified analyses of the **same public L2/anonymous fill tapes** (10, 30, 60 seconds).
- No fitted classifier, threshold selection, future quote leakage, inferred private bot owner or real-market FDR. Same public projection SHA/counts/lots/book snapshot totals are verified across widths; archive completion remains explicitly **unverified** without a trustworthy upstream watermark.
- Six offline invariance tests plus a pinned-ABIDES `.github/workflows/robot-detector-abides-binwidth.yml` workflow with seven-day aggregate-only artifact. Full protocol: [ABIDES_L2_BINWIDTH_SENSITIVITY.md](ABIDES_L2_BINWIDTH_SENSITIVITY.md). Stage-2 live and identity release gates CLOSED.

- **Executed frozen genuine ABIDES bin-width robustness:** [successful CI #44903121650](https://github.com/IskanderAbdullin/Analytics/actions/runs/44903121650), **6 pure Python tests**, 4 genuine ABIDES matching-engine simulations, 12 explicitly **non-independent** same-tape analytical cases at predeclared widths 10/30/60s. Poisson two-seed median rho **−0.2430/−0.1271/+0.2061**, with **123/40/20** eligible lagged clock bins; fixed-cadence median rho **−0.2776/−0.4279/−0.1929**, with **95/33/14** eligible bins. Source public prints, lots, L2 count and SHA fingerprint were identical within each simulation across widths. **Poisson two-seed median changes sign under rebinning**, a negative robustness finding; not a signal, independent p-value or per-run prediction. Source completeness unverified. Seeds 1901/1902 spent; no width selected post hoc.

## 2026-11-21 — explicit frozen research seed ledger and replay guard

- Introduced machine-readable `research/seed_registry.json` for all **known** spent canonical ABIDES development/evaluation and constructed toy seeds: 41–44, 61–63, 71–73, 901–904, 1101–1104, 1301–1304, 1401, 1501, 1701 (toy), 1801–1802, 1901–1902. The later same-seed 1501 study is declared an explicitly **non-independent replay**, not a new blind holdout.
- `tools/research_seed_registry.py` validates unique records, exact replay provenance, AST-literal frozen source constants in four Python experiments, and fails closed for known-spent proposed seeds. It explicitly cannot prove globally unseen status of a new number. Added seven pure standard-library tests and lightweight source-path-triggered CI `robot-detector-seed-ledger.yml`.
- Full protocol [RESEARCH_SEED_REGISTRY.md](RESEARCH_SEED_REGISTRY.md). This is a research artifact provenance gate, **not** a model performance test, real-market accuracy calibration, trading signal, or participant identifier. Stage-2 scientific release remains CLOSED.

- **Verified seed provenance source gate:** [successful GitHub CI #44903479712](https://github.com/IskanderAbdullin/Analytics/actions/runs/44903479712) passed **7/7 pure Python tests**, 11 canonical records / **29 known spent** seed values, **4 frozen source constant matches**, 1 non-independent replay. Absent seeds remain only "not in local ledger", **not proven globally unused or validated blind holdouts**. No simulator rerun required. Includes AST-only read rather than importing execution code.

## 2026-11-21 — separate public book/trades completeness declarations

- Added immutable `PublicStreamClaim` / `DualPublicStreamClaim` to validate independent **caller-provided** L2 and public-trades interval coverage. Each stream has a distinct claimed time range, half-open missing segments, source string, instrument, venue and session. Matching labels are checked but **not independently verified against the raw public tape**. Source gap detection never purports to certify actual broker delivery.
- Optional `source_coverage` on `summarize_lagged_book` abstains for uncovered entire previous-book or current-trades bins before reporting descriptive L2-vs-flow rho. Existing archive `complete_through_ns` still functions separately. New `stream_coverage_independently_verified=false` and `raw_stream_source_identity_verified=false` prevent false coverage assurances.
- Seven no-simulator tests and cheap independent Python CI include mismatch/boundary/gap rejection, source pair conservation and prior watermark regression. Full contract: [L2_DUAL_STREAM_COVERAGE.md](L2_DUAL_STREAM_COVERAGE.md). Stage-2 physical ownership/market-statistics/live-trading release remains CLOSED.

- **Executed optional two-stream public coverage gate:** [success CI #44911006336](https://github.com/IskanderAbdullin/Analytics/actions/runs/44911006336), **7 new feed-integrity tests + 6 watermark regression tests**, and [successful pinned genuine ABIDES L2 CI #44911006251](https://github.com/IskanderAbdullin/Analytics/actions/runs/44911006251). Caller-supplied coverage claims cannot prove raw provider completeness; no trader identities, trading or real-market FDR released.

## 2026-11-21 — strict public timestamp/price/lot integer validation

- Corrected potentially lossy integer coercion in the public L2 snapshot, public execution projection/join and lagged L2 analysis paths: new `public_numeric.exact_nonnegative_integer` uses the standard `operator.index` protocol and refuses fractional/numerically-integral floats, booleans, decimal/text strings and invalid negative/zero exchange values. Existing valid int fixtures retain identical behavior.
- Added eight no-ABIDES tests in `tests_l2/test_public_numeric.py`, covered by the existing L2 CI; no additional expensive ABIDES workflow is needed. Documentation: [L2_PUBLIC_NUMERIC_INTEGRITY.md](L2_PUBLIC_NUMERIC_INTEGRITY.md). This fixes one class of source-data distortion, not feed completeness, exchange causal ordering, physical bot identity or real-market FDR.

- **Executed strict public numeric integrity CI:** [successful pinned ABIDES run #44911366203](https://github.com/IskanderAbdullin/Analytics/actions/runs/44911366203), **41 Python tests** including 8 new strict scalar tests; prior genuine simulator public L2/print outputs remain consistent. No truncation of float/string/decimal/boolean values into tick price, lots or timestamp in the public analysis paths. Source authenticity/coverage remain unverified.

## 2026-11-21 — strict unique-price L2 structure

- Strengthened `l2_probe.audit_l2_public`: duplicate or reversed prices inside one aggregated L2 side now fail closed (bid prices strictly decreasing; ask prices strictly increasing), preventing double-counting at the same level in the previous-bin public imbalance. Repeated timestamps across separate snapshots are **still preserved**.
- Added six deterministic no-ABIDES tests in `tests_l2/test_l2_level_uniqueness.py`, including source-level rejection in both public join and lagged-L2 analytics. Document: [L2_UNIQUE_PRICE_LEVELS.md](L2_UNIQUE_PRICE_LEVELS.md). Must not apply this aggregated-L2 rule directly to per-order L3 feeds. Real feed provenance and bot-identity claims remain unverified.

- **Verified strict unique-price L2 source check:** [successful pinned ABIDES CI #44911604350](https://github.com/IskanderAbdullin/Analytics/actions/runs/44911604350) passed **47 Python tests**, including six new duplicate-level checks, while genuine 1,152-snapshot / 709-fill feasibility output remained unchanged. Research/market release gate stays CLOSED.

## 2026-11-21 — append-only and separate-feed-gap metamorphic invariants

- Added `tools/public_feed_metamorphic.py` generating purely synthetic public L2/anonymous print fixture tapes and checking six correctness properties: append-only closed-prefix stability, monotone decreases under book-feed gaps, independent trades-feed gaps and combined gaps, exclusive watermark tightening, and explicit eligible/abstained trade-bin conservation.
- Five Python offline tests plus independent lightweight `.github/workflows/robot-detector-feed-metamorphic.yml` run 64 deterministic source-only fixtures without a genuine ABIDES matching-engine simulation. No hidden maker/taker IDs, real broker market data or trading. [L2_PUBLIC_METAMORPHIC.md](L2_PUBLIC_METAMORPHIC.md). Test seed labels are not scientific held-out real simulations.

- **Executed read-only public-feed metamorphic stress:** [GitHub CI #44911963501](https://github.com/IskanderAbdullin/Analytics/actions/runs/44911963501) **5/5 tests plus 64 generated synthetic software fixtures**, all append-only closed-prefix, independent declared L2/trades gaps, watermark tightening and eligible/abstained bin conservation checks passed. Reference 8 eligible bins declined to 7 with one source gap, 6 with both, and 6 with tighter watermark. [.NET CI #44911963474](https://github.com/IskanderAbdullin/Analytics/actions/runs/44911963474) and [seed provenance CI #44911963433](https://github.com/IskanderAbdullin/Analytics/actions/runs/44911963433) also succeeded. Synthetic fixtures do NOT represent empirical exchange participants or real-market FDR.

## 2026-11-21 — preregistered genuine ABIDES 30-second clock-origin robustness

- Added `tools/abides_l2_binphase_sensitivity.py` with previously unused **2101/2102** genuine ABIDES development seeds, two frozen Poisson/fixed-cadence noise backgrounds, one 30-second bin width, and fixed **0/10/20-second phase offsets**. Exactly four actual matching-engine tapes are reanalysed into twelve correlated public clock-origin views; unchanged original public SHA, prices, lots, side and relative event timing are checked. No phase tuning, hidden maker/taker IDs, trade signals, exchange market FDR or physical owner claims.
- Six source-only tests and an isolated pinned genuine ABIDES workflow; seed registry extended to **12 canonical studies / 31 known spent seeds / five frozen source constants**, with CI trigger for future source drift and documentation [ABIDES_L2_BINPHASE_SENSITIVITY.md](ABIDES_L2_BINPHASE_SENSITIVITY.md). All later independent scientific evaluations must use new genuinely untouched held-out data. Stage-2 release gate CLOSED.

- **Executed genuine 30-second clock-origin sensitivity:** [successful ABIDES CI #44912441330](https://github.com/IskanderAbdullin/Analytics/actions/runs/44912441330), **6 frozen-plan Python tests**, 4 actual matching-engine simulations, 12 correlated public analytic views. Two-seed median Poisson rho **−0.0137 / −0.1608 / −0.1809** with **39 / 42 / 41** eligible lagged-bin pairs across offsets 0/10/20 seconds; fixed-cadence rho **−0.2178 / −0.1946 / −0.4925** with **42 / 41 / 42** pairs. No median sign flip in this phase survey, but magnitude changes substantially on identical tapes. All original public SHA, book events, prints and lots conserved; source completeness unverified, no threshold/model/phase selected. Seeds 2101/2102 spent.
- [Successful research provenance CI #44912522820](https://github.com/IskanderAbdullin/Analytics/actions/runs/44912522820) confirmed the updated 12-study/31-seed ledger and five frozen source constants; earlier example 2101/2102 became spent and therefore had to be replaced with nonregistered 2201/2202, which are **not globally verified fresh**.

## Post-phase robustness and prospective controlled-TWAP contrast (2026-11-21)

- The prior 2101/2102 four-tape retrospective review now includes strict
  nonfinite/type checks, a per-seed signed correlation phase contrast,
  changed eligible-bin count, and a **threshold-free abstention gate**.
  One of four original synthetic runs actually **reverses rho sign**
  although all six two-seed phase medians remain negative. All four
  simulations change eligible-bin counts across origins. Four matching
  runs may also share seed-level randomness across backgrounds; do
  not call them statistically independent market samples.
- Previous `public_sha256` provenance hashes only *executed print
  records*, so old aggregate-only artifacts **do not prove equality
  of entire L2 book contents**. New strict domain-separated
  `public_tape_fingerprint.py` adds exact hashes of quote timestamps,
  ordered same-time snapshots, unique price/size levels, public prints
  and side labels; a source-normalized phase shift must preserve
  the combined SHA. No exchange-provider authenticity claim.
- Pure review `abides_l2_phase_review.py` and
  `abides_l2_phase_fragility.py` produce descriptive JSON and keep
  `scientific_stage2_release_allowed=false`, irrespective of
  observed rho. No raw private agent IDs or account data exported.
- Newly reserved development seeds `2401/2402` (13 canonical ledger
  records / 33 locally known seed values / 6 constant checks) specify
  one *controlled TWAP* against background-only ABIDES conditions, two
  runs each, with three analytical origins each. Tests reject missing
  case matrices, content drift, misreported controlled fills and
  posthoc truth leak claims. Study protocol:
  [ABIDES_L2_TWAP_PHASE_CONTRAST.md](ABIDES_L2_TWAP_PHASE_CONTRAST.md).
  Until genuine matching-engine CI is checked, no empirical result
  for the injected-TWAP study is asserted.
- Live trading, physical bot identification, independent source
  completeness and real-market phase false-alarm estimates remain
  **CLOSED / UNKNOWN**, not silently inferred.

## Executed controlled public L2 TWAP contrast and phase-choice diagnostic (2026-11-21)

- [ABIDES CI #44915375635](https://github.com/IskanderAbdullin/Analytics/actions/runs/44915375635)
  succeeded on the **source-preregistered** 2401/2402 development seed
  cohort: 4 actual matching-engine market simulations and 12 dependent
  public phase-origin views; true controlled TWAP execution participation
  was verified *after* public feature computation (22 printed fills on
  each injected-TWAP original market).
- The two-seed median descriptive rho for **background only** at
  0/10/20s was **−0.2262/−0.0613/−0.4756**; with **injected TWAP**
  **−0.0711/+0.000058/+0.1004**. Exactly **2 of 4** original runs change
  rho sign across fixed phases, and eligible book/trade bin counts
  change across phases for all 4 originals. The raw event tape was
  NOT committed; complete aggregate-only original SHA-256 is
  `2391c9f223b6841f8346502282b7e099856e6feee7726cd4769967dcbcd97fa8`.
- Deterministic, source-only `abides_l2_twap_separability.py` reveals
  the **post-hoc phase-choice trap**: apparent strict ordering
  (injected rho range entirely above background range) is **false
  at 0s**, **true at 10/20s**, but **false across all origins**.
  It explicitly does not select a threshold, use statistical
  classification accuracy, or open the scientific or trading gates.
  A matching new CLI can reprocess saved full JSON or the 12-row
  committed scalar fixture without ABIDES.
- The old L2 experiment used a print-only SHA; this new study checks
  **combined exact ordered public L2 plus public trade SHA** across
  every phase before retaining case summaries. That prevents silent
  L2-content drift within a simulated source but cannot authenticate
  independent real provider archives.
- Expensive source-controlled ABIDES workflow changed to **manual
  dispatch only after the successful original run**; the cheap
  research-ledger workflow tests the source, retrospective case
  fixture, non-identifiability and all provenance gates. Seeds
  2401/2402 are now **spent**, and no real market owner-count claim
  or out-of-sample significance is supported.

## Aggregate-only privacy hardening

The public-phase aggregate serializers for the original background study
and new controlled-TWAP experiment now reject **every unrecognized row
field**, in addition to enforcing numeric exactness, frozen row matrices
and source hash consistency. Synthetic tests inject
`passive_agent_id`, `controlled_agent_ids`, `hidden_order_id`,
`private_event_manifest` and raw book fields and verify they cannot
be persisted in aggregate-only CI artifacts. This closes a leakage
path where future developer code could have appended extra private
keys to otherwise valid public summaries. All source-private analysis
remains detached from the published public case schema.

## 2026-11-21 — new real execution archives, two independent UTC sessions

[Official Binance Vision raw spot trade download #44916791033](https://github.com/IskanderAbdullin/Analytics/actions/runs/44916791033)
successfully verified **116,446 real LTCUSDT public prints** for
**2026-11-18 UTC**, SHA-256
`2fbf1fe2f85c813b3d5e4922d674799adced6f306effe0e5cf9add62a57e6522`.
The second precommitted [run #44917086043](https://github.com/IskanderAbdullin/Analytics/actions/runs/44917086043)
verified **161,957 public prints** for **2026-11-19 UTC**,
SHA-256
`9208231cbd6b55e4de42d04d9c07aa636be235be6d1c08ddb3c6953dbc6f3c1a`.
The first day is inspected development evidence, second day is a
previously unseen *source/timing descriptive* day, not a blind
evaluation of an unchanged bot classifier.

Observed trade IDs contiguous inside and between dates:
**608186258–608464660**, **278,403** exchange public executions.
No missing IDs inside the downloaded intervals, no external guarantee
that this is every matching-engine execution. Total observed aggressive
buy/sell counts: **131,444 / 146,959**.

The second day was rebinned at **0/10/20s** for one fixed 30s
window, strict UTC-edge exclusion and preservation of all source
trade counts. Buy/sell-dominant bin memberships and one-sided
count change with the origin. **These are three analytic views of
one real source day, not independent market samples.** No real L2
book was sourced. A strict separate offline fixture pair validator
and synthetic negative tests were added; the original new-data
workflow is now manual-only, with the cheap research-ledger CI
guarding all source metadata and within-day conservation.

Source-license gate: Binance Vision dataset **CC BY-NC-SA 4.0**
non-commercial research only, with separate restrictions on live
proprietary trading, data redistribution and commercial use.
MOEX non-display feeds for algorithmic trading require a separate
contract; no such automated MOEX use is claimed. No raw public trade
ZIP, private IDs, credentials or large artifacts were committed.
