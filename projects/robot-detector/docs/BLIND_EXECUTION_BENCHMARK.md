# Stage 2 — Truth-blinded synthetic execution benchmark

**Authoring:** 2026-11-19. **Purpose:** evaluate event-level attribution of publicly observable trade-print patterns against **private synthetic generator labels**. This is an independent, falsifiable test of the FIXED and VARIABLE cadence screens, **not** calibrated market accuracy and never an estimate of actual MOEX/SPB robot identities.

## Why a new blind benchmark

Existing historical SBER testing showed no independent advantage of predicted exact-q future prints over a T/2-shift placebo on Nov 12/13 (14 out of 983 checks in each case). Subsequent experimental features and clock-frequency artifacts demonstrate why apparent regularity is insufficient evidence of participant identity.

A properly evaluated detector must be asked to recover *synthetic* controlled-order events **from a public projection that hides all generator labels**. The detector cannot inspect `HiddenProducerByEventId` until predictions are complete; the bench scores each model's attributed public print IDs only afterward. Every public `EventId` is an opaque deterministic SHA-256 prefix, not a revealing `SYN-ROBOT-123` source label.

## Implemented research cases

`BlindExecutionBenchmark.Generate(BlindedMarketScenario)` produces a fully reproducible `TradeImportResult` and **separate** private assignment truth. The private truth is used **only** by the scoring code.

Four different seeded cases:

| Case | Controlled agent prints | Other prints | Why |
|---|---|---|---|
| `clustered_null` | 0 | Clustered background only | Tests false attribution on clocked bursts and vendor-like co-timed prints |
| `fixed_twap` | Twelve same-q 5-second SELL clips (default) | Independent background | Baseline for historical fixed-size periodic screen |
| `variable_twap` | Twelve periodic clips cycling q 25/50/75/100 | Independent background | Tests varied child size and where strict constant-q model can miss |
| `partial_fill_twap` | Two same-time public executions per one of 12 scheduled slices, total 100 lots per slice | Independent background | Tests what can be observed when one controlled execution appears as multiple prints |

Background is **not** a validated Hawkes process: it is a reproducible set of short bursts, varying clip sizes, mixed directions and some whole-second clock alignment, with one synthetic background producer assignment per print. Real exchange queue/fill physics, auction halts, anonymous cross-venue routing, conditional mark distributions and market impact are absent.

Two research detectors are evaluated without any source/label changes:

- `PeriodicDetector.Detect` from `RobotDetector.Core`, requires fixed-q evidence.
- `VariableSizeCadence.Detect`, allows varying clips, but requires distinct sizes, coverage, source/mode/session consistency.

Both see only the **exact same public tape**, not internal producer identities.

## Metrics — descriptive only

For each detector and scenario: accepted candidate sequence count; number of **unique** attributed public print IDs; true positive injected print IDs; false positive background print IDs; injected prints not attributed; event-level precision (TP/attributed if attributed>0 else `null`) and event-level recall (TP/injected prints if injected>0 else `null`). Do **not** invent zero recall for a pure-null scenario; its denominator does not exist.

These metrics are **synthetic known-truth recovery**, not out-of-sample market false-discovery probabilities or posterior confidence for real robot detection. A detector that identifies one synthetic producer's several prints cannot prove a real parent order on anonymous exchange history.

## Fundamental non-identifiability demonstration

`BlindExecutionBenchmark.RelabelSamePublicTape` keeps the *same exact public market data* and all `EventId` values unchanged, while attributing the controlled prints to **one** or **two** private synthetic producers. The data, and therefore **both detectors' outputs, are identical**, although the hidden number of controlled producers differs. This proves that **owner count is not generally identifiable from those public prints alone**. No better posterior confidence or cleaner UI can remove that information gap without additional verified features/assumptions.

All output explicitly includes `CanInferActualRealWorldRobotOwners=false`, `IsABidesExchangeSimulation=false`, `PhysicalProducerCountInferred=false` for each screen; there is no trade command.

## CLI

```powershell
# From projects/robot-detector/
dotnet run --project src/RobotDetector.Cli -- benchmark-blind `
  --seeds 5 --background-prints 120 `
  --output data/results/blinded-research.json
```

Only **aggregate** case results are serialized. No private producer map, identifiable real account, broker token or raw market tape is included.

## Required checks and further research

- Repeatability of seed/expected synthetic events, opaque public IDs, exact false-positive/true-positive conservation.
- Background-only null has undefined recall, not 0% or 100%.
- Fixed/variable test on clean historical-like case without noise; partial-fill case contains exactly 2 simultaneous prints per slice with conserved volume.
- Same public tape relabelled to 1/2 agents yields **identical detection reports** yet different hidden truth counts.
- Entire .NET CI and CLI benchmark smoke pass; write actual results only after CI.
- **Next:** replace this toy generator with independently calibrated richer ABIDES-NG controlled simulations, preserving hidden per-agent truth, actual exchange matching/queue physics, partial fills, liquidity replenishment, VWAP/POV varying cadence, and a true statistical train/holdout protocol. A mixture of known synthetic trials does not substitute for exchange-market validation.

Research examples, inspected from actual public source:

- [ABIDES-NG TWAP agent](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/twap_execution_agent.py) recomputes slice size as remaining quantity / remaining slices and redistributes earlier underfills.
- [ABIDES-NG POV agent](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/pov_execution_agent.py) targets a fraction of observed market volume.
- [ABIDES-NG VWAP agent](https://github.com/GabrieleDiCorato/abides-ng/blob/main/abides-markets/abides_markets/agents/vwap_execution_agent.py) uses an expected volume curve (e.g. U-shaped intraday).

Our tiny C# generator does **not** integrate or claim identical results to these Python agents; it is a set of deterministic unit tests for truth isolation and false claims.

**Status of real-bot identification:** not validated. Stage-2 scientific and forecasting release gates remain **CLOSED**.

## Executed reproducible smoke — 2026-11-19

**CI:** [Robot Detector .NET CI 44577833225](https://github.com/IskanderAbdullin/Analytics/actions/runs/44577833225). Verified **116/116** offline checks and all 8 benchmark cases (2 seeds for each scenario), using **35 clustered background prints** per case. Original IPO CI also passed. These are small unit-test cohorts, **not** independently calibrated statistical confidence intervals.

| Scenario (2 seeds) | Detector | Correctly attributed synthetic prints | Background false attributions | Missed injected synthetic prints |
|---|---|---:|---:|---:|
| Clustered null | Fixed-quantity | 0 | 0 | N/A (0 injected) |
| Clustered null | Variable-quantity | 0 | 0 | N/A (0 injected) |
| Fixed TWAP | Fixed-quantity | **24** | 0 | 0 |
| Fixed TWAP | Variable-quantity | 0 | 0 | 24 |
| Variable-clip TWAP | Fixed-quantity | 0 | 0 | 24 |
| Variable-clip TWAP | Variable-quantity | **24** | 0 | 0 |
| Two-print partial-fill TWAP | Fixed-quantity | 32 | 0 | 16 |
| Two-print partial-fill TWAP | Variable-quantity | 24 | 0 | 24 |

**What this shows:** the two methods have complementary strengths in this deliberately controlled case. The fixed-clip model entirely misses varying child clips; the variable-clip model entirely misses constant clip sizes, because it requires size diversity. Both lose evidence under simultaneous two-print partial fills. Therefore a simple one-model "bot counter" cannot cover even all four stylized generators.

**What this does NOT show:** zero real-market false discovery, high precision on MOEX/SPB, actual parent-order identification, proof that an execution was profitable, or live forecast accuracy. Two toy null seeds and simplified noise are too weak for calibrated market claims. The public-print non-identifiability test still makes the real-world physical owner count unknown even if event-level synthetic recovery were perfect.

Next scientific validation must use ABIDES-NG known-agent public projections, broader noise and queue/matching scenarios, predeclared null families and truly independent held-out market data before any live trading signal.
