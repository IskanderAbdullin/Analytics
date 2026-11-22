# RD-PUBLIC-CONDITIONAL-NULL-16 — burst-preserving timing null: preregistration and falsification gate

Status: **METHOD DEVELOPMENT ONLY; NOT CALIBRATED**. Date: 2026-11-22. No new source data or simulation seed was examined to set this protocol. This document does not supersede any frozen ABIDES protocol.

## Observable and estimand

Input is a public, sorted sequence of exchange timestamps, clustered at *exactly identical* reported timestamp values. Cluster size is recorded for robustness but never interpreted as a parent order or physical owner. The seven descriptive candidate periods remain the previously registered 5, 10, 15, 20, 30, 45, 60 seconds, tolerance ±50 ms. Report all seven, including negatives; no best-only significance. The descriptive statistic is the count and fraction of adjacent **unique timestamp** gaps within tolerance of each period, together with eligible-gap denominator. A zero denominator requires abstention. The previous-only L2 gate is independent and must be applied before claiming a valid L2-conditioned observation.

## Proposed conditional randomization (unvalidated)

Predeclare a fixed UTC time grid of 60-second blocks, with each block divided into twelve 5-second cells. For each cell, retain its observed number of unique event timestamps and the ordered vector of simultaneous print-cluster sizes. Conditional on these cell counts, sample event times **uniformly inside their original cell**, then sort within each cell. Attach the cluster-size vector by original within-cell order; do not split clusters, and never move a cluster to another cell. Use deterministic RNG streams derived from a preregistered seed and replicate index, with no private agent labels or future L2 in features. For a given candidate period, compare the observed statistic to the distribution across *all* replicates; if the number of unique events is less than two, abstain. Predeclare at least 999 replicates before any independent prospective evaluation. This conditional model assumes exchangeability **within each 5-second cell**. It preserves coarse occupancy and cluster multiplicity but **does not preserve sub-5-second bursts, order-flow autocorrelation, market impact, or event-time Hawkes dependence**. Consequently its randomization distribution is not a justified market p-value unless the exchangeability assumption survives independent falsification. In the present stage report only sensitivity diagnostics, not p-values or FDR.

## Mandatory falsification suite before use

1. Split-fill invariance: duplicating prints at an existing timestamp changes neither unique-event cadence nor cell occupancy.
2. Local occupancy preservation: exact event counts per 5-second cell and full multiset of cluster sizes per cell remain invariant in every randomized replicate.
3. Nontrivial randomization: a cell with at least two distinct admissible times must not produce an unchanged interarrival vector in all replicates; a fixed-timestamp cluster-size permutation alone is rejected.
4. No artificial cross-cell transfer, negative timestamps, duplicate output clusters, or future/at-time L2 eligibility.
5. A constructed unrelated periodic background at 5, 10, 15, 20, 30, 45 or 60 seconds must be reported as a **hard negative for actor attribution**, even if its cadence score is perfect.
6. A constructed self-exciting momentum burst with nonuniform within-cell intensity must expose exchangeability failure; do not call it a controlled null success.
7. The same public tape with two different hypothetical private owner allocations must produce exactly the same public score; owner inference is nonidentifiable.
8. Test low counts, timestamp quantization, missing intervals, time-zone boundary, and incomplete L2: abstain or explicitly warn, never silently impute.

## Decision gate

Before running any new ABIDES seed or external feed, implement this as a deterministic source-free diagnostic with adversarial tests. Compare with a separate **block-resampling alternative preserving within-cell relative offsets** (which may preserve target cadence and hence have no power); explicitly document the power-versus-validity tradeoff. Do not choose 5-second cells, seed, period, tolerance or threshold by looking at 3301–3340 again. A future, independent preregistered source-holdout protocol is required for any inferential claim. Negative outcomes remain part of the release record.

NEXT_ACTION: implement the 5-second conditional sampler and invariance/falsification tests, run cheap source-free CI, then audit the exchangeability failure on constructed clustered and self-exciting backgrounds. No new p-values, source seeds, real-market FDR, or physical-owner claims.
