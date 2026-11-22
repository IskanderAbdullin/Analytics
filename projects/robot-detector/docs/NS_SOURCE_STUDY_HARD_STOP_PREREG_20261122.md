# Prospective source-study hard-stop evidence gate (2026-11-22)

**SOURCE-FREE PREIMPLEMENTATION FREEZE**. New *planning eligibility checker* prevents a future agent from reading green source-free CI as permission for new original ABIDES seeds, vendor acquisition, independent evaluation or scientific release. This checker is NOT a source license checker, automated source authenticator, execution approval, substitute for reading source terms or market FDR validation.

## Fixed schema and outcomes

Input exactly one dict containing source_family, study_phase and 9 evidence states:
- source_family one of "ABIDES_SIMULATOR", "LOBSTER_PUBLIC_DEMO", "BINANCE_TRADE_ONLY", "COINBASE_MARKET_DATA", "MOEX_ISS_HISTORY"
- study_phase exactly "INDEPENDENT_SOURCE_STUDY" or "REAL_MARKET_RELEASE"
- evidence keys exactly "provider_research_rights", "immutable_source_revision", "unit_safe_source_clock", "trade_event_definition", "exchange_event_completeness", "causal_l2_coverage", "original_world_train_cal_eval_split", "power_and_resource_adequacy", "frozen_models_and_thresholds".
- Each evidence value exactly "UNKNOWN", "FAILED" or "DOCUMENTED_EXTERNAL" (case sensitive), no bool or raw vendor identifiers, arbitrary extra fields or missing dimensions; preserve all 9 dimensions unabridged even for early failure.

The checker must always report "NOT_AUTHORIZED_FOR_SOURCE_EXECUTION": it is impossible to grant actual vendor/research/trading access from a self-declared JSON document. Its independent research planning classification is either "BLOCKED_EVIDENCE" if any state != DOCUMENTED_EXTERNAL, or "STRUCTURAL_EVIDENCE_DOCUMENTED_EXTERNAL_REVIEW_STILL_REQUIRED" if all 9 are claimed DOCUMENTED_EXTERNAL. A positive result does NOT certify authenticity or permit original data workflows or market FDR. Never let self-declared flags imply user authorization.

Source-specific hard stops:
- Public Binance trade-only historical ZIP has no corresponding synchronized L2 coverage in existing work: no source M1-v3 L2 evaluation permitted.
- Coinbase Market Data Terms 2026-08-07 clause 3(5): algorithm development/validation access without express written permission blocked. Self-reported rights flags do not override this prohibition or legal approval.
- Real market release always has no independently verified physical owner ground truth in this project, and remains BLOCKED regardless of 9 structural fields. A model is only a pattern detector, NOT a physical owner detector.
- Original historical LOBSTER 2012 public DEMO does not certify full exchange-event capture, and its type4-only ns precision and trade-only millisecond collision count remain unmeasured. All-source message 110818 collision figure must not be labelled a trade-only value.
- ABIDES simulation synthetic oracle cannot establish real-market FDR and spent seeds cannot be rebranded fresh; any original new study requires independent source-world provenance and pre-source power/resource freeze.

Default frozen negative fixtures:
1. All UNKNOWN ABIDES planning -> BLOCKED 9 prerequisites, execution=False, no owner/FDR.
2. One FAILED in otherwise DOCUMENTED_EXTERNAL -> BLOCKED and that failure exposed; do not pass due to short-circuit.
3. All DOCUMENTED_EXTERNAL -> structural candidate but **still** NOT_AUTHORIZED_FOR_SOURCE_EXECUTION and no real market labels.
4. Coinbase/real-market release blocked by provider/owner conditions regardless of user-filled evidence flags; Binance trade-only blocked for book-conditioned model.
5. Extra private/oracle/source event IDs, malformed types or unknown source name reject.
6. Persist one aggregate-only frozen snapshot of actual current evidence: 257/257 source-free CI is NOT original independent source proof; real original trade-only clock, exchange completeness, permissions and power are NOT proven. Tests must not pretend to verify source permissions.

Acceptance: public cheap Python exact CI and stored NO-GO result; no new simulation seeds, vendor archive downloads, computer use or trades. This gate is for scientific planning only. Before any future original-source execution there must be a separate explicit source lawfulness and budget/permissions process, still not automatable through this checker.

NEXT_ACTION: implement fail-closed module+tests separately, never modify prior source outcomes, then record scientific NO-GO in master checkpoint and stage issue.
