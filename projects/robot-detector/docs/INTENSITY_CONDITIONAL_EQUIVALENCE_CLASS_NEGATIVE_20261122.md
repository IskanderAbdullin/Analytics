# Exact 500ms occupancy equivalence-class counterexample (2026-11-22)

**Pre-test registration:** [issue #97 comment 7075610380](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075610380) recorded the paired construction, 64 replicate indices, seed 404, <=10ms adjacent-unique-gap metric and anticipated invariants **before** writing the new test. The previously frozen [500ms protocol](INTENSITY_CONDITIONED_NULL_PREREG_20261122.md) remains unchanged.

## Paired source-free public timestamp tapes

- **Dense burst (milliseconds):** \`[100,101,102,103,1000,1001,1002,1003]\`.
- **Dispersed within the same two 500ms subcells:** \`[100,225,350,475,1000,1125,1250,1375]\`.
- Both have exactly 4 unique events in UTC subcell [0,500), 4 in [1000,1500), and identical split-print multiplicity vectors (all ones). A separate matched duplicated-first-print fixture tests multiplicities [3,1,1,1] per subcell. No actor identity or independent market source exists in the construction.

The original dense tape has **6** adjacent unique timestamp gaps <=10ms within 5s cells, the dispersed one **0**. For each of 64 fixed replicates (seed 404), candidate C's 500ms-occupancy-preserving sampler returns an **identical sampled tape for both inputs**. The weaker A sampler does likewise. B's rigid offset translation keeps each input's original short-gap score (6 or 0) by design, thus sacrifices power to distinguish other temporal explanations.

**Proof by code structure:** Candidate C groups original unique timestamps by \`floor(t/500)\`, draws a fresh uniform sample of occupied millisecond slots in each such subcell with deterministic RNG (same seed and replicate), and assigns each original split-print multiplicity in chronological rank. No variable involving original within-subcell gaps enters the resampling law. Consequently, for two inputs sharing per-subcell occupancy and rank-multiplicity vectors, the conditional sampling mapping is identical **by construction**. This is a precisely limited structural impossibility to condition on the within-subcell gap pattern, **not** a demonstration that any real trading source must follow one process.

**Timestamp precision stress:** Flooring the dense tape to 10ms preserves eight public print rows but collapses eight distinct 1ms timestamps into two unique timestamps; the short-gap score falls from 6 to 0. A feed without known reliable precision or prior-only L2 should ABSTAIN for causal inference; apparent cluster size cannot identify a parent order or real owner.

## Checks, limits, next decision

Four deterministic adversarial unit tests evaluate the frozen pair, all 64 A/B/C replicates, matched duplicate prints and 10ms quantization. These passed **4/4 on source-equivalent locally transcribed code**, without a complete checkout. Exact committed GitHub CI must confirm them before labeling the source tests VERIFIED.

No p-value, market randomization-exchangeability theorem, external source run, new holdout seed, owner count, real-market FDR, or actual trading operation is asserted.

NEXT_ACTION: verify the exact committed CI and negative tests; then prospectively compare at least one genuinely dependence-preserving, nontrivial conditional model whose support is wider than B's rigid shift, with a clearly stated untestable exchangeability assumption; verify previous-only L2 coverage and precision abstentions on controlled missing-data examples. Never tune the frozen 500ms width on these observed development controls.
