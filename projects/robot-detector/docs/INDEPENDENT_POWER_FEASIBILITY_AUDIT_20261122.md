# Independent-world power feasibility — negative methodological result (2026-11-22)

**Classification: SOURCE-FREE HYPOTHETICAL DESIGN AUDIT, NOT EMPIRICAL POWER.**
[Precommitted complete 72-case grid](PAIRED_INDEPENDENT_POWER_GRID_PREREG_20261122.md) committed at `318ecb96` **before** code/any numerical outcomes; [implementation](../tools/public_hypothetical_power_grid.py) committed at `e085fac5` with eight negative/unit tests. Exact public [Python CI #45038045732](https://github.com/IskanderAbdullin/Analytics/actions/runs/45038045732) **100/100 PASS**, including 8 new power-grid tests. An *independent* SciPy beta/binom formula check reproduced the selected cutoffs and scenarios below; independent code review does not replace source validation. The **complete** 6×3×4 aggregate panel is deterministically regenerated using:
```sh
cd projects/robot-detector
python tools/public_hypothetical_power_grid.py --output data/results/hypothetical-power-grid.json
```
No source/oracle records, new seeds or raw L2 data are read.

## Frozen simultaneous gates and cutoff examples

Under only hypothetical IID **original seed worlds** (not prints or phase variants), four simultaneous one-sided Clopper–Pearson intervals use Bonferroni α/4=0.0125: TWAP lower sensitivity >0.80 AND all three negative upper worst-case error <0.05. ABSTAIN counts as miss on positive and possible false alarm on each negative. Pairing *within* a seed world is allowed and left dependent; joint success probability is only bounded, not treated as the product of marginals.

| Evaluation seed worlds n | Minimum positive alarms | Maximum errors in EACH negative cohort | One-sided adjusted upper if 0/n negatives |
|---:|---:|---:|---:|
| 100 | 90 | 0 | 0.04287 |
| 160 | 140 | 2 | 0.02702 |
| 250 | 215 | 4 | 0.01738 |
| 400 | 339 | 10 | 0.01090 |
| 600 | 503 | 18 | 0.00728 |
| 1000 | 829 | 34 | 0.00437 |

Selected **joint power lower–upper bounds** (hypothetical positive success p_pos, identical *marginal* error per each of three negatives p_neg):

| n | p_pos | p_neg | Rigorous lower bound | Rigorous upper bound |
|---:|---:|---:|---:|---:|
| 100 | .90 | .010 | 0.0000 | 0.3660 |
| 100 | .95 | .010 | 0.0000 | 0.3660 |
| 100 | .90 | .020 | 0.0000 | 0.1326 |
| 160 | .95 | .010 | 0.3516 | 0.7839 |
| 250 | .90 | .010 | 0.6597 | 0.8922 |
| 400 | .90 | .010 | 0.9916 | 0.9973 |
| 400 | .90 | .020 | 0.4533 | 0.8179 |
| 600 | .90 | .020 | 0.8924 | 0.9641 |
| 1000 | .90 | .020 | 0.9960 | 0.9987 |

The 100-world **starting suggestion is underpowered for the prespecified simultaneous release gate** under any within-seed cross-cohort dependence at plausible p_neg ≥0.01: even its joint *upper bound* is 0.3660 for 1% errors. At 2% errors, 100 worlds have upper bound 0.1326, not evidence of adequate evaluation power. A zero lower bound here means no *guaranteed* joint power, **not** that true power is zero. This is an adverse feasibility result; it must not be repaired by retroactively weakening thresholds.

## Source-cost estimate and external applicability boundary

[Original pinned 160 genuine ABIDES source run #44944144915](https://github.com/IskanderAbdullin/Analytics/actions/runs/44944144915) reported **160** matching-engine cases, source revision `ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242`, workflow started 2026-11-21T20:02:41Z and completed by 20:04:13Z (~92s wall). Linear **illustration only**, not a measured forecast: n=100 evaluation alone means 400 original source cases, 2.5× historical workload; n=400 means 1600 cases (10×), n=600 means 2400 cases (15×), **plus separate training/calibration runs and model implementation**. Runtime, concurrency, service quota, cost and simulator version at execution are not guaranteed by one historical workflow; no new source workflows were launched.

Historical spent development 3301–3340 had Poisson grouped false alarms 6/40 and momentum 7/40, and grouped TWAP positives 32/40 with 1 abstention. These are **inspected retrospective synthetic outcomes of the prior detector**, not prospective M0/M1/M2 distributions or a basis for a new holdout. Their high false-alarm fractions warn that **merely increasing sample size cannot fix specificity**; the assumed p_neg grid of 0–2% is explicitly *optimistic relative to that old failure*. A successful new scientific method must first demonstrate lower hard-negative error without posthoc retuning.

**Rights / access:** [source gate](REAL_SOURCE_LICENSE_GATES.md) permits pinned ABIDES-NG research simulation under its upstream BSD-3-Clause licensing documentation, but source-revision/LICENSE and simulation dependency pin must be rechecked before *new* source jobs. Real exchange L2 licensing and completeness remain blocked. No owner/FDR inference from simulation. No new seeds allocated.

**Decision:** retain proposed ≥100 worlds as a **design idea only**, not a frozen evaluation sample; do NOT launch 400+ original cases. Prioritize scientific method falsification (conditional intensity residuals, M0/M1/M2 hard negatives) and independent source/protocol validity review before selecting a new power/resource configuration. The master release issue stays OPEN.

Sources:
- NIST exact binomial: https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbino.htm
- NIST Bonferroni: https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm
- ABIDES-NG upstream licence: https://github.com/GabrieleDiCorato/abides-ng
