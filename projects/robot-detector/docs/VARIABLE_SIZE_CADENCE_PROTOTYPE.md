# Stage 2 R&D: cadence without fixed per-trade size

**Implemented:** 2026-11-18. **Status:** research-only candidate generator; no calibrated confidence, no actual robot count, no validated forecast and no trading operations.

## Motivation

The fixed-size cadence detector and its strict prospective tests did **not** produce a demonstrable next-print advantage (14/983 matched future prints versus 14/983 half-period placebo on Nov 12/13). A subsequent history-only recency gate removed 165/167 forecasts in independent Nov 5/6 data (only 2 eligible, no hits). See [ROLLING_REAL_PILOT.md](ROLLING_REAL_PILOT.md) and [RECENCY_GATE_PILOT.md](RECENCY_GATE_PILOT.md).

A real parent order executed by TWAP/POV/VWAP may produce child clips of different sizes because of liquidity/underfills/queue and participation constraints. This is clear in the open-source [ABIDES-NG execution agents](https://github.com/GabrieleDiCorato/abides-ng/tree/main/abides-markets/abides_markets/agents); also see the [TWAP agent source](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/twap_execution_agent.py), [VWAP source](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/vwap_execution_agent.py) and [POV source](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/pov_execution_agent.py).

The papers and public source are design references; this module does **not** copy ABIDES models or infer privileged parent-order identifiers. Academic context: [Lillo, Mike & Farmer, Phys Rev E 71, 066122 (2005)](https://doi.org/10.1103/PhysRevE.71.066122) on long-memory from order splitting; [Sato & Kanazawa (2023)](https://arxiv.org/abs/2301.13505) on model-conditional aggregate order-splitting estimates. Neither establishes the identity or exact contemporaneous number of bot programs from public trade prints.

## Independent C# module

`src/RobotDetector.Core/VariableSizeCadence.cs` provides `VariableSizeCadence.Detect(TradeImportResult, VariableCadenceConfig)`.

Pre-declared experimental defaults (not chosen on test data):

| Control | Value |
|---|---:|
| Minimum matched prints | 8 |
| Distinct observed child sizes | 3 |
| Minimum observed period coverage | 70% |
| Candidate period range | 500 ms–300 s |
| Period search grid | 50 ms |
| Temporal matching tolerance | max(25 ms, min(250 ms, 1.5% of T)) |
| Largest allowed missing-cycle gap | 4 |
| UTC window duration | 60 min |
| Maximum prints per instrument/source/side/mode/session/chunk | 2,500; **split an oversized UTC window into disjoint chunks, report boundary effects** |
| Candidate period limit | 48 |
| Anchors per period | 40 |

The source is separated by instrument UID, EXCHANGE/DEALER source, reported direction, trading mode, session and UTC window; **quantities are deliberately not part of this grouping**. Candidate period proposals are generated from near-neighbour time deltas, optionally divided into missing-cycle multiples. Each candidate is checked against its own history; one original print cannot be attributed to multiple accepted candidates, and the resulting quantity diversity and observed lots are explicit evidence.

**Crucial:** regular prints across different sizes may come from completely different market participants responding to a common clock or orders; the module outputs `State="candidate"`, `ConfidenceCalibrated=null`, `OwnerKnown=false`, `PhysicalBotCountKnown=false`, `StatisticalSignificanceEstablished=false`. It does not predict future prints or establish profitable strategies.

Dense UTC windows are split into disjoint bounded **event-count chunks** instead of skipping the whole hour; `SplitDenseWindowCount` and `DENSE_WINDOW_SPLIT` expose the partitioning. A trailing chunk with fewer than `MinMatches` prints cannot generate a candidate and is reported by `SkippedTinyRemainderCount`/`TINY_CHUNK_NOT_EVALUATED`. A single hidden periodic program can be split into multiple observational episodes at the artificial boundaries. The old independent Nov 2/3 counts were measured with **version 0.1 (skipped dense windows)** and must not be compared numerically with new version 0.2 without adjustment.

## Time-dependent negative controls

`src/RobotDetector.Core/TemporalCadenceNull.cs` provides two **weak, illustrative controls**, both conditional on instrument/source/side/mode/session and minute-like UTC blocks:

1. **uniform:** uniformly resample timestamps within each minute while preserving number of prints, sizes, side, source, trading mode and minute-level intensity. Breaks real burst/cluster structure, so NOT a trustworthy full exchange null.
2. **rotate:** apply a shared randomly selected non-zero circular time shift to all prints inside one minute. Preserves their relative within-minute clock positions but changes minute-to-minute phase alignment and boundary placement.

The full variable-cadence detector is rerun on each seeded control. Aggregate `(1 + #nullCounts>=observed)/(B+1)` is only a **descriptive global count comparison**. It is not a calibrated p-value, FDR, accuracy, confidence or robot-count estimate.

## CLI

From `projects/robot-detector/`:

```powershell
dotnet run --project src/RobotDetector.Cli -- variable-cadence \
  --input fixtures/synthetic_variable_clip_5s.csv \
  --min-matches 8 --min-distinct-sizes 3 \
  --output data/results/variable.json

dotnet run --project src/RobotDetector.Cli -- variable-temporal-null \
  --input fixtures/synthetic_variable_clip_5s.csv \
  --mode uniform --trials 10 --output data/results/variable-null.json
```

The synthetic source contains 12 public-like EXCHANGE SELL prints at exact 5 s intervals, with q repeating 10/20/30/40 lots. Expected *synthetic* model: at least one 5000ms, 12-print candidate with 4 distinct quantities. Constant q must not trigger this **specific** variable-clip model.

## Tests and next gates

- Deterministic synthetic cadence, constant clip rejection, EXCHANGE/DEALER isolation, dense skip, timestamp control preservation, cyclic-shift structure and negative-control reproducibility.
- Independent research-only real-data access smoke on a **prespecified instrument/day** should report candidate counts and skip rates, not owner number or signal accuracy. If dense windows dominate, change algorithm design on a **separate development dataset**, not the test day.
- Proper Stage 2 validity needs common 1-second/60-second clock nulls, clustered/Hawkes-like background, partial-fill aggregation, controlled ABIDES known-agent labels and untouched instrument/date splits.
- A candidate generator that cannot demonstrate out-of-sample forecast or recoverable behavioural patterns **must remain disabled for live alerts**.

Existing successful and negative results remain unchanged; this is a new independent research hypothesis rather than a retroactive reinterpretation of previous held-out samples.
