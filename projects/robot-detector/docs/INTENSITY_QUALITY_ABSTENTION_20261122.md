# Candidate C: precision and causal-L2 abstention wrapper (source-free, 2026-11-22)

**Pre-test freeze:** [issue #97 comment 7075657012](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075657012).
This is a **separate conservative engineering quality gate**, not a retuning
of 500ms candidate C, new source calibration or a claim about an exchange
timestamp specification. It must not be confused with verifying
probabilistic validity of C.

\`quality_gated_intensity_sample\` calls the strict previous-only L2
observation gate and returns a toy conditional C sample **only if**:
- public print timestamps are integers in milliseconds with **declared
  \`source_precision_ms == 1\`**. Unknown, noninteger, 0, 10ms, 100ms and
  Boolean precisions **ABSTAIN** as \`UNSUPPORTED_OR_UNKNOWN_PRINT_PRECISION\`;
- at least two distinct public timestamps provide a gap;
- every unique print has a validated local strict earlier L2 snapshot
  under the existing 1000ms age limit, with no newer precision-overlapping
  update or conflicting same-time coverage;
- public snapshot dictionaries have the preexisting exact field allowlist,
  rejecting \`agent_id\` and other private/oracle metadata.

On coarse/unknown precision, local-L2 quality ABSTAIN, missing L2 or a
single unique timestamp, no samples are produced. No real exchange-wide
sequence completeness is established, even if local observation is eligible:
\`exchange_completeness=UNKNOWN\` always.

Four source-free adversarial test groups fixed before coding cover:
1. Good two-print toy tape + previous-only 1ms covered snapshots for each
   of 64 fixed replicates, preserving 500ms occupancy and replay.
2. Seven invalid/unknown/coarse precision types, no samples.
3. Missing and overlapping-precision L2, private field failure.
4. Single unique timestamp and invalid Boolean replicate fail closed.

The four source-equivalent tests passed locally (4/4, not exact checkout).
New exact GitHub CI **PENDING** for this commit; do not claim successful
GitHub run until verified. Original previous-only bug repair is independently
tested by preceding [CI #44996216864](https://github.com/IskanderAbdullin/Analytics/actions/runs/44996216864).

The 1ms condition is a **conservative development eligibility assumption**,
not independently validated real feed quality. Passing it cannot establish
market p-values, physical owners, real-market FDR or a calibrated timing
null. A future external source needs an independently validated source
precision and coverage contract before any inferential statement.

NEXT_ACTION: verify exact committed wrapper tests in cheap CI and preserve
all abstentions. Then compare a nontrivial dependence-preserving public timing
null with stronger adversarial burst and periodic controls without using
already inspected 3301–3340 ABIDES seeds as blind data.
