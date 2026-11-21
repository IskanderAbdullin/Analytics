# Genuine ABIDES public L2 clock-origin sensitivity — frozen before outcomes

**Date:** 2026-11-21. This is a strictly **read-only** source-timing robustness study, not a new detector, physical agent label, real-market FDR or trading algorithm.

## Scientific reason

The preceding genuine ABIDES [bin-width robustness experiment](ABIDES_L2_BINWIDTH_SENSITIVITY.md) found that the **two-seed Poisson-background median Spearman correlation changed sign** when the public book/next-trade interval width changed from 30 seconds to 60 seconds on the **same synthetic market tapes**. Bin width is not the only arbitrary time discretization choice: a researcher can also shift the **origin (clock phase)** of a fixed-width interval while holding the underlying public trades and order-book snapshots unchanged.

This experiment fixes three offsets **0s, 10s and 20s** for **one constant width of 30s** *before* seeing any new results. It reports all three values without selecting a "best" phase.

## Preregistered pinned genuine matching-engine plan

Source: `tools/abides_l2_binphase_sensitivity.py`. Source-controlled immutable constants:

- Previously unused development-only genuine ABIDES seeds **2101 and 2102**, registered as **spent for future blind evaluation** on the same source commit that launches this study. Previous seeds 41–44, 61–63, 71–73, 901–904, 1101–1104, 1301–1304, 1401, 1501, 1801–1802 and 1901–1902 cannot be reused as fresh evaluations.
- Two background modes: 60 Poisson-noise agents (mean 20s wake-up) and 60 fixed-cadence noise agents (20s), no separately injected TWAP/VWAP/POV execution agent. This is **not** a market devoid of algorithmic policies.
- **Exactly four genuine exchange simulations** (two seeds × two backgrounds), each producing one original anonymous public execution tape and one depth-five L2 stream.
- Pinned upstream matching engine revision `ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242`; session 09:30–09:42, ABM instrument, depth 5.
- For each original public tape, re-bin the book and prints with identical 30-second intervals at **exactly three fixed phase offsets** 0/10/20 seconds. Mathematically the source timestamps are shifted together by a constant *before* the existing strict integer L2 processing, so relative event times, equal-timestamp ties, prices, quantities and reported sides remain unchanged. This is a coordinate transformation, not a new market draw or event sequence.
- Previous fully completed book bin's displayed depth imbalance versus *next completed trade bin's* reported BUY fraction; same missing/stale/crossed book abstention and tie-aware Spearman. No threshold/phase selection, future lookahead, real-time prediction, maker/taker ID reading or individual parent-order identification.

The script checks exact original public SHA-256, print count, total public lot count and L2 snapshot count across the **three correlated views of each of the four actual tapes**. It reports a per-simulation rho range across phases and cohort-median descriptive coefficients across the two genuine seeds per phase. Undefined coefficients are explicitly null, not zero. Source archive completeness remains **not independently attested**.

## Scientific non-independence / release decision

The twelve analytical records are **NOT twelve independent market experiments** and do not support confidence intervals or real market p-values. Changing source time origin, like changing bin width, is a researcher degree of freedom that can produce large apparent variation without any distinct execution program. A large phase-dependent correlation would undermine use of a single chosen public rho as evidence of a physical bot. Conversely, a small variation on four synthetic market runs is insufficient to validate the real world.

On execution, 2101/2102 are spent for future independent holdout claims. They are tracked in `research/seed_registry.json` with literal source-constant auditing, not used for model training or trading.

## Reproduction and tests

Six no-simulator tests in `tests_background/test_abides_l2_binphase_sensitivity.py` verify phase values, exact shift invariance, signed source arithmetic validation, four-vs-twelve independence, frozen case matrix and rejection of false source/identity claims. The isolated [`robot-detector-abides-binphase.yml`](../../.github/workflows/robot-detector-abides-binphase.yml) workflow runs these pure tests **before** the genuine pinned matching engine and publishes only an aggregate-only seven-day result artifact.

No actual accounts, broker tokens, user trade history, local PC GUI or real orders are touched. **Scientific Stage-2 identity and live-trading gates remain CLOSED.**

## Executed four-simulation result (2026-11-21)

[Successful genuine ABIDES matching CI #44912441330](https://github.com/IskanderAbdullin/Analytics/actions/runs/44912441330) ran the **six frozen-plan Python tests** and **four actual pinned matching-engine scenarios**, reprocessing each anonymous public L2/executed-print tape at the three predeclared 30-second origins without any market reruns across origins.

| Public synthetic background | Origin offset 0s: rho / eligible bin pairs | 10s | 20s |
|---|---:|---:|---:|
| Poisson noise, two-seed median | **−0.0137 / 39** | **−0.1608 / 42** | **−0.1809 / 41** |
| Fixed-cadence noise, two-seed median | **−0.2178 / 42** | **−0.1946 / 41** | **−0.4925 / 42** |

Changing only the analytical **clock-origin** of the same simulated public tape altered the two-seed median coefficients materially, especially fixed-cadence at 20 seconds. Unlike the earlier width experiment, **none of these six median values changes sign**. The result is a negative robustness warning **about researcher-controlled time alignment**, not a measure of real market false-positive rates or statistically significant agent identification. Cohort medians do not establish a sign change in any individual simulation, and the twelve views are correlated.

The exact public digest, executed lot/fill totals and L2 source snapshot counts were conserved across all phases within each of the **four** genuine simulations. The evaluated 2101/2102 seeds are now **spent** for any further independent holdout claim.

[Research seed-ledger CI #44912522820](https://github.com/IskanderAbdullin/Analytics/actions/runs/44912522820) passed after replacing its former "unlisted candidate" illustration: once 2101/2102 became spent, testing them as unknown candidates was correctly rejected. The non-spent demonstration numbers 2201/2202 are **not** certified globally unused; they only lack a local ledger collision.

Seven-day aggregate-only result `abides-public-l2-binphase` contains per-run descriptive values without private maker/taker truth or raw public events.

## Follow-up: within-original-tape paired diagnostics (2026-11-21)

After the original four simulations, the read-only aggregate now explicitly
compares **each original seed/background simulation with itself** at 0s→10s
and 0s→20s. These are signed **descriptive** rho differences, not four
independent experiments at each origin. Per-simulation output also records
whether the **defined** rho signs straddle zero (distinct from the sign of a
two-seed cohort median) and the range of eligible clock-bin counts.

The derived `paired_cohort_contrasts` computes medians **only from seeds
with both comparison coefficients defined**. It refuses to infer a paired
effect by subtracting unpaired phase-specific medians: one phase may have
valid rho on a different subset of the two original seeds. A null paired
contrast means not enough defined paired coefficients, not zero difference.
The same simulated source tape is used, but the *eligible bin memberships
may change*, so these contrasts are not event-wise matched observations.
No phase is selected, no additional matching-engine run is required to
re-analyze already saved full case outputs, and seeds 2101/2102 remain spent.

This is a scientific **robustness/fragility diagnostic only**: with merely
two seeds per background, no confidence interval, real-market error rate,
private actor attribution or live release gate is justified. The additional
tests use constructed software fixtures, not new independent market data.
