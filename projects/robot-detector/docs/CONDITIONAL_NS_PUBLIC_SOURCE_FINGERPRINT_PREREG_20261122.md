# Prospective exact-ns public source provenance binding and replay guard (2026-11-22)

**SOURCE-FREE DESIGN FROZEN BEFORE COUNTEREXAMPLE / CODE.** Previous complete public type4→post-event causal M1-v3→LL integration passed 230 synthetic Python source-free tests; it checks equality of paired source book snapshots, but equal book snapshots alone do **NOT** establish that evaluated trade events originated from the same actual source. This potential false-confidence provenance gap must be falsified rather than described as fully solved. No actual vendor source, independent holdout, seed allocation, market FDR or owner labels.

## Precommitted adversarial hypothesis

Two different public message histories may have **identical post-event BBO snapshot timestamps and prices** but different event types at those exact times (e.g. an execution in one history becomes a delete in the other), hence different visible trade intensity. The old integrated helper can legitimately score either history with the same book tuple because it lacks a cryptographically bound source event-type fingerprint. That does not indicate a model algorithmic failure; it means **same books != same source tape**. Document this negative before repair.

## New structural-only binding

- Input for binding: same **strict synthetic public-only** paired source rows allowed by the earlier type4 projection (timestamp ns, event_type, resting_side, top bid/ask, complete) plus safe local original run label (ASCII alphanumeric/dot/underscore/hyphen, 1..128 chars, not a vendor order/account ID). Source precision exact1ns, true asserted continuity, literal exchange-local ns unit.
- Hash ALL ORIGINAL public message rows, including event type, resting side and POST-event BBO, in strict chronological source order, using deterministic canonical JSON, SHA-256, a fixed schema-version domain separator. The full canonical serialized row sequence is **never output**; only an in-memory sha256 fingerprint and safe counts may be used by a protected bound evaluation object.
- BoundSource object contains internal public projection, run_id and exact lowercase sha256 public-only digest; BoundEvaluation binds a separate NsEvaluationWindow and explicit expected run_id and expected digest. At scoring, require exact run ID and digest equality **and** the same projection BBO tuple, source clock unit, complete external source assertions and train/eval run ID exclusion; else ABSTAIN. Earlier M1-v3 lag and LL frozen.
- A structural-only registry guard sees a bounded set of bound sources and rejects duplicate run_id even under different source content, and duplicate public fingerprint even under different IDs (replays/phase aliases); it cannot certify globally independent source worlds, cryptographic source authenticity, rights, or actual market owner truth.
- Never print full vendor source messages, book rows, order reference IDs, real agent IDs or a secret; only minimal aggregate status, source count and explicit unknown market owner/FDR flags. Hash equality is *not* proof of independent source provenance, since unsourced public input could be forged.

## Fixed negative/positive tests before running

1. The frozen five-message source-free history A has two visible type4 executions at the same exact timestamp; construct B changing one visible type4 at that timestamp to type2 delete while leaving **every BBO timestamp and price identical**. Require same BBO tuple, different projected visible count and different public SHA. Demonstrate old book-only matching cannot distinguish identity (negative finding), then assert new cross-bound scoring rejects B with A's expected digest.
2. A correctly bound source/run/time/digest is scored using already frozen train-only M1-v3 and prior LL; expected integral 2.875, LL=log(.75)-2.875, one distinct visible cluster, two visible type4 execution rows.
3. Tampered source digest, mismatched run labels, even if books identical, mixed exchange ns/millisecond unit, bad source continuity, train/eval original run ID overlap all ABSTAIN.
4. Duplicate original source ID with distinct digest and replayed source digest with different IDs reject within structural registry. No automatic seed novelty claim, no globally unique proof.
5. One-nanosecond difference in valid visible source row must alter fingerprint; an exact duplicate row retained changes its fingerprint but public time-cluster count remains one; source layout is not inferred physical owner count.
6. Mismatched source credentials/vendor account/order/agent fields fail source-free adapter, no raw serialized row output, no market FDR/pvalue.
7. Exact cheap public Python tests and full audit, no genuine ABIDES or vendor data acquisition. If any limitation cannot be repaired without original third-party authenticated source metadata, mark BLOCKED and retain the counterexample.

**NEXT_ACTION:** implement structural source binding and adversarial book-identical/event-type-different public-history test; then assess whether future independent original source provenance manifest needs externally signed checksum, license, temporal split and source-revision pin. Do not call the structural hash global source authenticity.
