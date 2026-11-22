# Prospective M1 lagged-L2 conditional intensity design (2026-11-22)

Status: DESIGN FREEZE, NOT FITTED OR EVALUATED. Distinct from previously inspected 3301–3340. M0 is a constant-cluster-rate comparator, not a detector. M1 must not use source labels, agent IDs, future book events, or test-run rates.

## Inputs and causal ordering
A public print cluster is the unit; simultaneous split fills are grouped, with multiplicity recorded only as a separate public diagnostic. For each cluster at time t, use the last complete L2 book snapshot with timestamp strictly less than t. Same-time L2 is ambiguous and forbidden; absent, incomplete, stale or coarse-clock snapshots cause ABSTAIN, not imputation. If feed lacks a verified bound on L2 completeness and timestamp accuracy, model validity remains unestablished. Use only public bid/ask and timestamp, with strictly checked allowed fields and positive non-crossed quotes. No oracle labels in feature code.

## Candidate M1 and fit split
Define one **fixed** prospective feature: lagged relative quoted spread (ask-bid)/mid, mid=(ask+bid)/2, where 0 < bid <= ask. Fit a two-stratum constant intensity model using a spread boundary estimated from TRAINING RUNS ONLY (training median of eligible spread observations), with a fixed deterministic tie rule (spread <= training median is low; greater is high). Rates are cluster counts divided by fully observed exposure duration in each stratum; strata with zero eligible exposure or zero training clusters ABSTAIN rather than smoothing post hoc. Evaluation predicts from trained median and two trained rates; evaluation prints cannot enter rates or median. Exposure assignment requires complete, predictable L2 segments; unknown book continuity abstains. This is an exploratory descriptive conditional null, not calibrated significance.

## Mandatory falsifications before source holdout
- Same-time/future book snapshots rejected, including same-time tie ordering
- Split fills do not change target cluster counts
- Book staleness, missing snapshots, unknown completeness, invalid/crossed BBO and coarse timestamp precision abstain
- Median threshold is invariant to evaluation-run prints and L2
- No exposure in one stratum, zero event count or a one-sided stratum abstains
- Fixed unrelated periodic and momentum-burst backgrounds must be reported as hard negatives, never called owners
- Independence split by original source run, not multiple analytic phases of one tape
- M0/M1/M2 comparisons include abstention and coverage, not just a cherry-picked conditional statistic

## Scientific boundary
A low/high spread split is a pragmatic, predeclared falsifiable baseline. It is not evidence that conditional intensities are Poisson, that time-rescaled gaps are independent, or that event-source identities can be recovered. All calibration/threshold decisions must be frozen on training/calibration runs prior to genuinely independent evaluation. Synthetic oracle is assessment only. Real-market FDR and owners remain unidentified.
