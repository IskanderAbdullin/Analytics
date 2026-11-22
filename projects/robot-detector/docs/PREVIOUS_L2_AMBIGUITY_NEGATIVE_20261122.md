# Previous-only L2 snapshot ambiguity: source-free negative controls (2026-11-22)

**Frozen pre-test design:** [issue #97 prereg comment 7075629666](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075629666).
Method: [public_period_l2_gate.py](../tools/public_period_l2_gate.py). No private
source data, synthetic agent IDs, inferred real owners, p-values or market FDR.

## Failure modes and code fix

Prior implementation accepted the latest *strictly eligible* L2 quote, ignoring
a more recently observed ambiguous sample whose reported timestamp precision
overlaps the public print. A previously covered older book therefore could
incorrectly license a descriptive result, despite a known intervening update
with unresolved causal order. The correct conservative interpretation of this
particular observed sample sequence is **ABSTAIN**, not an implied absence of
the unresolved update.

Second, conflicting same-time L2 snapshots with opposing \`covered\` flags
could produce a different result when input order was reversed. Tied
snapshots in this context do not give a trustworthy deterministic order.

The revised local gate retains its preexisting 1000ms max-age parameter,
strict public-only field allowlist and status \`exchange_completeness=UNKNOWN\`.
When a known newer observed quote overlaps the print under its timestamp
precision, reason \`AMBIGUOUS_NEWER_L2_ORDER\` is reported; conflicting
latest exact-time snapshots report
\`CONFLICTING_TIED_L2_SNAPSHOTS\`. Both fail closed. Exact duplicate
same-time covered records and future-only snapshots do not change an otherwise
valid local observation. These are **conservative engineering eligibility
decisions**, not independent proof of exchange event completeness or causal
identification of any participant.

## Frozen source-free falsification matrix

1. Prints [1000, 2000]ms, strictly older covered 900/1900ms and newer
   ambiguous 999/1999ms precision 2ms -> 2×
   \`AMBIGUOUS_NEWER_L2_ORDER\`, ABSTAIN.
2. Tied 900/1900ms samples with conflicting covered True/False -> 2×
   \`CONFLICTING_TIED_L2_SNAPSHOTS\`, ABSTAIN for all four permutations.
3. Exact duplicate covered snapshots plus later future quote ->
   \`ELIGIBLE_LOCAL_OBSERVATION_ONLY\`, exchange completeness still UNKNOWN.
4. Latest observed eligible uncovered quote -> coverage ABSTAIN;
   private/oracle fields -> fail closed \`ValueError\`.

Existing source-free eight prior-L2 regression cases must remain green.
Local **source-equivalent** transcription of four new plus eight original
cases passed **12/12**; this is not an exact checked-out GitHub test.
The newly committed workflow adds explicit discovery and must independently
confirm the tests before a VERIFIED status is claimed.

No source seeds, previous frozen precision threshold, 500ms null or
historical ABIDES results are changed.

**NEXT_ACTION:** verify exact HEAD cheap CI and confirm all 12 prior/new
L2 tests, then investigate missing-feed completeness and coarsened precision
abstention in a prospectively frozen controlled experiment. Retain all
negative outcomes and keep master issue #72 open.
