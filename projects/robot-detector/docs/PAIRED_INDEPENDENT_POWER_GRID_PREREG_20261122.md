# Prospective conservative joint-power feasibility grid — source-free (2026-11-22)

**DESIGN FREEZE BEFORE CALCULATIONS.** Extends [paired-seed inference preregistration](PAIRED_SEED_CLUSTER_INFERENCE_PREREG_20261122.md) and the *unfrozen* [independent source evaluation design](INDEPENDENT_SOURCE_EVALUATION_DESIGN_20261122.md). This is not an execution protocol, not a new holdout, not independent empirical evidence, and may only be used to decide whether a prospective source study is worth its resource cost. No seeds or source jobs.

## Frozen conditions and hypothetical input grid

- One **original independent world** consists of one paired observation from each of four Poisson/fixed20/momentum/TWAP cohorts. Treat all abstentions as errors: negative ALARM or ABSTAIN = conservative error, positive only ALARM = success.
- Proposed (not yet adopted) joint scientific release gate: for positive TWAP, Bonferroni-adjusted one-sided Clopper–Pearson sensitivity **lower > 0.80**; for **all three** negative cohorts, Bonferroni-adjusted one-sided error **upper < 0.05**. Familywise alpha=0.05, per-marginal alpha=0.0125, no best-cohort selection. Coverage/abstentions reported separately. This is NOT a physical robot inference.
- Compute **only** for original-world sample sizes n ∈ **{100, 160, 250, 400, 600, 1000}**, hypothetical positive all-case alarm probability p_pos ∈ **{0.85, 0.90, 0.95}**, and identical marginal worst-case negative-error probabilities p_neg ∈ **{0.00, 0.005, 0.01, 0.02}** for each of the three negatives. These are not inferred from previously viewed 3301–3340. No parameter grid expansion after looking at results without versioned addendum.
- For each n, calculate integer cutoff k_pos_min (minimum successes with lower bound >0.80) and k_neg_max (maximum errors with upper bound <0.05). If none, mark infeasible, not guessed.
- For each hypothetical rate pair compute exact **marginal** pass probability from Binomial(n,p) distributions. Crucially, the four cohort outcomes are paired within a world; their dependence is unspecified. DO NOT multiply four marginal pass probabilities or assert exact joint power. Report rigorous Bonferroni/union-bound **joint power lower = max(0,1 - (1-q_pos) - 3*(1-q_neg))**, and upper = min(q_pos,q_neg). Lower 0 means inconclusive, not zero true power.
- No new source seed allocation without separate preregistration of source lawfulness, code pin, sample-size feasibility, threshold stability, model fit, observation horizon and 3-way run-disjoint train/calibration/evaluation. The proposed n is *evaluation worlds only*; training/calibration costs must be added.
- If n=100 cannot support reasonable success under plausible hard negatives, document as a negative feasibility result, do not silently relax cutoffs. When n>1000 is scientifically necessary, stop for a reviewed scalable implementation; do not truncate source data.

## Numerical reproducibility and falsifiers
- Deterministic exact finite binomial sums, no Monte Carlo, no new random seeds. Source-free tests check n=100 zero-error upper, threshold monotonicity in n where appropriate, mandatory full Cartesian grid, p_neg=0 upper bound behavior, >=0/<=1 probability bounds, union-bound not exceeding marginal upper, no claim of source independence.
- NIST Clopper–Pearson method: https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbino.htm
- NIST Bonferroni multiple comparisons: https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm
- Exact matched-pair discordant testing (context, not a source-level validation): https://pmc.ncbi.nlm.nih.gov/articles/PMC3716987/

**NEXT_ACTION:** source-free implementation + all-grid aggregate JSON and adversarial tests; compare n=100 proposal honestly; then scientific resource/source-rights review, **not** a large original ABIDES run.