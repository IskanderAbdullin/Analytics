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

