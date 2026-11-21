# Public-book common-market-factor nulls: counterexamples to physical bot attribution

**Research status:** synthetic, deterministic **non-ABIDES** data-generation counterexamples for L2/print association. These are not real exchange data, a market-calibrated conditional-null distribution, a predictive agent detector or evidence that any individual trader owns a specific print.

## Problem demonstrated by previous actual ABIDES tests

The [strict simulated L2 audit](L2_TRADE_CONTEXT.md) found 2,630/2,630 public executions shared timestamps with L2 mutations and were therefore all unassignable to a strictly previous quote *within the timestamp*. The [completed-prior-bin alternative](L2_LAGGED_BIN.md) produced observable pairs, but empirical descriptive rank correlations were **−0.341 null, 0.152 POV, 0.104 VWAP** in one *development* simulator seed. A simple public book/flow correlation cannot be promoted to physical VWAP/POV identity.

A crucial adversarial control asks a different question: **Can a common market-wide latent condition create a high lagged book/print correlation without an identifiable controlled parent order?** If yes, high correlation is not sufficient evidence of one particular robot.

## Explicit synthetic null families (not ABIDES matching engine)

`tools/l2_common_factor_null.py` generates fully anonymous public L2 snapshots and print tuples with a fixed 30-second bin width, 100 public lots and six deliberately separate public print events per populated next-bin. No private actor IDs are created and no broker API is called.

- **common_factor:** the book depth balance in completed bin t−1 and the aggregate public buy fraction in bin t respond to the same shuffled common latent market state. A high correlation is *built into public market conditions*, **not** caused by a single identified trading program.
- **independent_flow:** previous-book public state and subsequent aggregate buy fractions follow independent shuffled state orders; this tests that high correlation is not a guaranteed mathematical artifact of the interface.
- **market_wide_shock:** a group-wide persistent directional regime jump affects both public book and later public trade mixture across **many anonymized prints**; a shift is not attributable to one owner.
- **synchronized_clock:** public quote mutations and fills receive the *exact same exchange timestamp*; event-level quote/fill alignment must abstain while a previous-*completed*-bin public observation can still be computed without guessing event sequence.

The per-bin public sums and the multiset of public print sizes and sides are known from this transparent generator, not hidden actor information. These controls are educational *structural counterexamples*, not realistic conditional resamples preserving all market-book mechanics and not proofs about independent human actors. In particular, the common latent state is intentionally **constructed** to create correlation; the experiment cannot estimate how frequently such correlation arises in the real market.

## Outputs and tests

The read-only CLI:

```bash
python -m unittest discover -s tests_l2 -p 'test_l2_common_factor_null.py' -v
python tools/l2_common_factor_null.py --seed 1701 --bins 24 \
  --output /tmp/l2-public-common-market-nulls.json
```

The output records only generated counts, descriptive observed Spearman coefficients, the same-time abstention count and caveats. It refuses overwriting an existing research artifact. `tests_l2/test_l2_common_factor_null.py` contains five pure-Python tests for deterministic generation, strong common-factor/shock correlation with no named parent, full print/lot conservation, lag-versus-exact-timestamp behavior, private identity absence and invalid arguments.

The **dedicated lightweight [public-null CI workflow](../../.github/workflows/robot-detector-public-l2-nulls.yml)** installs only Python, without ABIDES or .NET; its seven-day artifact contains aggregate summaries, no private labels or raw market data. This avoids unnecessary simulation minutes and does not retrain any previous model.

## Verified deterministic counterexamples (2026-11-21)

[Successful lightweight Python CI #44896188923](https://github.com/IskanderAbdullin/Analytics/actions/runs/44896188923) executed **5/5 new unit tests** and the committed synthetic public-generator script at seed 1701, 24 thirty-second bins, 144 anonymous prints and 2,400 lots per scenario.

| Generated public market scenario | Spearman: previous public L2 depth imbalance → later BUY share | Rotated-bin placebo rho | Exact-time strict-join abstentions |
|---|---:|---:|---:|
| **Common market factor** | **1.000** | −0.263 | 0 |
| Independently shuffled next-bin flow | −0.195 | 0.330 | 0 |
| **Market-wide synchronized directional shock** | **1.000** | −1.000 | 0 |
| **Synchronized quote/trade clock** | **1.000** | −0.263 | **144/144** |

These are **deliberately constructed** correlations in synthetic anonymous public streams. The generator constructs **no named parent execution agent** and has no actual actor identity. A perfect `rho=1` is therefore **not sufficient evidence** of a particular market-making or execution robot; any classifier declaring one from that feature alone would make an unjustified identity claim. The clock-synchronized case shows that all exact-event quote/print comparisons may be undefined while the earlier completed-bin aggregate correlation remains perfectly defined.

**Crucial limitation:** A generator that fixes a shared latent factor to make two variables perfectly monotone is an **illustrative logical counterexample, not a probability estimate**. It is *not* independent market evidence, does not establish typical false-positive frequency, and cannot validate real exchange specificity. The rotated-bin placebo likewise is not a realistic conditional-null distribution.

## Methodological decision

A strong past-book/next-prints correlation, even if reproduced, cannot establish a physical trading robot if many anonymous participants share market conditions. Real market specificity would require well-validated source-conditional nulls preserving order-book updates, execution timing, spread/queue constraints, cross-instrument regime shocks, feed coverage and selection of multiple windows/features. The present four generated scenarios are **not sufficient** for that purpose.

All previous ABIDES seeds 41–44, 61–63, 71–73, 901–904, 1101–1104, 1301–1304, 1401 and 1501 remain **spent**. No tuning using these results as fresh blind holdouts, no live bot alert or order, no OsEngine runtime change, no GUI/Computer Use. Stage-2 scientific release gate CLOSED.
