# Prospective independent-source evaluation design — 2026-11-22 (DESIGN ONLY)

Status: **PROPOSED, NOT FROZEN FOR EXECUTION**. Authored after inspection of 3301–3340 and the 160-case source aggregate. Those cases are development evidence, not a blind test. No seeds allocated, source jobs launched, thresholds selected or performance claims made here.

## Scientific question
Can a period-agnostic, public-only conditional-null detector distinguish controlled TWAP injection from Poisson, fixed-cadence unrelated background and momentum, with honest coverage abstention, when all cohorts share a precommitted observation protocol?

## Unit and split
The independent unit is an **original matching-engine seed/world**, not fills, clock phases, repeated exports or a source replay. Four cohorts per seed (Poisson, fixed20, momentum, injected TWAP) are paired outcomes of one simulated world; uncertainty must cluster by seed. Separate disjoint development, calibration and final evaluation seed sets; no holdout source data until code, thresholds and exclusions are frozen. Prior 3301–3340 are spent development and must never be relabelled as final evaluation.

## Proposed precision gate (not a power claim)
Before allocating new seeds, calculate and archive an exact binomial/cluster bootstrap precision and power analysis under multiple plausible false-positive and sensitivity rates. A starting planning target is **at least 100 independent seeds** for final evaluation, each with four cohorts, subject to feasibility and preregistered recalculation. At 0/100 false alarms, the one-sided 95% Clopper–Pearson upper bound is about 2.95% for an individual cohort; this is NOT a guarantee of zero false alarms, nor a correction for multiple cohorts. Report confidence intervals for each negative cohort and all-cause abstention, plus paired seed-level contrasts; use multiplicity correction or predeclare one primary contrast. No claim of real-market FDR.

## Frozen-before-source requirements
1. Pin ABIDES revision, dependencies, matching engine, observation horizon, exchange event ordering, public schema and source licenses. Public-only inference must run before any private oracle is joined.
2. Freeze model version, training/calibration split, randomization procedure, candidate periods, binning and phase treatment, event-rate strata, split-fill handling, missing-L2 eligibility, coverage denominator and abstention rule.
3. Freeze a single primary estimand: seed-level difference in alarm probability (TWAP minus worst of the three negatives), with abstentions reported separately and a conservative sensitivity analysis counting abstentions as errors. Also report all three individual negative false alarm rates.
4. Freeze success criteria before data: e.g. TWAP sensitivity lower one-sided 95% confidence bound >0.80, and each negative cohort false alarm upper one-sided multiplicity-adjusted bound <0.05, with prespecified abstention ceiling. These are *proposed* gates, not achieved results; assess whether planned sample size has adequate power before adoption.
5. Hard negatives: exact same-time split fills; clock-origin changes; burst-preserving null; incomplete prior L2; irregular event density; missing duration; identical public tape with distinct hidden owner partitions. No hidden owner ID or controlled agent labels may enter public feature construction.
6. Record **all** outcomes, seed-wise provenance, failures, exclusions and null results. No phase, threshold or source selection based on evaluation performance; no reruns counted as new independent seeds.

## Feasibility and safety gate
Do not launch 400 expensive original-source cases just to fill time. First finish deterministic adversarial tests, verify data licensing and pinned source, produce a documented resource estimate and explicit affordable batch plan, then separately freeze the protocol and allocate locally unused seeds. If precision is infeasible, publish a negative/inconclusive feasibility conclusion rather than relaxing gates post hoc.

NEXT_ACTION: implement source-free exact confidence-bound and seed-clustered inference tests with synthetic fake fixtures, including zero events, abstentions and replay duplication; review the proposed power and multiplicity choices before final preregistration.