# Simple observable trade-flow footprints — independent baseline

**Version:** experimental 0.1, 2026-11-19. **Status:** standalone, read-only .NET 10 implementation. This is a deliberately simpler parallel research method than detecting specific timed robots.

## Purpose and scientific honesty

The earlier fixed-size algorithm produced **14/983** historically replayed future matches versus **14/983** at half-period placebo; a development-derived 2-cycle recency restriction left **2/167** proposed forecasts on untouched days. The variable-size candidate detector showed day sensitivity and needed dense-group handling. These observations justify an alternative, more directly observable baseline.

**A footprint measures aggregate anonymous trades, not a trading program, trader, metaorder or number of bots.** Do not infer maker/aggressor side from reported exchange direction without a verified source-specific rule. The report always contains `actualBotCountKnown=false`, `statisticalSignificanceEstablished=false`.

## What this module computes

`src/RobotDetector.Core/FlowFootprint.cs` groups original public prints by **InstrumentUid + TradeSource + TradingMode + SessionId + UTC 5-minute bucket** (5 min configurable). No case labels or hidden owners are used.

Each JSON window includes:

| Feature | Definition | Important limitation |
|---|---|---|
| Count and total lots | Number of actual prints and `sum(QuantityLots)` | One parent order can generate several prints |
| Reported BUY / SELL / UNKNOWN volume | Sum quantities separately | Provider DIRECTION is not a verified passive side |
| Signed volume imbalance | `(BUY lots - SELL lots)/(BUY lots+SELL lots)`, or null when absent | **Not Cont-Kukanov-Stoikov order-flow imbalance**: only public prints are available |
| Longest BUY and SELL sequences | Maximum contiguous run in timestamp + arrival ordering | Different participant prints can form a long run |
| Lag-1 sign agreement | Number of adjacent known-direction pairs with equal sign / all adjacent known-direction pairs | UNKNOWN breaks continuity; this is not trader persistence |
| Median trade interarrival | Middle timestamp difference in ms | Duplicate timestamps/partial fills and feed gaps matter |
| Interarrival CV | Std dev of interarrival time / mean (population definition) | Zero interarrival and market bursts are common |
| Count Fano factor | Population variance / mean of count-per-bin in 1-second bins between the **first and last observed print**; zero bins inside included | Not a calibrated Poisson/Hawkes test; sensitive to bin width |
| Near-integer-second phase | Fraction of prints whose millisecond timestamp is in [0, 100) | Exchange-wide clock periodicity is well documented; **not** bots |

For the Fano factor, the code avoids materializing potentially millions of empty bins by using the exact identity `sum(count^2)/totalPrints - totalPrints/binCount`, where `binCount` covers first-to-last observed bins inclusively. If there is only one bin, Fano is null. File SHA and coverage flag are preserved. No absent minutes before the first print or after the last print are invented.

**No classification, anomaly alert, high/low quality prediction or profitability score** is emitted. This makes the baseline useful even when none of the period-finding detectors is reliable.

## Usage

From `projects/robot-detector/`:

```powershell
dotnet run --project src/RobotDetector.Cli -- flow-footprint \
  --input fixtures/synthetic_variable_clip_5s.csv \
  --window-minutes 5 --bin-seconds 1 \
  --output data/results/flow-footprints.json
```

Synthetic fixture expectations: 12 same-side public-like prints, total **300** lots, 12 consecutive reported SELL signs, exact **5,000 ms** interarrival median. Every timestamp falls on a whole-second boundary. All interpreted only as descriptive evidence.

## References and other open approaches

- Muravyev et al., [Does trade clustering reduce trading costs?](https://doi.org/10.1111/fima.12405) — clock-wide second periodicity demonstrates why naive "one-second bots" are unreliable.
- [Periodicity of trading activity in FX markets](https://doi.org/10.1111/jfir.12280) — many instruments show begin-minute clustering.
- Lillo/Mike/Farmer, [Long memory in supply and demand](https://doi.org/10.1103/PhysRevE.71.066122) — signed order-flow persistence may reflect metaorder splitting, but owner IDs aren't observable in these prints.
- Cont/Kukanov/Stoikov, [Price Impact of Order Book Events](https://arxiv.org/abs/1011.6402) — L2/L3 **OFI** is not equivalent to our trade-print imbalance.
- [twowaymind/orderflow-metrics](https://github.com/twowaymind/orderflow-metrics) — independent open-source feature examples; no direct dependency.
- [cyrustang147/Microstructure-Bars](https://github.com/cyrustang147/Microstructure-Bars) — time/volume bar construction and autocorrelation reference.
- [Tworasos/tape-and-book](https://github.com/Tworasos/tape-and-book) — explicit signal test loop on public data, useful research philosophy.

## Testing and next comparative experiment

- Add synthetic cases for equal 1s spacing (Fano=0), clustered prints with internal empty bins (Fano>2), missing side, source and UTC-window partition, invalid configuration.
- Compile and run full standalone .NET self-tests and CLI smoke. Existing IPO project remains unaffected.
- Run **one fresh public trade archive** through `flow-footprint`, log only aggregate coverage and hash. No on-chain or private trading data.
- Implement a second *simple* O(N) activity-episode detector on the footprint windows, using a reference baseline and no "bot count", only if independent descriptive statistics remain correct.
- Any later forecast variant must be assessed on strictly future data with strong conditional nulls. **The known failed fixed-q forecasting results remain unchanged.**

This is an independently testable baseline, not a retroactive repair of earlier unsuccessful candidate algorithms.
