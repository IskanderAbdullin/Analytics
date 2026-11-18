# Stage 2 — forecast failure forensics (post-hoc, read-only)

**Created:** 2026-11-18. **Implementation:** `src/RobotDetector.Core/ForecastFailureDiagnostics.cs`. No automated trading; no actual parent-order or individual participant identity information is available. **This module is deliberately forbidden from tuning the forecast on an already evaluated held-out date.**

## Motivation

The read-only SBER rolling prediction pilot on **2026-11-12 and 2026-11-13** produced **14/983** hits at the predicted time, exactly **14/983** hits at a half-period-shifted placebo. Historical periodicity screening did not translate into reliable next-print prediction. [Original, frozen findings](ROLLING_REAL_PILOT.md). These two dates must remain sealed: **do not choose new thresholds, change the detector or claim improvement based on their outcomes**.

Failure hypotheses include:
- No recent candidate evidence, i.e. a historical series stopped long before the scoring cutoff;
- A public print of the expected q/side occurred near the forecast target but outside the strict time tolerance (observed time shift);
- A print with different q but matching source/side occurred at the expected time (possible changed child size/partial fills);
- A print in the opposite reported side occurred at the expected time;
- No comparable print was present around the target, or the available tape did not cover the whole wider diagnostic window.

These are **non-exclusive observational clues, not proven mechanisms**. Public matched trades lack the identity needed to attribute one specific print to a specific parent order, algorithm, or owner.

## Implementation and scope

- `WalkForward.ForecastCheck` now includes immutable **LastTrainingEvidenceUtc** and **TrainingMatchedCount**, which are computed only from the actual prefix of prints at or before the cutoff.
- `RollingForecastObservation` carries the original **TradingMode**, historical evidence timestamp/count, and predicted target with the unchanged observed hit/placebo data. No new trading signal is introduced.
- `ForecastFailureDiagnostics.Analyse(source, rollingReport, DetectorConfig)` validates SHA compatibility, forecast counts, historical provenance (last evidence must precede cutoff), and strictly matching venue/source/mode/session for all later-print comparisons.
- Three historical candidate-age buckets are **predeclared**: `fresh_0_2_cycles`, `age_2_8_cycles`, `stale_over_8_cycles`. A bucket's hit counts are descriptive only. The age itself is known before the outcome and is not computed from future prints.
- For misses, the original exact matching tolerance is `max(minTolerance, min(maxTolerance, period * relativeTolerance))`. Widened **diagnostic-only** window is `max(exact+1ms, 250ms, min(10000ms, 0.25*period))`; it is not a new prediction window and must never be used to improve a held-out hit count.
- Count separately whether same-q/side prints are near but outside exact tolerance; alternative size is at exact target or nearby; or opposite reported side prints are at target. Flags can overlap. Nearest-window coverage must extend past the wider window before absence is reported. Every scan is restricted to same instrument, trade source, mode and session.
- For round-second market-wide synchronization, report count of forecast target timestamps within the first 100ms of a whole UTC second and their observed hits. This is a preliminary common-clock diagnostic, not a robust exchange-level null.

## Command

From `projects/robot-detector/`:

```powershell
dotnet run --project src/RobotDetector.Cli -- diagnose-forecast \
 --input data/raw/sber.csv \
 --min-matches 6 --warmup-minutes 60 --stride-minutes 30 \
 --max-cutoffs 12 --output data/results/failure-diagnostics.json
```

Report: JSON counts only. No participant IDs, individual market prints or market orders are emitted by the GitHub workflow.

## Synthetic regression matrix

1. Exact, stable 5-minute series: no misses, all historical age buckets reconcile to the number of forecasts;
2. Next execution changes q=100 to q=200: same-time different-size observation is recorded, but **not** a new bot identity;
3. Next print delayed by 5 seconds: same size near but outside the 200ms scoring tolerance, not counted as a successful forecast;
4. Candidate last observed more than 8 cycles earlier: stale-history diagnostic;
5. DEALER print at expected EXCHANGE target: MUST NOT be treated as positive match or as evidence of size/time drift;
6. Source hash mismatch or supposedly historical evidence timestamped after cutoff: MUST fail closed.

## Development data study (predeclared before running)

Use **SBER 2026-11-09 and 2026-11-10** as exploratory diagnostic/development days; these are distinct from the sealed November 12/13 validation sessions. Freeze settings to the previously reported `minMatches=6, warmupMinutes=60, strideMinutes=30, maxCutoffs=12`; keep source SHA, per-date print count and aggregate diagnostic flags. Do **not** publish original user data/market tape; use the process-scoped pinned Russian Trusted Root CA already validated in previous CI runs.

Never describe the output as calibrated probability or exact cause. Selecting a candidate feature based on these exploratory diagnostics must require an additional untouched forward test on new instrument/dates. Per-source feed completeness and auction/halts remain unverified.

## Stage gate

Even if a large fraction of misses shows changed size or stale history, **do not** rewrite the original held-out 12/13 November results. They remain 14/983 against 14/983 placebo (no detected advantage).

Next legitimate research step: design new candidate-lifecycle/trade-burst models using the development sample; compare against well-defined nulls and ABIDES known-agent truth; freeze parameters and validate on untouched data. No online trade signals may be released without those gates.

## Measured development results — 2026-11-18

[GitHub Actions run 44303630656](https://github.com/IskanderAbdullin/Analytics/actions/runs/44303630656): all steps passed, **38/38** .NET offline tests. Real data archives were discarded after processing.

| Metric | 2026-11-09 | 2026-11-10 | Combined |
|---|---:|---:|---:|
| Future forecast windows | 187 | 119 | **306** |
| Predicted exact hits | 4 | 5 | **9** |
| Phase-shift placebo hits | 3 | 5 | **8** |
| Misses | 183 | 114 | **297** |
| Misses where last evidence was >8 periods old | 182 | 109 | **291** |
| Forecasts based on >8-period-old history | 184 | 109 | **293** |
| Misses with same-q outside strict timing tolerance | 20 | 27 | 47 |
| Misses with alternative q inside strict tolerance | 7 | 13 | 20 |
| Misses with alternative q within wider nearby window | 60 | 58 | 118 |
| Misses with opposite side at exact target | 7 | 16 | 23 |
| Misses with no same-side print in wider window | 52 | 3 | 55 |
| Misses with incomplete nearby audit window | 68 | 50 | 118 |

**Historical age bucket counts:**

| Bucket | Forecast windows | Exact hits | Placebo hits |
|---|---:|---:|---:|
| Fresh (<=2 periods old) | 9 | 6 | 3 |
| Aging (2–8 periods old) | 4 | 1 | 0 |
| Stale (>8 periods old) | 293 | 2 | 5 |

SHA-256 of compressed public archives:
- 2026-11-09: `8e4ea994b10a0398f2cd08fe80ba67ecf082c14edc062ac154507fb769cd5a8a`
- 2026-11-10: `95b62c78e2fee6a310426ecd1a42732c19a019d7ba77d5c4cf4fc1415a32befd`

**Interpretation:** 291/297 observed misses (98.0%) occurred for candidates whose last supporting print was over eight predicted cycles old. This suggests candidate *staleness* is a major practical deficiency. Fresh-bucket hit rate (6/9) looks much higher but comprises **only nine forecasts**, was observed on development data, and cannot be cited as independent evidence of a real predictive edge. Even apparent exact hits do not prove participant continuity.

Other diagnostic flags are **not mutually exclusive** and apply to different audit window completeness subsets; summing them into a cause distribution is invalid. The full live exchange feed and order identity are not available. For 118 misses the broad nearby audit window could not be fully observed within the same source/session sequence; this is not a declaration of missing exchange prints.

**Next predeclared development-driven change:** create an optional `maxTrainingAgeCycles=2` *historical-evidence recency gate*. It must filter candidate forecasts **before accessing future print outcomes**, keep the original unrestricted baseline unchanged, and be compared on a fresh untouched pair of SBER dates (proposed 2026-11-05/06) with the same 60-minute warmup, 30-minute stride, 12 cutoffs and T/2 phase-shift placebo. A gate may dramatically reduce the sample size; report the absolute number of eligible forecasts as well as rates. Do not retune threshold on those two dates, and do not reinterpret the old sealed 12/13 November replay.
