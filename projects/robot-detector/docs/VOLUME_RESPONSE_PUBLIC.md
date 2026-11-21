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

## Scientific limits

- Positive lag association can be caused by general market volume autocorrelation, time-of-day seasonality, independent market makers or many unrelated traders.
- Reported-side lots are mixtures; **every participant** may contribute to current-bin volume. No parent-order inference follows from a rho or a ratio.
- Conditioning on only contiguous *populated* bins can select for busy conditions and bias results. Null `rho` means not identifiable from these observations, not absence of a program.
- The feature can be used to *formulate* a future model of relative flow, but it is not an independent validated detector yet; do not report TP/FP on this feature as if it attributed individual orders.
- No significance correction for multiple instruments/windows/time resolutions; no real-market FDR, fill-level owner count, queue reconstruction or performance forecast.
- **Stage 2 scientific release gate remains CLOSED.** No T-Invest account or trading API access; no real orders, GUI, OS Engine changes or broker tokens.
