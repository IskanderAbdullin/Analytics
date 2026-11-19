# Observable high-activity windows — a simpler alternative to robot counting

**Implementation:** `src/RobotDetector.Core/FlowActivityEpisodes.cs`, standalone read-only .NET 10. **Status:** experimental and *not statistically calibrated*. Date: 2026-11-19.

## Why this path?

The original trade-period screens fit history but did not demonstrate out-of-sample predictive benefit; a strict 2-period age gate left only 2/167 future forecasts on fresh data. Variable-size cadence can still confuse synchronized public prints and missed dense windows. The independent [FlowFootprint](TRADE_FLOW_FOOTPRINT.md) baseline passed 56 offline tests and processed 121,920 real SBER prints into 203 source/5-minute windows without dropping prints, so it provides an easier-to-verify basis for detecting *observable activity*, without pretending to know owner identities.

## Explicit, predeclared rules

For each `InstrumentUid + TradeSource + TradingMode + SessionId`:

1. Generate 5-minute UTC footprint windows containing actual public prints, signed reported volume, lot count and direction.
2. For each window, only compare against **four immediately preceding contiguous populated windows** of exactly the same source/mode/session. Missing time windows reset the reference; do not fabricate zero-volume auction/closed periods.
3. The **historical reference** is the median number of prints and median total lots in those four older windows. Neither the current window nor any later print can modify its baseline.
4. Label a window `unvalidated_observed_activity` only if all the predeclared conditions hold: at least 10 prints, count >=3× reference median, lots >=3× reference median, and absolute provider-reported volume imbalance >=0.6.
5. Label the dominant direction `reported_buy_dominant_high_activity` or `reported_sell_dominant_high_activity`, explicitly not inferred aggressive/passive side.
6. Report the original source SHA, number of evaluated windows, warmup/gap windows and each flagged window with baseline medians and ratios. No owner IDs, calibrated confidence or predicted future price.

These thresholds are **heuristic research defaults**, not optimal or fitted market parameters. They must be evaluated on truly independent days with source-aware and trading-session-aware controls.

## Example

Synthetic fixture `fixtures/synthetic_activity_episode.csv`: four consecutive 5-minute periods with five small prints (50 lots total in each), followed by 20 BUY-reported prints of 100 lots each in the fifth. The historical medians are **5 prints and 50 lots**, the new print-count ratio is **4×**, lot ratio **40×**, and provider-reported side imbalance is **1.0**. Exactly one observable high-activity window should be flagged.

```powershell
dotnet run --project src/RobotDetector.Cli -- activity-episodes \
  --input fixtures/synthetic_activity_episode.csv \
  --reference-windows 4 --min-prints 10 \
  --min-count-ratio 3 --min-lot-ratio 3 \
  --min-abs-imbalance 0.6 \
  --output data/results/observed-activity.json
```

For real public archives, also inspect `flow-footprint` with the **same** window width; remember that aggregating across trading regimes or losing book depth invalidates many microstructure conclusions.

## Controls and false-positive hazards

- A high-volume balanced BUY/SELL window must **not** be flagged under the direction-dominance rule.
- An EXCHANGE baseline must never be borrowed by a DEALER or another instrument/session/mode.
- A gap (including missing source windows) requires new warmup; do not treat absent prints as zeros.
- Modifying only prints after the flagged window must not revise its earlier baseline or label.
- A public news release, an auction, a marketwide synchronized burst, multiple unrelated participants, or incorrect source `DIRECTION` semantics may produce exactly the same signature.
- Do not interpret a flagged window as a unique robot, institutional order, manipulation, confirmed edge or an actionable trading signal.

References: [Lillo et al. on order-splitting and long memory](https://doi.org/10.1103/PhysRevE.71.066122), [Muravyev et al. on market-wide clock clustering](https://doi.org/10.1111/fima.12405), [independent orderflow-metrics open-source examples](https://github.com/twowaymind/orderflow-metrics).

## Next gates

1. Compile all three .NET projects, run existing and new offline tests, CLI goldens. No trade API calls.
2. Execute a read-only empirical smoke on one public MOEX/SBER archive with predefined settings, retain only aggregate flagged-window counts and hash; use the same data only as an engineering test, never independent prediction validation.
3. Compare this simple detector with existing fixed-q/variable-q cadence on **independent** dates with a common-clock/null and no data-driven threshold adjustment.
4. Only after statistically robust, prospective, cross-instrument validation may any activity label be considered for optional live alerts; physical bot count remains unidentifiable from these prints.
