# Prospective cross-model held-out log-likelihood hard-negative panel — 2026-11-22

Status: **SOURCE-FREE PRECOMMIT, BEFORE RESULT CALCULATION**. New descriptive comparison of previously preregistered and *already constructed* three public tapes, NOT independent source validation, new research seeds, a new classifier, or a revision to M0/M1-v2/M2 frozen fitting protocols.

## Frozen evaluation setup

Use exactly the three public event sequences frozen in [CONDITIONAL_PUBLIC_TAPE_AMBIGUITY_PREREG_20261122.md](CONDITIONAL_PUBLIC_TAPE_AMBIGUITY_PREREG_20261122.md): `periodic=(20100,21000,21900,22800)`, `momentum=(20100,20101,20102,22800)`, `irregular=(20100,20710,21930,22850)` milliseconds, all in the same [20000,23000) source-asserted complete evaluation window. Reuse `toy_models_train_only()` *unchanged* to fit M0/M1-v2/M2 from separate declared source-free training runs; use previous-only public BBO snapshots 18500/20500 with M1-v2 fixed 1000ms lag and 10s staleness. No hidden scenario or owner identifiers are inputs to model prediction or fitting.

Compute FULL held-out log likelihood for all three:
- M0 from `predict_m0_exposure` and `heldout_fixed_intensity_log_likelihood`.
- M1-v2 from `predict_m1_dynamic_exposure` and the SAME full-window exact scorer.
- M2 from `evaluate_m2_run` predictably integrated self-exciting history. The M2 training grid and tau are already frozen.
Report for each tape the three actual LL numbers and differences `M1v2-M0`, `M2-M0`, M2 training coefficients `mu,a,tau`, fixed source-asserted coverage semantics, 4 unique clusters, no owner identifiability, no true real market FDR. Report all three tapes, whether M1v2 or M2 "wins" or loses, with no favorable subset selection and NO calibration threshold/p-value/robot label.

## Adversarial predictions / falsifiers

1. A constant M0 with exactly four unique events and same time denominator yields IDENTICAL held-out LL across the three tapes irrespective of event arrangement. If not, incorrect exposure/counting.
2. M1-v2 regime-adjusted LL may differ by number of events in each segment; a known transition exactly at 21500ms must use later, causally lagged regime. Its score is NOT proof of an algorithm.
3. M2 may find non-target momentum temporally more predictable than periodic/irregular; this is a methodological **false interpretation risk**, not a positive identification. All results retained, including if momentum M2 gains.
4. Under same public tape and public L2, any two invented private underlying stories produce **identical** outputs for all models; parameter fits receive no private story.
5. Splitting event fills at already present timestamps does not change source-free model likelihoods; mutating unknown source coverage/precision causes explicit `ABSTAIN`, not classification.
6. Absolutely no real source, source seed allocation, oracle labels, market p-values, physical actor attribution or change to frozen model/hyperparameters.

Acceptance: deterministic aggregate-only CLI (no raw source export) and source-free negative/unit tests run in existing cheap public-branch Python CI. Any failed predictions or bad model comparison outcomes are scientifically retained in the living plan.

NEXT_ACTION after this panel: examine whether M0/M1v2/M2 represent adequate scientifically falsifiable predictive baselines under realistic missingness, before a resource-approved independent source study.