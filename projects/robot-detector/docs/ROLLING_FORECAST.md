# Stage 2: prospective rolling evaluation with a phase-shift placebo

**Status:** experimental .NET implementation in `src/RobotDetector.Core/RollingForecast.cs`, subject to CI and real-data validation. This **does not** estimate the physical number of bots or the probability that an episode is a bot.

## Goal

A detector that finds repeating patterns in already observed history can overfit. A more meaningful test is to freeze a hypothesis at cutoff time, publish the next expected time window, and count only events observed **after** that cutoff. Repeating this across predeclared cutoffs creates a prospective series.

## Method

1. Partition public trade prints by `InstrumentUid + TradeSource + TradingMode + SessionId`. Never mix EXCHANGE/DEALER or distinct sessions.
2. From the first print in each partition, create cutoffs after `warmupMinutes=20`, then every `strideMinutes=15`, up to 24 cutoffs (all defaults, no manual tuning per file).
3. Call existing `WalkForward.Evaluate`, whose detector sees only prints `timestamp <= cutoff` and issues at most one next-slot window per candidate pattern. Events after cutoff are inaccessible to model fitting.
4. Ignore forecasts if an equivalent time slot for the same source/side/q/period was previously checked; prevent the same future print from confirming several sequential cutoffs.
5. Construct a **placebo forecast** for every emitted candidate by shifting its predeclared target time by `T/2`, with the same interval tolerance and side/size/source requirements. This placebo is a simple reference for background coincidences, **not** a valid exchange null significance test.
6. Count a forecast only when both the original target window and the placebo window are fully inside the observed future file. Do not report unobservable future intervals as missed predictions.
7. Output `ObservedHits`, `PlaceboHits`, `ObservedHitRate`, `PlaceboHitRate` plus individual cutoff/target/evidence IDs and the uncalibrated/source-incomplete warnings.
8. Physical bot count remains unknown; `Calibrated=false`. A correctly predicted trade need not belong to the same trader as earlier prints.

## Synthetic example

13 artificial EXCHANGE SELL prints of 100 lots every 5 minutes from 07:00 to 08:00 UTC, one trading session. A 20-minute warmup and 10-minute stride gives four cutoffs: 07:20, 07:30, 07:40, 07:50. The expected print windows are about 5 minutes later; placebo windows are 2.5 minutes after these predictions, where synthetic prints were not generated. This provides a no-future-leakage unit + CLI regression, **not** a production accuracy estimate.

Run from `projects/robot-detector/`:

```powershell
dotnet run --project src/RobotDetector.Cli -- rolling-forecast \
  --input fixtures/synthetic_long_cadence_5min.csv \
  --min-matches 4 --warmup-minutes 20 --stride-minutes 10 \
  --max-cutoffs 4 --output data/results/rolling.json
```

## Interpretation cautions

- The simple `T/2` placebo may accidentally intersect a second algorithm or rhythmic market-wide activity. It is not an FDR correction and is not statistically independent of the primary forecast.
- Many cutoffs and candidate periods cause multiple-comparison bias. High hit rates in one historical session do not establish stable predictive power out of sample.
- The current underlying `WalkForward` assumes exact `QuantityLots` and matches one print per candidate; it does not yet handle variable clip sizes, parent orders, full L2 book or venue matching mechanics.
- Trading halts, missing prints and source gaps can make apparent misses unverifiable. The source `HasVerifiedFeedCoverage` flag is false for a successfully parsed isolated public archive unless separately proven.
- Global events can have similar periodicity in many stocks, especially round-second/round-minute effects; later nulls should preserve these rhythms.
- The synthetic test's clean hits do not demonstrate MOEX/SPB live predictive performance.

## Next pilot and acceptance

After offline CI passes, reuse a read-only one-day public T-Invest archive, choose cutoffs via fixed config **before looking at outcomes**, publish the aggregate `forecast count/hits/placebo hits` and source SHA. Include one other trading date and inspect whether the observed hit rate is consistently higher than the placebo without assuming independent forecasts.

Do not publish a confirmed pattern flag or calibrated next-print probability based solely on this comparator. Full Stage 2 requires stronger null distributions, controlled ABIDES truth, reliability calibration and held-out date/instrument validation.

[Stage 2 design](STAGE_02_VALIDATION.md) · [SBER dual-null pilot](MULTIDAY_NULL_PROTOCOL.md).
