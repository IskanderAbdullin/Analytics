# Prospective conditional-intensity time-rescaling: falsification-first design (2026-11-22)

Status: **PREREGISTERED METHOD DESIGN, NOT AN EXPERIMENT, NOT CALIBRATED**.
Scope: public unique timestamp clusters and causally eligible previous-only L2; no agent IDs, owner inference or market p-values. Prior seeds 3301–3340 remain spent development evidence.

## Target and competing nulls
Define a *predictable*, nonnegative intensity λ(t | H(t−)) for public unique-timestamp cluster arrivals, not for individual split prints. Every intensity covariate must be observable strictly before t (including L2 with timestamp uncertainty), with explicit clock precision, feed completeness and source capability flags. λ is a model of **observable arrivals**, not agent intent. Fit on a designated training tape only; lock coefficients, feature transforms, coverage criteria and model-selection rule before any held-out tape. If no independent tape is available, report **model-development diagnostics only**.

A future preregistration must fix train/calibration/evaluation source-days, instruments, disjoint seed×scenario market runs, exact model family, observation windows, minimum event count, optimizer, regularization, thresholds, diagnostics and multiplicity handling. Do not retrospectively nominate the old 160 ABIDES runs as blind.

Candidate model M0: piecewise constant exposure-adjusted intensity per predetermined UTC time-of-day bucket estimated only from training days, with exposure gaps excluded. M1: M0 times a causal function of lagged public cluster count and lagged L2 imbalance/spread (predeclare lag and clipping), not contemporaneous or forward-looking snapshots. M2: explicitly fitted self-exciting point process as a hard-negative alternative. Model comparison requires genuinely separate source units and blocked time splits; event timestamps within one source run are not independent experimental units.

## Rescaling and mandatory abstentions
For successive distinct observable cluster times t_(i−1),t_i in a *continuous and complete* eligible observation window, compute z_i = ∫[t_(i−1),t_i] λ(u|H(u−)) du using a declared numerical tolerance and only causal covariates. Under a correctly specified simple point-process conditional intensity, z_i should resemble unit exponential waiting times; this is a **model diagnostic**, not proof of a robot or a valid market p-value. Exclude first-event left censoring; do not integrate across feed gaps, session boundaries, unknown timestamp precision, ambiguous same-time L2, or zero/invalid exposure. Record both denominator and abstentions. A zero λ integral with an observed event is model failure, not a valid zero waiting time. Exact simultaneous prints are one public timestamp cluster, not independent arrivals.

## Precommitted source-free falsification cases
1. Two constructed tapes with exactly one event per fixed 5s cell, identical occupancy and cluster multiplicities, but one with deterministic near-boundary placements and one with uniform interior placements. Conditional cell-count randomization cannot identify the within-cell hazard from counts alone; any apparent significance requires an additional exchangeability assumption.
2. Duplicate any print at an existing timestamp: unique cluster arrival count and z_i unchanged, multiplicity changes; a per-print rescaler that changes z_i is rejected.
3. Construct self-exciting bursts with matching coarse occupancy: naive uniform-in-cell null is misspecified. A fitted M2 may absorb the same rhythm as the purported target, revealing a validity–power tradeoff.
4. Reverse or delay L2 snapshots so a quote arrives at or after its print, and add conflicting tied snapshots: M1 must abstain, not use future L2.
5. Insert a missing-feed interval between two clusters: integration across it must abstain rather than silently treat zero observed events as zero intensity.
6. A perfect unrelated 20s fixed cadence is a hard negative for actor attribution regardless of any exponential-residual rejection.
7. Identical public tapes with different hypothetical private owner allocations must produce identical rescaled residuals.
8. Quantized timestamps with unknown resolution, empty tape, one cluster, zero predicted intensity, non-finite intensity, and timezone/session discontinuities must fail closed.

## Acceptance / decision gate
Before any independent source evaluation: implement deterministic source-free residual computation with exposure and previous-only guards, tests for all eight cases, frozen source allocation and honest comparison against M0/M1/M2. Publish calibration failures and no-power outcomes. **No source run, holdout, p-value, real-market FDR or owner label is claimed by this document.**

NEXT_ACTION: implement fail-closed causal rescaling core and eight negative controls; then freeze an independent source allocation before evaluation.