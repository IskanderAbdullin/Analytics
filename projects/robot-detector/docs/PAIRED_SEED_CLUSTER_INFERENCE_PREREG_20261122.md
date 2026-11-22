# Prospective seed-world clustered negative-control inference (2026-11-22)

**PRETEST / PREIMPLEMENTATION DESIGN FREEZE.** This is a new *source-free methodology*, not a change to any previously viewed ABIDES case. Prior seeds 3301–3340 stay spent. No fresh experimental seeds selected, no source jobs triggered, no calibration or statistical significance on real markets.

## Estimand, independence and immutable input contract

Each **original seed world**, not fill, phase or re-export, is one independent replicate *conditional on the future independent-run assumption*. Exactly four paired cohorts per seed:
`poisson_noise_null`, `fixed_20s_noise_hard_negative`, `momentum_noise_hard_negative`, `twap_45s_positive`.
At most 1000 worlds in this bounded source-free implementation; larger cohorts require a separate scalable review.

For this aggregate-only checker, accept one row **per seed** with exactly:
`seed` (positive exact int), `outcomes` (dict exactly the four cohort keys). Each status exactly `ALARM`, `NO_ALARM` or `ABSTAIN`. The interface has no raw prints, phase, oracle agent ID, owner label or vendor identifier. Repeated seeds and incomplete cohorts fail; this checker does **NOT** establish independently generated worlds, source licenses, or a genuine untouched holdout — those must be established by provenance manifest and preregistration outside it.

## Conservative inference to implement

For each of the three negative cohorts, count **ALARM or ABSTAIN as a potential false-alarm error**. For positive TWAP, count only **ALARM as a success**; positive abstention counts as failure. For every one of the 4 marginal rates use **one-sided exact Clopper–Pearson** with `alpha/4` Bonferroni allocation, default familywise `alpha=0.05`; 4 simultaneous bounds remain valid under within-seed cohort dependence if whole seed worlds are independent. Report all denominators, missingness/abstentions, original status counts, sensitivity lower confidence bound and each negative upper bound. Conservative contrast lower bound = lower bound sensitivity - max(three upper negative bounds), *not* a physical owner detection metric. **Do not select a favorable negative cohort**, use worst of three. Status `SOURCE_FREE_METHOD_DIAGNOSTIC_NOT_CALIBRATED`.

Paired seed-level directional diagnostic: define a world `TWAP_ALARM=1` only if positive cohort status ALARM; `ANY_NEGATIVE_ERROR=1` if any negative is ALARM or ABSTAIN. Among discordant worlds, `b=#(TWAP=1, ANY_NEGATIVE=0)` and `c=#(TWAP=0, ANY_NEGATIVE=1)`; the predeclared exact **one-sided** conditional McNemar/sign tail `P(Bin(b+c,0.5) >= b)`; if `b+c=0`, return 1. This is a source-free mathematical diagnostic, **NOT** validated real market p-value and not the same estimand as the conservative contrast. All 4 cohorts must be reported, even if a candidate performs worse than M0.

## Mandatory source-free negative controls

- Complete fake six-world fixture with mixed alarms, misses and abstentions preserves each world pairing. A 20s unrelated periodic background can false alarm and must be counted as negative.
- An all-ABSTAIN negative cohort is counted as worst-case false alarm; an all-ABSTAIN positive cohort has zero credited successes; no-eligible source observation must NOT be called evidence of no false alarms.
- Duplicate world/partial missing cohorts, bool/negative/fractional seed, unexpected private/oracle/raw/phase field or unknown status fail closed.
- A one-sided no-negative-events 0/100 bound must be >0, and Bonferroni upper must be **higher** than unadjusted. Paired discordants `b=c=0 -> 1`; `b=3,c=0 -> 1/8`; symmetry `b=1,c=1 -> 3/4`.
- Clusters/replays/phase variants must never enter as separate independent world rows; structural checking is not proof of source independence.
- Numerical guard 1..1000 worlds, no expensive bootstrap or invented p-values/accuracy.

**DoD:** precommit frozen before source-free implementation; code, adversarial tests, exact Python CI; evidence and state updated. Next scientific gate: independent actual source-world allocation and coverage/power/multiplicity plan, with source rights and resource budget, BEFORE any simulator seeds or market evaluation.