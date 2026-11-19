# Beyond the periodic-cadence detector: simpler, independently testable research paths

Created 2026-11-19. This design memo is intended to prevent over-optimizing the original clock-regularity algorithm. The scientific release gate is unchanged: **no calibrated actual-robot count and no profitable next-print forecast have been demonstrated**.

## Why reconsider the approach?

On SBER Nov 12/13, the original periodic detector had **14/983** forward matches, exactly the same as its half-period shifted placebo. A historical-only recency filter restricted candidate forecasts to **2/167** on untouched Nov 5/6 (no hits). A new varied-quantity periodicity detector found **7** candidates on MOEX Nov 3 but only **1** on Nov 2 under different tape density, while skipping two dense groups under the earlier build. Improving coverage alone is not expected to solve scientific non-identifiability.

**The goal should be to identify an observable signature with predictive or descriptive validity**, not to force every public print into an inferred robot count.

## Parallel alternatives, from simplest to hardest

### A. Transparent trade-flow footprint (first new implementation)

Use only prints from the public read-only tape, no unknown parent/order IDs. Within bounded clock-time windows by instrument/source/session, output:

1. **Trade count, total lots, BUY/SELL lots and signed imbalance** `(BUY lots - SELL lots) / total lots`. If the provider's DIRECTION semantics are not verified as aggressor side, label it *reported-direction imbalance*, not dealer aggression.
2. **Inter-arrival interval distribution** (median and coefficient of variation). Marketwide self-exciting bursts can create repetitive prints with no fixed execution plan.
3. **Dispersion of print counts (Fano factor)** in 1s/10s time bins: `sample variance(counts)/mean(counts)`. Values >1 are compatible with clustering, **not** diagnostic of bots; the bin width and feed gaps matter.
4. **Run-length persistence of reported trade direction**: longest same-direction run and lag-1 sign agreement, only if BUY/SELL semantics present. Both can reflect market conditions and splitting, not one identified agent.
5. **Clock phase concentration**: number of prints within 100ms after an integer UTC second, versus number of *observed* active bins. Compare against a data-preserving null to avoid mistaking exchange activity regularity for several traders.
6. Explicit missing input and `coverageVerified=false`; metadata, per-source isolation, and warnings for unreliable signs.

Deliver this as a simple CLI `flow-footprint` and JSON time-window metrics, with synthetic exact tests. This baseline is **descriptive**, inexpensive, and useful even if no timed strategy can be identified; it can become an optional dashboard panel later.

### B. Simple observable "activity episodes" (second implementation candidate)

On 10-second time buckets, find **long intervals of unusually high volume and sustained same-reported-side imbalance** relative to a local median/MAD reference and a minimum count. Use a state machine `quiet -> active -> quiet` with start/end timestamp, total lots and drawdown to baseline. Do not call an episode a bot. Evaluate stability under time-of-day controls and known scheduled auctions. This can be simpler and more robust than searching thousands of potential cadence periods.

An episode likely reflects many participants and reacts to market conditions; **does not** solve attribution. Fast O(N) streaming update makes it a practical candidate for a free live monitor.

### C. Book-side quote oscillation and replenishment (separate L2 signal)

The existing experimental best-quote diagnostic can measure repeated touch/cancel-like oscillations and order-book imbalance. Aggregated **L2** does not expose individual order IDs, so it cannot reliably classify iceberg orders, spoofing, or who placed/cancelled. Use *"quote replenishment-like"* and mark gap/coverage.

Implement only after verified historical/replay book snapshots for the relevant MOEX/SPB instrument; never reconstruct order cancellations from trades alone.

### D. Metaorder sequence model / variable TWAP, later

Use run persistence, price response, clip-size trajectories and change-point segmentation. HMM/Bayesian/ABIDES-like hidden parent order assumptions are model-dependent and expensive. Validate first on simulator data with known ground-truth agents, not just unlabeled public prints.

### E. Explicitly reject unobservable bot counts

The number of physically distinct running programs is not identifiable from public anonymous trades alone. In particular, one algorithm can generate many streams, and several programs can produce one indistinguishable stream. Report observed **episodes/footprints/candidate sequences** only.

## Source references and transferable ideas

Academic:

- Muravyev et al., *Does trade clustering reduce trading costs? Evidence from periodicity in algorithmic trading* (Financial Management 2022): **1-second timing and round-second bursts can be common market structure**, not evidence of unique owners. https://doi.org/10.1111/fima.12405
- *Periodicity of trading activity in foreign exchange markets* (Journal of Financial Research 2022): trading can cluster at beginnings of minutes in many FX pairs, so a 60-second time signature requires venue and activity controls. https://doi.org/10.1111/jfir.12280
- Lillo, Mike & Farmer, *Theory for Long Memory in Supply and Demand* (2005): persistent signed flow can arise from order splitting; informative **aggregate behaviour**, but not a public owner label. https://doi.org/10.1103/PhysRevE.71.066122
- Cont, Kukanov & Stoikov, *The Price Impact of Order Book Events*: **OFI** requires order-book event changes and should not be conflated with the reported-side imbalance computed only from prints. https://arxiv.org/abs/1011.6402

Open implementations to inspect selectively (technical examples, not validated MOEX accuracy claims):

- https://github.com/twowaymind/orderflow-metrics — dependency-free order-flow imbalance, signed trade classification, bar construction, execution/impact metrics; **port ideas**, avoid calling raw print imbalance OFI.
- https://github.com/cyrustang147/Microstructure-Bars — time/volume/order-flow bars and elementary lag-1 autocorrelation for a simple baseline; read implementation to inform tests.
- https://github.com/Tworasos/tape-and-book — public order book/trade features plus honest tests of whether the observations predict anything. Data source differs from T-Invest and is not an immediate adapter.
- https://github.com/purunjay-bhardwaj/market-microstructure-analyzer — simple spread/imbalance anomaly examples and charts with synthetic inputs. Does not identify algorithm owners.
- https://github.com/alimekawi9/sentinel-trade-surveillance — labeled synthetic surveillance and time-window evaluation, but it has privileged simulated trader labels unavailable from T-Invest public trades.
- https://github.com/chirindaopensource/detecting_unusual_trading_patterns_on_cryptocurrency_exchanges — entropy/ACF/change-point replication; heavier methods suited for a later research step, not the first production baseline.
- https://github.com/GabrieleDiCorato/abides-ng — known-agent execution simulation for controlled blind truth; must project down to exactly the fields available from our anonymous public tape before assessing recoverability.

## Comparative experiment requirements

For identical instrument/day/source and a **frozen** time partition, run fixed-q cadence, variable-q cadence and simple trade-flow footprints side by side. The third method has **no candidate bot count**; compare its coverage, runtime, consistency across dates and any independently observed future behaviour. Keep a clean negative control for every strategy and record skipped groups separately. When a method fails a future-data test, document the failure and **don't promote it to live signals**.

Next implementation order:
1. Finish and verify bounded dense-window segmentation in PR #13; source streams cannot be silently omitted.
2. Implement simple `flow-footprint` read-only C# Core + CLI + deterministic tests with no dependencies.
3. Add 10-second burst episode output (only after baseline stats are demonstrably correct).
4. Recheck on additional instruments and dates without model fitting on evaluation data.
5. Later consider quote-replenishment and live gRPC **read-only** ingestion, subject to source completeness and attribution limits.

**This document is a design plan, not a claim those future modules have already been implemented.**
