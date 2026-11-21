# Genuine ABIDES-NG background-only L2 null cohorts

**Protocol frozen 2026-11-21 before execution; no model training.** This study is deliberately about the *non-identifiability* of execution programs from aggregated public-market L2/print associations. It is not a detector, a high-confidence identity estimate, an order-entry program, a validated real-market conditional null or a market FDR measurement.

## Prior evidence motivating this study

- [Strict quote/fill join](L2_TRADE_CONTEXT.md): 2,630 out of 2,630 genuine ABIDES simulated public fills had the same timestamp as some order-book mutation, therefore a strict within-timestamp as-of join correctly abstained on all fills.
- [Completed-bin lagged L2](L2_LAGGED_BIN.md): using the fully *previous* 30-second bin avoids event-order ambiguity. Exploratory descriptive Spearman rho against next-bin reported BUY share was null background **−0.341** (13 pairs), POV **0.152** (10), VWAP **0.104** (13), not a reliable discriminant.
- [Constructed public common-factor counterexamples](L2_COMMON_FACTOR_NULLS.md): synthetic public common market state and synchronous broad shocks can intentionally produce **rho 1.000** without specifying an identifiable parent execution order. These were deterministic educational data, **not** an actual matching-engine null.

The next valid scientific question is whether **genuine order-book matching** with varied background mechanisms can produce analogous public associations **without adding the particular controlled TWAP/VWAP/POV execution agent**.

## Frozen genuine matching-engine design

Source: pinned [ABIDES-NG commit ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242](https://github.com/GabrieleDiCorato/abides-ng/tree/ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242). The frozen plan is implemented by `tools/abides_l2_background_nulls.py` and tested in `tests_background/test_abides_l2_background_nulls.py`.

| Background cohort | Simulated population | Why it matters |
|---|---|---|
| `poisson_noise` | 60 `NoiseAgent` agents with Poisson inter-wake times, mean 20 s | No singled-out execution program; dispersed background arrivals |
| `fixed_cadence_noise` | 60 `NoiseAgent` agents with fixed 20 s between re-wakes | Check whether periodic public flow can emerge from independently waking background agents |
| `noise_plus_momentum` | 50 Poisson noise agents + 10 `MomentumAgent` trend followers | Heterogeneous *algorithmic* background may produce common market directionality without a specifically injected VWAP/POV parent |

Every cohort runs exactly the two **previously unused** seed values **1801, 1802** (six genuine exchange simulations), one ABM symbol, a 12-minute synthetic session **09:30–09:42**, L2 book capture depth five, 30-second public bins, last L2 quote only from the strictly **previous completed** clock bin, at most 30 s old.

All cohorts **omit separately injected `TWAPExecutionAgent`, `VWAPExecutionAgent`, and `POVExecutionAgent`** and check that no named execution agent appears. This **does not** mean a market without algorithmic participants: background noise, momentum agents, exchange and simulated liquidity providers have automated policies. Nor does it imply zero hidden metaorders in a real market.

Parameter values, modes, source commit, seed list, source/data validity checks, and summary schema are **committed before execution**. No result-dependent threshold, model tuning, adaptive seed selection, classifier or causal claim is permitted. After the run, seeds 1801 and 1802 become **spent** and cannot be treated as a fresh blind holdout for model fitting.

## Strict public-only observable

Actual exchange matching produces L2 snapshots and fills. The feature pipeline first projects each fill to the *public scalar tuple* `(timestamp_ns, price_cents, quantity, reported_aggressive_side)`, without accessing its maker/taker IDs; the separate summary hash is computed from only this public projection.

- Previous-bin book imbalance: `(sum_bid_qty - sum_ask_qty) / (sum_bid_qty + sum_ask_qty)` for all displayed depth-five levels from the last valid public update of the completed earlier 30-second bin.
- Outcome: **subsequently completed** public trade-bin reported BUY share `BUY_lots / (BUY_lots + SELL_lots)`.
- Ties-aware Spearman rank association is emitted only when at least five valid pairs have nonconstant ranks; otherwise `null`. The previous bin is strictly in the past relative to the *start* of the current outcome bin. There is no real-time prediction.
- Each public trade and lot count is conserved. Missing, stale, one-sided and crossed book states abstain; no gaps are filled with invented quotes or zero trades. Equal timestamp updates remain separate.
- The quote-to-individual-fill strict join is retained as a **data-quality audit**; same-time events abstain. It is **not** used to select or train the lagged association.

Output includes only by-case anonymized counts, prior-bin pair counts, SHA-256 of the *public-only* projection, a descriptive rho when defined, and a rotated-bin placebo rho. It excludes individual execution rows, book levels, simulator parent-agent IDs and per-order private truth. The rotated placebo **does not preserve market mechanics** and must not be used for p-values or FDR.

## Test, cost and publication contract

The dedicated [`robot-detector-abides-background-nulls.yml`](../../.github/workflows/robot-detector-abides-background-nulls.yml) has:
- A **fast no-ABIDES** preflight: five deterministic tests of exact frozen seed/cohort matrix, missing and duplicate case rejection, public lot/bin bounds, explicit undefined coefficients and strict refusal of identity/accuracy claims.
- One pinned, genuine matching-engine run **per of the six fixed combinations** (not synthetic pre-generated prices or individual actor ground truth).
- Assert public fills and L2 exist, no named execution agents were inserted, no identity or statistical significance fields are claimed, and all accounting conserves counts.
- A seven-day **summary-only** artifact with no private maker/taker IDs, no raw trade tape or user market data.

## Scientific decision rule

Even a large positive rho in *any* background cohort is sufficient to **refute the claim that high public rho uniquely identifies a single VWAP/POV execution program**. Conversely, a low rho in all six simulations **cannot** prove real-world specificity: the sample is extremely small, these are not realistic distributions of every market microstructure regime, and the three cohorts vary several factors simultaneously. A missing/undefined coefficient is not evidence of no bots.

A genuine future detection model would need distinct, market-faithful conditional nulls spanning common liquidity shocks, event ordering, market auctions, feed gaps and independent producers; a pre-registered new feature and parameter-selection protocol; then a completely **new untouched blinded seed and venue/date sample**, with physically identified actor ground truth available only in simulation, not actual public trade tapes.

**Stage-2 scientific release gate CLOSED.** No live alerts, physical bot counts, real-market false alarm probabilities, broker account access, OsEngine/GUI changes or real order placement.
