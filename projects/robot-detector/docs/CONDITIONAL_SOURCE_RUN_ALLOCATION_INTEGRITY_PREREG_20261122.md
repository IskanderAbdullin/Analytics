# Prospective original-run allocation integrity checker (2026-11-22)

Status: **SOURCE-FREE IMPLEMENTATION PREREGISTRATION**, not data allocation, independent evaluation or market release. Addendum to the existing [M0/M1/M2 allocation gate](CONDITIONAL_INTENSITY_ALLOCATION_GATE_20261122.md), which remains unchanged. Existing 3301–3340 and all other known evaluated seeds remain spent, not candidates.

## Before coding

Build a deterministic **manifest integrity checker**, not a detector, model fitter or seed allocator. Its only purpose is to prevent pseudoreplication/leakage when a future, separately approved and frozen source protocol supplies original market-run metadata.

Exactly three split labels: `train`, `calibration`, `evaluation`. Each nonempty split must enumerate **all four** predeclared independent ABIDES-like backgrounds, one source run per scenario for each local seed in that split:
- `poisson_noise_null`
- `fixed_20s_noise_hard_negative`
- `momentum_noise_hard_negative`
- `twap_45s_positive`

Use a public-only immutable metadata record with exactly `source_run_id` (nonempty internal experimental label, not a vendor/broker/order identifier), `seed` (positive exact integer), `scenario` (fixed enum), `tape_fingerprint` (lowercase SHA256-looking 64-hex *public tape* digest). **No raw prints, order IDs, oracle fields or agent IDs.** A source run is one scenario×seed; all analytic phases must share that exact record and stay in its split; phase rows must never be separate allocation units.

The checker must **ABSTAIN/reject** when:
1. A split is empty, a seed has incomplete/duplicated scenarios, or a seed appears across two splits (even for a different scenario).
2. An original source-run ID or public-tape fingerprint is repeated under another allocation record or across splits (replay/non-independence); fingerprints are provisional guards, not source provenance proof.
3. An allocated seed intersects the full **project-local known-spent seed ledger** `research/seed_registry.json`; malformed or missing registry fails closed, not silently treated as empty.
4. Any metadata has unexpected fields, invalid types, invalid fingerprints, invalid cohort name, falsified split keys or duplicate records.

Do not require a fixed number of newly allocated seeds here; even 1 seed per split is a **toy checker fixture**, not a sufficient study, CI-tested independent blind set, statistical power statement or source allocation. The future scientific *source preregistration* must separately establish dates, pinned source revision, global novelty limitations, seed counts and ranges, independent units, observation horizon, quality gates, model freeze SHA, calibration rule, 4× scenario complete reporting and planned confidence intervals **BEFORE** any new source data.

## Planned negative tests

- Complete toy three-split manifest with **fake fixture seed IDs** (not reserved research seeds) accepted for *structural correctness only*.
- Same seed in train and evaluation rejected even if scenario differs; 3 analytic phases of one run cannot be represented as 3 original market runs.
- Same source-run ID or public tape fingerprint across splits or within split rejected.
- Missing hard-negative cohort and repeated scenario rejected; unseen private/oracle fields rejected.
- Known-spent 3301 rejected (and regression checks other ledger seed ranges).
- Nonintegral/bool seed, malformed digest, malformed registry rejected.
- No source data, fresh ABIDES simulations, p-values, owner classification or real FDR.

**Acceptance:** deterministic source-free tests plus exact checked-out Python CI; preserve negative outcomes even if the checker reveals blockers. NEXT_ACTION after implementation: independent scientific power/coverage and source rights design, not generation of attractive seeds or retrospective FDR.