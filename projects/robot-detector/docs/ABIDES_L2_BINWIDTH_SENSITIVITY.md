# Genuine ABIDES public L2 bin-width sensitivity — frozen before results

**Experimental stage:** descriptive robustness only, no fitted detector, physical owner identity, market p-value, trade recommendation or source completeness attestation.

## Scientific purpose

Existing [genuine matching-engine background nulls](ABIDES_BACKGROUND_L2_NULLS.md) showed public depth-five book-imbalance to next-bin reported BUY-share Spearman correlations changed when only the background-agent population or wake-up policy changed. The [archive watermark gate](L2_ARCHIVE_WATERMARK.md) separately showed that truncated terminal intervals require explicit trustworthy completeness evidence.

A complementary source of non-robustness is **researcher choice of time-bin width**: selecting the interval size after seeing its correlation is a multiple-testing/selection leak. Rather than select a favorite duration, this experiment **freezes 10, 30 and 60 seconds before observing any outcome** and reports their differences for the **same public tape**.

## Frozen genuine ABIDES design

The source-controlled `tools/abides_l2_binwidth_sensitivity.py` fixes:
- **New, previously unused development-only** seeds `1901,1902`.
- Two simulated background modes: `poisson` (60 NoiseAgents, mean 20-second re-wake) and `fixed_cadence` (60 NoiseAgents, exactly 20-second re-wake).
- Session `09:30–09:42`, one ABM instrument, L2 depth five, pinned genuine ABIDES-NG commit `ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242`.
- **Four actual exchange matching-engine executions** (2 seeds × 2 backgrounds), each producing one public exchange executed-print tape and one public L2 event stream.
- **Three prespecified *analytical views* per simulation** (10, 30, 60 seconds; maximum permitted quote age equals the width), for 12 case-by-width records. These **are not 12 independent simulations** and may not be treated as one.
- No separately injected TWAP/VWAP/POV execution program, though normal simulated background agents are also algorithms. No private maker/taker IDs used by the feature; no cross-symbol mixing.

Every view compares the last valid public L2 imbalance in the **previous completed clock bin** with the reported BUY-lot share of the **next observed trade bin**, using the same tie-aware Spearman and gap/stale/one-sided/crossed-book abstention rules. The completed current-bin outcome is retrospective only; **not known at trade-bin start**.

For each seed/background, `aggregate()` verifies that all three bin-width records have **identical public SHA-256 projection fingerprints, executed print counts, total public lots, and L2 snapshot counts**. Each populated trade bin must be either counted in the eligible-bins total or explicitly abstain. Only coefficient bounds and descriptive statistics are asserted; the test does **not** require a positive or negative rho.

## Outputs and interpretation

Per simulation the report stores the number of widths with defined rho, the min/max and span of its observed rho across widths; for each background/width it reports the median descriptive rho across the **two actual seeds**. A `null` coefficient means the eligible data failed the minimum sample/rank variation rule, not that the market contained no algorithms.

A large span across widths shows **time discretization sensitivity** but cannot establish typical real-market error. A small span on four synthetic simulations also cannot certify robust market specificity. Widths are correlated views of the **same tape** and therefore do not provide independent replications or confidence intervals; neither a `max(rho)` threshold nor a best-performing bin width will be selected on these now-spent development results.

The ABIDES output is a simulated archive. Without a separately source-attested exclusive completeness watermark, the data function preserves the earlier descriptive tape behavior and explicitly reports `completion_watermark_independently_verified=false`. The study keeps `source_completion_verified=false`; no statement of real L2 completeness is permitted.

## Verified genuine ABIDES result (2026-11-21)

[Successful pinned ABIDES CI #44903121650](https://github.com/IskanderAbdullin/Analytics/actions/runs/44903121650) passed six plan/conservation tests and executed **four actual matching-engine simulations** on the source-frozen seeds 1901–1902 (two background modes). Each public tape was re-analysed at the **three prespecified** bin widths, producing twelve *correlated analytical views*, not twelve independent experiments.

| Background | Bin width | Eligible lagged 30s-equivalent quote/trade-bin pairs (two simulations) | Median **descriptive** Spearman rho |
|---|---:|---:|---:|
| Poisson noise | **10 s** | 123 | **−0.2430** |
| Poisson noise | **30 s** | 40 | **−0.1271** |
| Poisson noise | **60 s** | 20 | **+0.2061** |
| Fixed-cadence noise | **10 s** | 95 | **−0.2776** |
| Fixed-cadence noise | **30 s** | 33 | **−0.4279** |
| Fixed-cadence noise | **60 s** | 14 | **−0.1929** |

**Negative robustness finding:** Even the *sign* of the **two-seed cohort median** changes for the Poisson background between 30-second and 60-second binning, without any different market simulation or new private agent. Fixed-cadence coefficients vary substantially too. This is direct evidence that the **observed public statistic is sensitive to the arbitrary, research-chosen clock width** under these conditions. It does not prove every individual simulation reverses sign; cohort medians and per-simulation ranges are separate descriptive quantities preserved in the uploaded artifact.

The same-source SHA-256, print/lot/book-count conservation checks passed for all three re-analyses within each genuine simulation. Source completion remains unverified; the result is not a calibrated market FDR, a validated causal effect, an individual participant identifier, or a trading edge. Neither the 10-, 30-, nor 60-second width is selected as "best" after these outcomes; **1901 and 1902 are now spent**.

Artifact `abides-public-l2-binwidth-sensitivity` (aggregate-only, seven-day retention) contains the per-seed correlations and public-only count summaries. No private maker/taker IDs, account tokens, raw book/event tapes or trading orders were used.

## Verification and safety

Six pure-Python tests in `tests_background/test_abides_l2_binwidth_sensitivity.py` exercise frozen seeds, incomplete/duplicated matrices, conservation, identical tape across widths, explicit null correlations and rejection of false attribution/calibration fields.

The isolated [`robot-detector-abides-binwidth.yml`](../../.github/workflows/robot-detector-abides-binwidth.yml) workflow first runs these fast tests, then exactly four pinned ABIDES matching simulations, and uploads a seven-day aggregate-only artifact. It never uploads raw trade/event tapes, book levels, private maker/taker IDs or secrets.

Upon evaluation, seeds `1901,1902` become **spent** for all future independent validation claims. No real trading orders, no GUI/Computer Use or OsEngine changes. **Research/identity/trading release gate CLOSED.**
