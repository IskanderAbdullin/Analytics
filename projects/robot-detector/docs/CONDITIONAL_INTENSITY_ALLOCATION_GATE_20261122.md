# Prospective M0/M1/M2 allocation and falsification gate — 2026-11-22

Status: **DESIGN ONLY; NO INDEPENDENT SOURCE ALLOCATED OR EVALUATED**.
This is an extension of CONDITIONAL_INTENSITY_PREREG_20261122.md, not a revision to any frozen earlier study. The 3301–3340 source grid and all previously viewed public tapes are development evidence, never blind holdouts.

## Hypotheses and estimand
Unit of inference: independent seed×scenario **market run** (or independently sourced instrument-day); unique public timestamp cluster is an event, not a private order or owner. Competing predictive explanations are M0 (exposure/time-of-day activity), M1 (M0 plus strictly prior L2 spread/imbalance and lagged cluster counts), M2 (M0 plus history-based excitation). The question is whether prospective public-event predictive calibration/generalization improves, not whether a physical robot is identified. An unrelated deterministic periodic background is an explicit hard negative.

## Frozen procedure to finish BEFORE collecting new source data
1. Establish lawful source and source completeness; enumerate independent run IDs before generation. Record source revision, simulator code SHA, parameters, timestamps, public projection and provenance hashes. Do not select seeds based on observed outcomes. Assign entire market runs, not event rows or bin phases, to development, calibration and final evaluation. All analytical phases of a run remain in the same partition.
2. Predeclare at least three non-overlapping partitions: training for fitting, calibration for choosing any decision cutoff, and untouched evaluation for one-shot reporting. Holdout seed registry is written before source generation; an inability to establish independent runs means **NO_HOLDOUT**, not a smaller retrospective holdout.
3. Fit M0, M1 and M2 using only training records and strictly past covariates. Select observation windows, time bucket width, history kernel/lag, clipping, regularization, optimizer convergence tolerance, missingness/abstention rules and model comparison criterion in a separate frozen implementation spec BEFORE any source evaluation. Until that spec exists, do not run new source experiments.
4. Calibration may set a single common decision rule using calibration runs only; no per-scenario or per-phase threshold tuning. Final evaluation reports all scenarios and all predeclared models, with denominators, abstentions, negative-control false alarms, missed positives, calibration diagnostics and run-clustered uncertainty. No source-exchangeability assumption is silently inferred from a rescaling diagnostic.
5. Synthetic private oracle, when present, is joined **after** public-only scores have been written and hashed; it must never enter feature selection, fitting or threshold choice. Real owner identity and real-market FDR remain unknown.

## Required adversarial acceptance
- Invalid/nonfinite/nonnumeric/negative rate must yield explicit abstention, not Python TypeError or a successful statistic.
- Split prints at identical timestamps cannot increase event count.
- No missing, future, same-time or incomplete L2 can enter M1; unknown timestamp precision or feed gaps abstain.
- Unrelated periodic backgrounds and bursty momentum backgrounds are reported as negatives even if the residual test rejects.
- Dependence across phases and runs is respected; repeated same-seed replay is not an independent replicate.
- A model can fail to improve over M0; report this without changing frozen decisions.

## Next implementation
Build deterministic source-free causal feature extraction and fitting specification with fixed hyperparameters and adversarial tests; verify exact GitHub Python unit workflow. Only then register independent seeds and collect source. This document does not claim fitted models, calibration, p-values, real-market FDR, or owner labels.
