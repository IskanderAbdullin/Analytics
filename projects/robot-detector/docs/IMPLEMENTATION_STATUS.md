# Implementation status — Market Robot Detector

Date: 2026-11-18. Branch: `main`. Milestone: experimental `0.1`.

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

**GitHub Actions compilation and offline regression SUCCEEDED on 2026-11-18.** Confirmed run: https://github.com/IskanderAbdullin/Analytics/actions/runs/44276050349 — build of Core, CLI and SelfTests: success; 18/18 offline self-tests: success; CLI golden fixture: success; read-only order API sentinel: success. The separate existing IPO CI also succeeded in PR #2. The available local execution container itself lacks `dotnet`; GitHub hosted runner provided the verified build. This is **not** a live-market accuracy validation.

Real public T-Invest archive `SBER_TQBR` for `2026-11-17` was downloaded and parsed via an isolated GitHub Actions runner: **121,920 prints, zero invalid records**. The fixed-volume screen found **209 preliminary candidate episodes**, not 209 verified bots. Data SHA-256 `0af872b1c9c861e7af40a1c40e5bbdf565f9161dd997337c08da584c4dafc782`; log https://github.com/IskanderAbdullin/Analytics/actions/runs/44278450117 . The GZip format and TLS additional Russian Trusted Root CA were verified. Completeness, side semantics, and actual bot identity are still unknown. No live gRPC T-Invest stream connection has been tested or implemented.

## What's done versus remaining stage gates

- **Stage 1, partial:** data contract, ZIP/CSV import, T-Invest public one-day downloader, explainable fixed-volume candidate detector, windowed processing, independent UTC FFT peaks, synthetic golden fixture, CLI. **Remaining:** validate more instruments/days, reconcile candidates across event-count chunks, robust burst assembly, exchange session calendars, full performance metrics and quality stats, more sophisticated candidate fusion.
- **Stage 2, initial:** synthetic injected/null trials with hidden IDs, reproducibility regressions, one-step chronological matching. **Remaining:** ABIDES-NG controlled truth, realistic Hawkes/common-clock null, statistical multiple-testing corrections, held-out calibration, quantitative research report, blind parameters.
- **Stage 3, not yet operational:** no actual `MarketDataStream` subscription, no persistent live state, no UI/service. Historical endpoint is **not** a substitute for real-time book/trade streaming.
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

1. **DONE (initial build):** GitHub Actions compiled all .NET projects and passed 18 self-tests. Continue adding CI as code grows.
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
