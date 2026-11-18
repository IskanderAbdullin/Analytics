# Real SBER local-size null control — preliminary research pilot

**Date:** 2026-11-18. **Status:** executed, exploratory; NOT statistical confirmation of any actual bot.

## Inputs and reproducibility

- T-Invest read-only public trade archive `SBER_TQBR`, `2026-11-17`.
- Raw compressed archive SHA-256: `0af872b1c9c861e7af40a1c40e5bbdf565f9161dd997337c08da584c4dafc782`.
- 121,920 public trade prints, rejected rows 0. Original fixed-volume screen under version present in PR: 209 candidate episodes. Not independent owners/programs.
- GitHub Actions run: https://github.com/IskanderAbdullin/Analytics/actions/runs/44279441032 .
- Method: `SizeShuffleNull.Compare` from `src/RobotDetector.Core/SizeShuffleNull.cs`: for each 60-second bucket and each instrument/source/direction/trading-mode/session, permute `QuantityLots` among the prints. Preserve all timestamps, original event IDs, prices, sides, local lot-size multiset, session and source. Re-run full screening pipeline for each shuffle.
- Repetitions B=4, first seed 31415, increments 1009. No private account information or raw market data in git/artifacts.

## Observed result

| Sequence | Candidate episodes | Prints whose size changed |
|---|---:|---:|
| Original | **209** | — |
| Shuffled #1 | 140 | 95,375 |
| Shuffled #2 | 141 | 95,112 |
| Shuffled #3 | 144 | 95,312 |
| Shuffled #4 | 129 | 95,160 |
| Average of shuffled | **138.5** | — |

A descriptive global candidate-count exceedance frequency under this **particular** shuffle model is `(1+0)/(4+1)=0.2`, which is **not statistically significant at conventional levels** even if one accepted the null model. Do **not** quote this as the probability that a signal is or is not a bot, and do **not** infer actual number of owners.

## Interpretation and limitations

The original count is higher than the four controls. This warrants further investigation, but it could reflect real order-splitting, fixed-size market microstructure, heterogeneous session patterns, correlated print bursts, timestamp resolution, or other mechanisms besides distinct bots.

The local size-shuffle null disrupts size-time correlations while retaining exchange print timing and within-minute distributions. It **does not preserve all serial size dependencies**, endogenous execution mechanisms, order ID, fill aggregation, or market impact. Four shuffles are far too few to calibrate a false discovery rate or global significance after exhaustive candidate search. Even a much larger B would not overcome inappropriate null assumptions.

**Next experiments:**
1. 20–100 controls on pre-registered alternative days/instruments; no tuning thresholds on the final held-out test.
2. Second clustered/Hawkes or block-preserving null which retains more size serial dependence.
3. Complete ABIDES-NG blinded known-agent ground-truth benchmark.
4. Stable cross-day prediction and out-of-sample prospective scoring; multiple-testing-aware detector confidence.
5. Refuse `confirmed` state until these gates are passed.

No real-time MarketDataStream, order placement or OsEngine trading integration is implied by this experiment.
