# Public-only lagged volume response (experimental Stage 2)

## Question and boundary

Can the *publicly observable* volume on the preceding completed clock bin be associated with **reported BUY or SELL lots** in the current clock bin, as a descriptive clue for volume-responsive execution (POV-like flow)? The output is **not** a hidden parent-order reconstruction, a fill-level VWAP/POV classifier, a trading signal, or an estimate of physical market participants.

This feature was designed in response to [#31](https://github.com/IskanderAbdullin/Analytics/issues/31). The earlier ABIDES evaluation revealed complete misses on one VWAP (50 controlled exchange fills) and one POV (14 controlled fills) scenario; neither historical scenario was used to fit a coefficient, threshold, or feature selection.

## Data contract and mathematics

Input is **only** the public `CsvTradeReader` projection. No private ABIDES maker/taker IDs, truth manifest, accounts, or live API are referenced anywhere in `VolumeResponseResearch.Describe`.

All windows are fixed UTC clock bins of width `--bin-seconds` (default 30). Events are separated by instrument UID, ticker, public trade source, trading mode, session ID, and data kind. BUY, SELL and UNKNOWN prints all contribute to **market volume** (V_t) for that group. Reported-side lots (B_t), (S_t) include just BUY or SELL prints, respectively. The source direction is **provider-reported** and may not mean what the trade side in ABIDES means; never conflate with passive order ownership.

Only contiguous *populated* clock bins yield observations:

```text
Previous completed UTC bin t-1: X_t = V_(t-1)
Current completed UTC bin t:     Y_t = B_t or S_t
Public diagnostic:               rho = SpearmanRankCorrelation(X_t, Y_t)
Public ratio:                    median( Y_t / X_t )
```

**The previous completed bin is the only volume exposure.** No t+1/future-volume predictor and no private truth may enter these features. Because the outcome `Y_t` is only observed after current bin t ends, this is a retrospective *association*, **not** an intrabin prediction available at the beginning of t.

The rank correlation uses average ranks for ties. If the feature or outcome is constant, or if there are fewer than `--min-pairs` contiguous observations (default eight), correlation is `null`, rather than 0. This protects against pretending a null coefficient proves no volume response. The reported median ratio may be **greater than one**: the previous market-volume denominator and current-side numerator refer to *different time periods* and the ratio is **not a true participation-of-volume share**.

A missing populated bin breaks adjacency; missing data is **never assumed to mean zero traded volume** because a single public CSV does not prove archive completeness. The number of non-adjacent transitions is explicitly returned, and entire groups exceeding `--max-bins` are skipped with a warning rather than sampled silently.

Report:
- `sideProfiles`: two reported-side summaries for each evaluated source group, including Spearman rho (nullable), median lag ratio (nullable), observed lots, adjacent-pair count and gap transitions.
- `observations`: bounded time-bin level public-only evidence with the previous bin's market lots and the current bin's reported lots. These do **not** include individual source event IDs or actor ownership.
- Explicit flags `physicalBotCountKnown=false`, `statisticalSignificanceEstablished=false`, `ownerIdentityKnown=false`.

## Run safely

From the `projects/robot-detector` directory:

```powershell
dotnet run --project src/RobotDetector.Cli -- volume-response `
  --input fixtures/synthetic_variable_clip_5s.csv `
  --bin-seconds 5 --min-pairs 8 `
  --output data/results/volume-response.json
```

A second `--output` to the same path fails closed; do not overwrite previous evidence. For instrument archives, choose a meaningful bin width and account for observed timestamps, session breaks, non-trading days and possible incomplete feeds. The command is strictly read-only.

## Tests and research hygiene

Five deterministic C# self-tests: controlled prior-bin association arithmetic and total print/lot conservation; missing-bin boundaries without zero imputation; append-only prefix invariance (no future leakage in earlier observations); source/session isolation, constant controls and order invariance; malformed configuration, oversize groups and duplicate event IDs. GitHub Actions runs a **fresh artificial development-only CSV**, not the older ABIDES held-out seeds.

Separate real ABIDES runner smoke reports *public-only diagnostic coefficients* on **already spent development seeds 41–44** (TWAP/null/VWAP/POV) without reading truth during feature computation. These coefficients are illustrative, not calibrated precision or physical producer evidence. **Never use the frozen 901–904 outcomes to choose bins, cutoffs or significance thresholds.** After any model is proposed, freeze new independent simulator configurations, seeds and eventually untouched genuine source dates/instruments **before** final blind evaluation.

## First genuine ABIDES public-only development observation — 2026-11-21

[Successful .NET CI #44891939160](https://github.com/IskanderAbdullin/Analytics/actions/runs/44891939160) passed **128/128** C# internal checks, including no-future-leak and missing-bin controls. [Successful genuine ABIDES CI #44891939139](https://github.com/IskanderAbdullin/Analytics/actions/runs/44891939139) ran all four pre-existing **spent development** scenarios on public simulated exchange fills using 30-second bins (59 adjacent pairs each). Importantly, it did **not** use source maker/taker identities in the public lag calculation.

| Synthetic scenario (one seed each) | Public prints | Spearman `previous total → next BUY` | Spearman `previous total → next SELL` |
|---|---:|---:|---:|
| TWAP seed 41 | 3,923 | 0.394 | 0.240 |
| **No controlled execution agent**, seed 42 | **3,060** | **0.695** | **0.765** |
| VWAP seed 43 | 3,788 | 0.544 | 0.584 |
| POV seed 44 | 3,702 | 0.746 | 0.487 |

**Critical negative finding:** the source with **no controlled execution agent** has stronger lagged association than the TWAP sample in both reported directions, and stronger than several of the other executed strategies. Therefore, positive `rho` cannot by itself distinguish VWAP/POV/TWAP programs from market-wide background autocorrelation. These four cases are *not* matched causal counterfactuals, and comparing their `rho` values does not establish a significance test or measure model specificity. **Do not add a candidate/bot flag based on a fixed `rho` cutoff.**

## Additional independent development-seed null survey

`tools/volume_response_dev_survey.py` defines an *additional* replication protocol with three untouched **development** seeds (61, 62, 63) for each of `null`, `pov` and `vwap` (nine ABIDES matching-engine runs). The script **discards private truth**, passes only the public CSV into the read-only C# descriptor and emits only public SHA fingerprints, ranks, counts and per-mode median ranks. Explicitly refuses the **spent evaluation** seeds 901–904. The workflow's aggregate artifact expires after 14 days; raw files remain ephemeral.

The nine-case development-only experiment **completed successfully** in [ABIDES CI #44892179775](https://github.com/IskanderAbdullin/Analytics/actions/runs/44892179775). The corresponding expiring artifact is `abides-public-volume-development`, containing only public fingerprints and aggregates. Each row below is the **median Spearman rho across three real ABIDES matching-engine simulations**, with the same 30-second bin and historical defaults for every scenario:

| Synthetic scenario | Median rho, reported BUY | Median rho, reported SELL |
|---|---:|---:|
| **Null (no controlled execution agent)** | **0.510** | **0.548** |
| POV | 0.538 | 0.501 |
| VWAP | 0.511 | 0.596 |

These associations overlap substantially. In these development simulations the null is slightly stronger than POV for SELL; null BUY nearly equals VWAP BUY. This fails to establish useful discrimination of controlled VWAP/POV programs by public lagged volume correlation. **No threshold was selected and no event-level classification was added**. This is descriptive reproducibility and sensitivity analysis: no calibrated market FDR, confidence bound, cross-instrument out-of-sample accuracy or participant identification. The previously frozen 901–904 truth outcomes were **not** used to design or select this diagnostic.

## Independent scientific references informing the null-first design

- [*Intraday periodicity in algorithmic trading* (2014)](https://www.sciencedirect.com/science/article/pii/S1042443114000274) describes intraday transaction and volume periodicity, including a possible market-wide coordination mechanism. Periodicity therefore need not identify a single physical algorithm.
- [*Does trade clustering reduce trading costs?* (2022)](https://onlinelibrary.wiley.com/doi/10.1111/fima.12405) reports periodicities and uses trading-activity lag controls. It motivates explicitly checking autocorrelation and fixed-clock confounders instead of claiming independent actor evidence from a pattern.
- [*Online learning of order flow and market impact with Bayesian change-point detection methods* (2024)](https://www.tandfonline.com/doi/full/10.1080/14697688.2024.2337300) discusses why anonymous metaorders cannot easily be directly recovered from public trade data; change-point segmentation is a possible **future** model but is **not** implemented by this feature.
- [*Volume autocorrelation, information, and investor trading* (2003)](https://www.sciencedirect.com/science/article/pii/S0378426603002310) describes serial correlation in observed market volume; a positive observed lag association is not sufficient identification of a specific participant.

These references support **experimental design and caution**, not calibrated predictive performance or participant attribution for this codebase. In particular, running a null test only after seeing a positive association is insufficient to claim confirmatory significance.

## Scientific limits

- Positive lag association can be caused by general market volume autocorrelation, time-of-day seasonality, independent market makers or many unrelated traders.
- Reported-side lots are mixtures; **every participant** may contribute to current-bin volume. No parent-order inference follows from a rho or a ratio.
- Conditioning on only contiguous *populated* bins can select for busy conditions and bias results. Null `rho` means not identifiable from these observations, not absence of a program.
- The feature can be used to *formulate* a future model of relative flow, but it is not an independent validated detector yet; do not report TP/FP on this feature as if it attributed individual orders.
- No significance correction for multiple instruments/windows/time resolutions; no real-market FDR, fill-level owner count, queue reconstruction or performance forecast.
- **Stage 2 scientific release gate remains CLOSED.** No T-Invest account or trading API access; no real orders, GUI, OS Engine changes or broker tokens.
