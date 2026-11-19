# Correcting post-hoc selection of the most crowded 100ms phase bin

**Status:** research-only, implementation and regression tests added 2026-11-19. No trading signal, bot identification, calibrated statistical probability or owner count is claimed.

## Why a different statistic is necessary

In the predeclared first-100ms check on SBER_TQBR and MOEX_TQBR (2026-11-17), the observed shares were **10.84% vs 10.18%**. But the already observed MOEX ten-bin histogram had its maximum in the **700–800ms bin** (2,030 of 15,208 public prints, approximately 13.35%).

It is **not valid** to inspect all ten 100ms bins, select the highest one, and then compare that selected bin with null simulations for only the first 100ms. That is a multiple-comparisons / look-elsewhere problem.

## Corrected observational statistic (no inferential guarantee)

Extend [ClockPhaseAudit.cs](../src/RobotDetector.Core/ClockPhaseAudit.cs) to report *two distinct questions*:

1. **Predeclared first-100ms:** retains previous first-bin counts, the same control distribution and descriptive tail frequency. This never changes retroactively when a later bin looks stronger.
2. **Exploratory maximum over all ten bins:** find `max_k(counts[k])`, choose lowest bin index in a tie, and for **each** minute-rotated null sample recompute the complete ten-bin histogram and its maximum. Compare the observed maximum to the distribution of the 99 *trial-wise maxima*, **not** to a distribution from one arbitrarily chosen bin.

Report `Peak100MsBin`, `ObservedPeakBinCount`, `ObservedPeakBinShare`, `NullMeanMaximumBinShare`, `Null95MaximumBinShare`, `DescriptiveAnyBinTailFrequency`, `RotatedMaximumBinCounts`. If the source group is too small/short, the descriptive observed maximum remains available but all null statistics remain `null`.

Mathematical example: if ten bins contain `[10,10,10,10,10,10,10,25,10,10]`, the selected maximum is 25 in bin 7; on a control sample whose bins are `[20,5,15,13,12,10,12,7,4,3]`, its control statistic is **20** (the maximum), not 7 (the control value at index 7). The null statistic must use the same max operation as the observed statistic.

The general **maxT/max-statistic resampling** principle for guarding against selection among multiple tests is documented in [Westfall & Young-style algorithms](https://statistics.berkeley.edu/sites/default/files/tech-reports/633.pdf), and implementation examples exist in [R multtest](https://web.mit.edu/r/current/arch/i386_linux26/lib/R/library/multtest/html/mt.maxT.html). **Those proofs do not apply automatically** to our approximate minute-phase rotation null; do not claim family-wise significance or calibrated p-values merely because the maximum is used consistently.

## Synthetic gate

- A stable public-like 740ms phase series must identify **700–800ms**, without changing the first-100ms result from zero to positive.
- Every null trial must create a 10-bin histogram and return its **largest count**. A maximum must be no less than the same trial's first100ms count (for the 100ms setting).
- A uniform ten-bin histogram remains nonexceptional after any coherent rotation.
- Source/mode/session isolation, input SHA, feed coverage and owner unknown fields unchanged.
- All baseline Robot Detector .NET tests and CLI smokes pass. This is an extension, not a replacement of previous findings.

## New independent-date protocol — frozen before its first run

Run the same **SBER_TQBR and MOEX_TQBR on 2026-11-18**, using the same fixed settings (first-ms 100, 100 minimum public prints per group, 99 shared-minute rotations, seed 20261119). The November 17 data informed the *choice to investigate the maximum* and are therefore **development data** for this statistic; results from November 17 cannot independently validate it.

Compute exactly the previously frozen first-bin shares *and* the newly frozen max-bin statistic. Do not choose different instruments or dates after seeing results. Print only aggregated source-group histograms, SHA hashes, observed and 99-trial null summaries; no raw exchange tape, owner/order IDs, account tokens, trade commands or market data artifacts.

Compare whether a start-of-second effect is consistent across two instruments and whether the strongest peak changes phase. Even if the max-bin descriptive frequency is small under this null, it means only that **public trade timestamps have an unusual clock phase under the chosen approximate rotation model**. It cannot prove any individual trader, number of physical bots or profitable prediction. Source clock/timestamp precision and shared infrastructure remain confounders.

**Results:** append only after the new GitHub Actions job has completed. A missing/unavailable archive must be reported as BLOCKED_BY_DATA rather than silently substituted.
