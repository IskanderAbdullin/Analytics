# Completed-bin L2 imbalance and next-bin public print flow

**Status:** purely descriptive, public-only ABIDES research. This is neither a VWAP/POV classifier nor a real-market trading signal. No parent-order attribution or physical actor identification is attempted.

## Scientific motivation: strictly same-time joins were unidentifiable

The [verified strict L2-to-fill audit](L2_TRADE_CONTEXT.md) found that **all 2,630 simulated executions** across agent-free, POV and VWAP runs shared timestamps with one or more L2 book updates. It correctly abstained on every single within-timestamp quote/print match; selecting a same-time quote by row index would impose an unjustified order.

The next defensible public feature uses only the **last observed book state in the completed previous clock bin** as a lagged exposure for the **aggregate reported directional flow in the subsequent bin**. This avoids *intra-bin same-time causal assignment*, at the cost of coarser time resolution and without any proof of actual market participant behavior.

## Source and data contract

`tools/lagged_l2_bin.py` accepts one symbol's genuine ABIDES `L2Snapshots` and already **anonymous** `PublicExecution` tuples (time, price, size, public reported aggressive direction). The original ABIDES maker/taker IDs are never passed into this function. Source grouping across actual brokers/instruments is **not implemented**: do not concatenate multiple symbols, sessions, venues or source clocks and claim isolation. This study only receives one symbol `ABM` at a time.

Fixed UTC bins of `bin_seconds=30` are computed in simulator nanoseconds. For a populated executed-trade bin `t`:

- Only snapshot updates from *exactly* bin `t-1` can provide the reference, not a current/future quote. The **last** L2 update in the completed previous bin is used, preserving the original book stream's event order including repeated timestamps. As it is in an **earlier** clock bin, same-time quote/execution ordering within the current bin is irrelevant.
- The prior book must be two-sided, unlocked/uncrossed, and no more than the configured age at the *opening of bin t*. By default the maximum is 30 s; no market data completeness is assumed from an unverified tape.
- The depth-five public book imbalance is `I_(t-1) = (sum_bid_lots - sum_ask_lots)/(sum_bid_lots + sum_ask_lots)`. This uses **only past completed public L2 state**.
- The *outcome* is the completed current bin's public reported BUY fraction `R_t = BUY_lots_t/(BUY_lots_t + SELL_lots_t)`. The current-bin outcome is **not available before bin t ends**, and is **never a predictor at the start of t**.
- When at least five eligible paired bins have nonconstant ranks, the module reports descriptive tie-aware Spearman rank correlation between `I_(t-1)` and `R_t`. Otherwise it is `null`, not a claim of no effect or 0 probability. Every populated trade bin is either eligible or explicitly abstains for previous-book absence, age, empty/one-sided or locked/crossed quote.

This is a **retrospective exposure/outcome association**. It does not tell which participant initiated the print, whether displayed book imbalance caused the trade, or whether a hidden parent order existed.

## Genuine ABIDES output — public-only exploratory evidence

The [successful isolated L2 CI #44895877902](https://github.com/IskanderAbdullin/Analytics/actions/runs/44895877902) ran **15 pure-Python integrity tests**, including the six new lagged-window checks, followed by actual exchange simulations for each public null/POV/VWAP mode using the already **spent development seed 1501** and unchanged 30-second bins.

| Simulated market mode | Current-bin observations with valid previous-bin L2 | Spearman(previous depth-five imbalance, next reported BUY fraction) | Rotated-bin placebo Spearman |
|---|---:|---:|---:|
| Agent-free background | **13** | **−0.341** | 0.159 |
| POV | **10** | **0.152** | 0.115 |
| VWAP | **13** | **0.104** | 0.247 |

The original exact-timestamp per-fill join still **abstained on every executed print**: 917/917 background, 797/797 POV and 916/916 VWAP. However, the separate previous-*completed*-bin approach did yield **10–13** chronological public quote/flow pairs per mode. This validates the **data extraction and timing method**, not the usefulness of the correlation as an execution identifier.

The small observed correlations **do not reliably discriminate** the controlled execution modes from the agent-free simulated background. Note the rotated-bin control is not a market-conditional valid null or a calibrated significance test. The sample is small, the three simulator economies are not exact causal counterfactuals, and `rho` is not TP/FP/FN for a private parent order. **Do not select a correlation threshold from these now-spent observations.**

## Controls and limitations

- The existing true **agent-free background** simulated market, plus separate POV/VWAP synthetic controlled-execution runs, are included as exploratory contrasts. A high correlation in background means the feature is not discriminative.
- A second descriptive placebo rotates entire **completed-bin reported BUY shares** across the original eligible clock times, preserving the set of outcomes and observed reference book imbalances. This intentionally breaks alignment; it is **NOT** a market-preserving conditional null, does not preserve realistic book/price reaction, and cannot support any false discovery probability, confidence interval or p-value.
- Correlation can result from market-wide directional shocks, liquidity self-selection, persistent market imbalance and simulated exchange algorithms other than the explicitly controlled agent. There is **no synthetic owner/parent-order ground-truth scoring** in this module because it does not output individual order attributions.
- The synthetic single-symbol ABIDES event sequence is not equivalent to a verified L2 broker feed with reliable per-event sequence IDs, cross-source receipt timestamps and archive completeness. A real market data collection protocol is required before using this on actual MOEX/SPB archives.
- The earlier seed 1501 has already been **spent** in the strict-join exploratory study, and is used here only for development of this *different* public observable. It is **not held-out evaluation**. Any future model changes require untouched seeds committed before scoring and independent market sessions.
- **Stage-2 research release gate remains CLOSED.** No real broker order, GUI, account access, or physical robot count.

## Tests and actual simulation

Six standalone tests in `tests_l2/test_lagged_l2_bin.py` cover exact known previous-bin rank association, missing quote bins without zero-imputation, strict age, nonrevisable past observations when future quotes arrive, preservation of equal-time previous-bin snapshot order, constant-background correlation abstention and malformed input rejection.

The existing [isolated L2 feasibility GitHub Actions workflow](../../.github/workflows/robot-detector-l2-feasibility.yml) runs these pure tests and three genuine ABIDES matching-engine modes (null, POV, VWAP) on a 10-minute developmental seed; it calculates both the strict-event abstention audit and this completed-bin view from the **same generated public tapes**. It checks event/lot conservation, lagged exposure timestamps, missing-bin accounting, no private agent IDs and the explicit absence of market significance claims. Only aggregates and per-bin public summaries are uploaded, no private truth or raw L2 event logs.

Reproduce from `projects/robot-detector` on the isolated Python 3.12 ABIDES runner:

```bash
python -m unittest discover -s tests_l2 -p 'test_*.py' -v
python tools/l2_trade_context.py --seed 1501 --output /tmp/public-l2-study.json
```

Output is immutable-once-created. Quote/fill data in this study must not be interpreted as a source of individual trading account activity.
