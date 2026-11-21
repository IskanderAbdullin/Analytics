# Stage 2 — Common-clock adversarial negative control

**Scope:** `projects/robot-detector/`. Added 2026-11-21. This deliberately hostile synthetic test asks whether the existing fixed-q and variable-q screens can attribute **independently generated public prints** to a periodic controlled execution program merely because their public timestamps, lot sizes and reported side share a common scheduler.

## Threat model and hidden truth

`MarketClockNullStress.Generate(seed, backgroundPrints, cycles, periodMilliseconds)` emits anonymous, deterministically SHA-identified `MarketTrade` records. Their public timestamps sit near a shared periodic clock grid, with reported SELL side and a global clip-size schedule. The default `--clip-mode fixed` gives all prints 100 lots; `--clip-mode variable` cycles public quantities 25/50/75/100 lots by clock slot. Neither mode has repeated controlled execution producers. Crucially, **each print is given a different private background producer label** and there are **zero controlled execution agents**. These labels are never supplied to either detector; they are retained solely for scoring by the existing `BlindExecutionBenchmark.Evaluate` path.

This is a worst-case test for over-interpreting a rhythmic *market-wide event* as an identified execution program. It does not claim that real print-level independence is observable or that this model is statistically representative of an exchange.

## Usage

From `projects/robot-detector/`:

```powershell
dotnet run --project src/RobotDetector.Cli -- benchmark-clock-null `
  --trials 20 --background-prints 120 --cycles 12 --period-ms 5000 `
  --output data/results/clock-null.json
```

Use `--clip-mode variable` to run the same zero-controlled-truth challenge against models that require variable-size evidence. Fixed and variable runs use disjoint opaque ID domains and keep private producer labels separate.

Without `--output`, the command prints JSON; with `--output`, it requires a new file path to avoid overwriting prior evidence. It never contacts brokers, downloads archives, reads accounts or places orders.

## Interpretation

Every case has `InjectedExecutionPrints=0`, `TrueSyntheticProducerCount=0`. For each detector, `TruePositivePrints=0`, all attributed prints count as false positives relative to *controlled* generator truth, and `EventRecall=null` because the positive denominator is zero.

`Models[].TrialFalseAlarmFraction` is the number of stress cases with at least one attributed public print divided by the number of generated stress cases. This number is purely **descriptive** for the chosen deterministic generator and seed range. It is **not** a calibrated probability of false discovery on MOEX/SPB, not a frequentist p-value, not a posterior probability of a physical robot, and not a trading recommendation. High false-alarm counts expose a weakness of the screen under an adverse common-clock confounder; zero counts on a finite toy run prove nothing about market specificity.

For any model, exactly conserve counts: the sum of `FalsePositivePrints` across cases equals `Models[].FalsePositivePublicPrints`; `FalseAlarmTrials` counts only cases whose detector attributed one or more events. Both screens receive the **same** public prints, and unique print IDs prevent accidental double counting in the scoring path.

## Checks and release gates

Four additional deterministic no-NuGet self-tests check: independent private producers and opaque IDs; zero controlled truth, false-positive conservation and undefined recall; summary arithmetic, reproducibility and fail-closed input bounds. The Windows convenience `RobotDetector.DotnetTests` wrapper executes the entire console self-test battery through `dotnet test`; this optional local wrapper is not required by upstream's no-NuGet CI.

**Executed stress smoke (2026-11-21):** 3 deterministic seeds per background profile, 60 independent public prints in each case, zero controlled parent executions. [Successful .NET CI run, 120/120 internal checks](https://github.com/IskanderAbdullin/Analytics/actions/runs/44888523166).

| Adversarial background | Detector | Cases with false attributions | Falsely attributed prints / total in cases |
|---|---|---:|---:|
| Shared clock, fixed 100-lot prints | Fixed-quantity | 3/3 | **81/180** |
| Shared clock, fixed 100-lot prints | Variable-quantity | 0/3 | 0/180 |
| Shared clock, cycling 25/50/75/100 lots | Fixed-quantity | 0/3 | 0/180 |
| Shared clock, cycling 25/50/75/100 lots | Variable-quantity | 3/3 | **81/180** |

The same three public cases are evaluated by both models in each profile; detector scores should not be summed as independent market observations. These 81 false attributions are a controlled *counterexample* to identifying a physical robot from a periodic anonymous tape, not a calibrated MOEX/SPB real-world false-positive rate, and do not establish a causal exchange mechanism. Neither null profile produces any controlled synthetic execution program.

Current research status: `Stage 2 scientific release gate CLOSED`. This experiment is neither ABIDES-NG with hidden agent truth and queue matching nor empirically calibrated clustered-null validation. Before any real-market claims: hold out entire dates/instruments, run multiple competing conditional null families through the full candidate-selection pipeline, check source clock precision/market session coverage, and evaluate forecast ability against prespecified placebo.

Tracking issue: [#27](https://github.com/IskanderAbdullin/Analytics/issues/27).
