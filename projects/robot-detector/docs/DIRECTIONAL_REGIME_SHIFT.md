# Stage 2: public-only directional regime-shift monitor

**Status:** experimental read-only research; significance/real-market specificity and individual actor detection **NOT established**. This module is **not** a Bayesian online change-point detector, CUSUM test, fill attribution engine, or trading signal.

## Scientific rationale

The existing periodic fixed-/variable-size screens missed all controlled fills in individual ABIDES-NG VWAP (50/50) and POV (14/14) examples, and the independent public-only volume-lag study found large, overlapping Spearman correlations for null, VWAP and POV backgrounds. Therefore adding another threshold on raw volume-lag correlation would overclaim evidence. This experiment tests a *different observable*: an abrupt change in **reported BUY share of public known-side lots**, without ever claiming it identifies the hidden actor.

References for conceptual motivation (not implementations or performance endorsements):
- Adams & MacKay, 2007, [Bayesian Online Changepoint Detection](https://arxiv.org/abs/0710.3742). Our code does **not** compute a posterior run-length distribution or Bayesian probabilities.
- [Online learning of order flow and market impact with Bayesian change-point detection methods](https://doi.org/10.1080/14697688.2024.2337300), Quantitative Finance (2024). Motivates studying changes in public order flow, but the present simple heuristic is neither the paper's algorithm nor validated against its data.
- [Online multivariate changepoint detection with Type I error control](https://www.sciencedirect.com/science/article/pii/S0167715221002200) (2022). Controlling repeated sequential false alarms requires additional statistical assumptions, simulation/null families and threshold calibration **not** implemented here.

## Observable and algorithm (pure public-only)

Input: `TradeImportResult` parsed from public prints. Partition by instrument UID, ticker, source, trading mode, session and data kind. Group into UTC-aligned **30-second** bins (`--bin-seconds`). For each bin `t`:
- `BUY_t`: total lots whose *publicly reported* side is BUY;
- `SELL_t`: same for SELL;
- `UNKNOWN_t`: all other valid public prints;
- `K_t = BUY_t + SELL_t`, `V_t = K_t + UNKNOWN_t`.

A bin is eligible only if `K_t` has at least the configured minimum and `K_t / V_t ≥ min-known-side-fraction` (default 0.9). Ineligible bins **reset** the past baseline; unknown direction is never imputed as BUY or SELL. Source gaps also reset the reference baseline. The monitor is retrospective: it evaluates the **observed content** of the current bin after reading the file, against exclusively earlier bins. **A final archive bin may be truncated or still forming; the code does not verify a trusted end-of-bin watermark.** Do not interpret the final bin as necessarily complete or enable live alerting without an independent completeness/watermark gate.

For each eligible completed current bin, compare with exactly six **earlier consecutive qualified** bins (default `--reference-bins 6`), never the current or any future bin:

```text
baseline reported BUY share = sum(BUY in bins t-6..t-1) / sum(K in t-6..t-1)
current reported BUY share  = BUY_t / K_t
signed change               = current - baseline
candidate                   = |change| >= 0.25 and valid past/current lots
```

This is a *rolling past-baseline share contrast*, with a simple two-bin cooldown after an observed candidate to limit immediate duplicates. It is not a sequential hypothesis test: the 0.25 threshold is exploratory, not a calibrated p-value, confidence, posterior bot probability, or risk-adjusted signal. It has no parent-order identity, market impact, quote depth or causal event attribution.

The output contains only **per-bin aggregate** public lots, reference/current shares, timestamps, source/mode/session and unvalidated reason labels. It does **not** contain individual event IDs, private ABIDES maker/taker IDs, source tokens, orders or personal accounts.

## Safe CLI

```powershell
dotnet run --project src/RobotDetector.Cli -- direction-shift `
  --input fixtures/synthetic_activity_episode.csv `
  --bin-seconds 30 --reference-bins 6 --min-share-shift 0.25 `
  --output data/results/observed-direction-shifts.json
```

Writes only to a new file and refuses to overwrite prior evidence. The CLI returns `sourceRejectedRowTotal > 0` as a nonzero warning exit for incomplete imports. The `SourceCoverageVerified` flag is inherited from the public source; a lone CSV never proves continuous exchange coverage. Large groups (`--max-bins`, default 10,000) are explicitly skipped rather than silently sampled.

## Deterministic verification

Six new C# self-tests assert:
1. After six stable 50/50 bins a synthetic public 90/10 print mixture yields exactly one observed shift, with exact 0.4 delta, **no owner identity or significance**.
2. A stable stream never produces a shift; the same shift produced by many independent public print sources still triggers but **cannot imply one actor**.
3. Missing clock bins and low known-side fractions reset the baseline; gaps are never filled as zero market-volume.
4. Previously emitted candidate windows cannot change when newer prints are appended; independent UID/session groups do not share history; arrival-order reorder does not change aggregates.
5. Duplicate public IDs and invalid configuration fail closed; oversize groups are skipped.
6. Explicit cooldown reduces consecutive redundant candidate windows.

The existing GitHub .NET CI additionally creates two truly fresh toy public CSVs (stable vs shifted) and validates the CLI JSON contract. The full C# suite now has **134** checks (if all CI checks pass).

## Genuine ABIDES-NG null-first survey

The new `tools/directional_shift_dev_survey.py` runs genuine pinned ABIDES-NG matching-engine simulations with three **new development seeds 71, 72, 73**, each in three modes: agent-free null, VWAP and POV. It discards private maker/taker truth, feeds **only** the public exchange-projection CSV into this public-only monitor, and aggregates *counts of shift windows* by mode and public clock bin. No hidden truth is used for any feature or threshold. It explicitly refuses prior spent evaluation/development seeds 41–44, 61–63, 901–904. It uploads a small aggregate-only CI artifact with 14-day retention.

The null mode is **not** an observationally equivalent controlled counterfactual for positive modes. Overlapping candidate counts across positive/null modes invalidate any inference that a shift labels a distinct robot. Even apparently fewer null candidates in three toy runs would be far too little evidence for a calibrated false positive rate or market predictive value.

## Executed synthetic public-only results (2026-11-21)

[GitHub .NET CI #44893110208](https://github.com/IskanderAbdullin/Analytics/actions/runs/44893110208) passed **134/134** internal C# tests and a CLI smoke: ten stable synthetic bins yielded **zero** candidate windows; six baseline bins followed by one BUY 90% vs 50% past BUY proportion yielded **exactly one** observed change of +0.4.

[Real ABIDES-NG CI #44893110253](https://github.com/IskanderAbdullin/Analytics/actions/runs/44893110253) ran the actual pinned matching engine for nine **exploratory development** simulations (three seeds 71–73 for each null, VWAP and POV). All public-only source shares used fixed defaults without private-maker/taker exposure:

| Synthetic cohort | Exchange prints in three runs | Evaluated clock bins | Unvalidated direction-shift windows | Cases with at least one candidate |
|---|---:|---:|---:|---:|
| Agent-free null | 9,526 | 162 | **1** | 1/3 |
| VWAP agent | 9,796 | 162 | **4** | 2/3 |
| POV agent | 9,448 | 162 | **2** | 2/3 |

A null source **also** triggered. This is a genuine confounder for any claim that the change-point labels are executions by one algorithm. Per 100 evaluated clock bins the descriptive candidate counts are 0.62 (null), 2.47 (VWAP), 1.23 (POV), but **these are not calibrated market-wide false discovery or false alarm probabilities**. The cohorts are not causal counterfactuals, the sample is tiny and multiple models/settings could have been considered. Importantly, these aggregates **do not score parent-order/fill-level recall**, because the method has no event-level actor attribution.

### Pre-registered independent synthetic replication

A new sealed wrapper, `tools/directional_shift_frozen_replication.py`, fixes the **previously unused** seeds `1101,1102,1103,1104`, the three modes `null,vwap,pov`, and **all existing feature settings** (30 s bin, 6 earlier bins, 0.25 minimum absolute reported BUY share change, 0.9 known-side fraction, 2-bin cooldown, minimum current known lots 100, reference known lots 500). Its protocol, Python invariance tests and CI command are committed **before** collecting the outcomes. This tests *replication*, not learning or threshold optimization, and provides a separate aggregate-only expiring artifact. Do not use these results to tune a follow-up model; a later model needs another genuinely untouched holdout.

### Independent replication outcome — negative result

The locked protocol completed **successfully** in [GitHub ABIDES-NG CI #44893601107](https://github.com/IskanderAbdullin/Analytics/actions/runs/44893601107), producing the separate expiring `abides-public-direction-shift-frozen` artifact. All 12 genuine matching-engine runs used the **exact same parameters** as the exploratory study; the 4×3 seed/mode matrix was fixed before evaluation.

| Pre-registered cohort (four simulations) | Public exchange prints | Evaluated clock bins | Unvalidated public shift windows | Simulations containing at least one |
|---|---:|---:|---:|---:|
| **No controlled execution agent** | 13,798 | 216 | **1** | 1/4 |
| **VWAP controlled execution** | 14,007 | 216 | **0** | 0/4 |
| **POV controlled execution** | 13,753 | 216 | **1** | 1/4 |

**Conclusion:** The hopeful exploratory ranking (**null 1, VWAP 4, POV 2**, each on three development runs) **did not replicate**. In this independent synthetic seed cohort VWAP produced **no shift candidates**, while a background-only null produced one. POV and the null each generated one. The feature is **not a reliable discriminator** of VWAP/POV controlled execution under these simulated conditions. Do not re-tune its threshold against these now-spent 1101–1104 outcomes, do not ship real-time alerts, and do not interpret shift windows as parent orders or individual bots.

This is an explicit negative result rather than an inferential test: the number of simulations is small, reported-side definitions are simulator-specific, null/positive cohorts are not perfectly matched causal counterfactuals, and a count of market-wide shift windows is not a per-order true/false classification. Zero VWAP candidate windows says this feature did not detect a public share shift in these runs; it is **not** a measured 0% fill-level VWAP recall.

## Boundaries and next gates

- First run this monitor on held-out **synthetic development** nulls and disclose the null shift windows. Never tune to spent seeds 901–904.
- If attempting a future *inferential* change-point model, predefine the full model-selection and threshold procedure on **new independent development data**. Test against clustered-background, market-wide synchronized directional shocks, timestamp gaps, auctions, feed-coverage loss, and independent simulations with no controlled algorithm.
- Freeze entirely new simulation seeds for blind evaluation before fitting, then validate on untouched real exchange dates/instruments with source-specific clock/side semantics. Multiple-hypothesis and sequential testing error control remains an unsolved scientific task.
- **Research release gate CLOSED**; **no physical bot counter, no market precision estimate, no live alerts or trading orders**. No OsEngine, GUI or broker-account actions.

Related [issue #31](https://github.com/IskanderAbdullin/Analytics/issues/31), [prior public volume null findings](VOLUME_RESPONSE_PUBLIC.md), [ABIDES blind execution protocol](ABIDES_GENUINE_REPLAY.md).
