# Evidence index — границы подтверждённого (2026-11-22)

Это **индекс**, а не копия исходных результатов. Канонические численные факты и неизменяемые протоколы — в [MASTER_RESEARCH_PLAN.md](docs/MASTER_RESEARCH_PLAN.md), `research/` и оригинальных GitHub Actions.

- **160 genuine ABIDES source cases, seeds 3301–3340:** [source run #44944144915](https://github.com/IskanderAbdullin/Analytics/actions/runs/44944144915), [один и тот же source replay #44944168231](https://github.com/IskanderAbdullin/Analytics/actions/runs/44944168231), [аудит](docs/ABIDES_160_ORIGINAL_SOURCE_AUDIT_20261121.md). Poisson/momentum false positives сохраняются; сгруппированные timestamp ухудшили чувствительность. ДВА workflow на одном источнике — не два независимых эксперимента.
- **Рынок без истинной owner-разметки:** 8 Binance spot архивов / 776 007 исполнений — [negative cross-market](docs/BCH_FOUR_DAY_OCCUPANCY_PANEL_20261121.md); LOBSTER AMZN 269 748 event/book rows — [формат](docs/LOBSTER_AMZN_PUBLIC_SAMPLE_FORMAT_AUDIT_20261121.md). Никакой физической owner идентификации.
- **Source-free M0:** [пререгистрация](docs/CONDITIONAL_M0_TRAIN_ONLY_PREREG_20261122.md), [код](tools/public_m0_train_only.py), [тесты](tests/test_public_m0_train_only.py). Точный GitHub Python workflow [#45020856671](https://github.com/IskanderAbdullin/Analytics/actions/runs/45020856671) на SHA `4f812ecc` завершился SUCCESS, лог показывает **39 PASS** (включая 9 M0). Между SHA `4f812ecc` и `8bd5a83b` изменились **только** план/M1-документ/state, а не Python-код и тесты. Это техническая проверка, **не** статистическая калибровка.
- **HEAD 8bd5a83b CI:** [ABIDES integration #45020935082](https://github.com/IskanderAbdullin/Analytics/actions/runs/45020935082), [seed provenance #45020935078](https://github.com/IskanderAbdullin/Analytics/actions/runs/45020935078), [.NET #45020935086](https://github.com/IskanderAbdullin/Analytics/actions/runs/45020935086), все SUCCESS. Это не независимая проверка новой M1, которую ещё не реализовали.
- **Открытая работа:** [M1 causal L2 pre-registration](docs/CONDITIONAL_M1_LAGGED_L2_PREREG_20261122.md) — **DESIGN ONLY** на исходном HEAD; M2 и независимый run-disjoint holdout ещё не готовы; после исходного SHA M1 добавлен **узкий source-free prototype** по [предкодовой prereg](docs/CONDITIONAL_M1_SOURCE_FREE_IMPLEMENTATION_GATE_20261122.md) с 12 локально проверенными тестами на source-equivalent stub. Точный GitHub M1 Python CI [#45024195498](https://github.com/IskanderAbdullin/Analytics/actions/runs/45024195498) на SHA `0f3728e1` **PASS: 51/51**, включая все 12 M1. Реальные данные не использованы. Ни одного нового source seed не выделено.
- **Контроли и ограничения:** [нулевая гармоника](docs/PERIOD_ZERO_HARMONIC_V2_NEGATIVE_20261122.md), [публичная owner неидентифицируемость](docs/SYNTHETIC_L2_OWNER_NONIDENTIFIABILITY_20261121.md), [условная 500ms неразличимость](docs/INTENSITY_CONDITIONAL_EQUIVALENCE_CLASS_NEGATIVE_20261122.md). Исторические неудачи не скрывать.

**Не подтверждено:** real-market FDR, число физических роботов, обменность кандидатных timing nulls, статистическая значимость M0/M1/M2, фактическое качество конкретного коммерческого источника L2. Нельзя распространять raw vendor archives/секреты.

**Further verified repair:** [provenance CI #45024279130](https://github.com/IskanderAbdullin/Analytics/actions/runs/45024279130) on SHA `24f2e8ff` SUCCESS after restoring living-plan/decision-log markers in concise AGENTS. [M2 preregistration](docs/CONDITIONAL_M2_PREDICTABLE_HISTORY_PREREG_20261122.md) remains DESIGN-ONLY: no tests or source results.


**M2 engineering (not yet independently verified):** preregistration commit `167d9174` precedes source-free scorer `tools/public_m2_train_only.py` and 12 authored tests. Local stand-alone equivalent passed 12/12; exact GitHub Python CI pending. Model fit is NOT market calibration or an actor detector.


**M2 exact CI and later negative:** Python run [#45024579897](https://github.com/IskanderAbdullin/Analytics/actions/runs/45024579897) PASS **63/63** on `8a28d374`, including 12 new M2 tests. Later `10**500` malformed timestamp/rate found uncontrolled OverflowError, added explicit safe-exact-range ABSTAIN and 2 tests; local equivalent 14/14 pass, new GitHub CI pending. Original M2 source data/calibration still absent.


**Original-run allocation integrity (pre-source, no holdout created):** [prereg](docs/CONDITIONAL_SOURCE_RUN_ALLOCATION_INTEGRITY_PREREG_20261122.md) committed before implementation (`fe591340`); source-free checker/tests reject split leakage, replay phases, spent local seeds, missing hard-negative cohorts, oracle fields and malformed registry. Local minimal-ledger 10/10 PASS; exact GitHub full-ledger CI pending. No globally fresh seed claim.


**Verified final source-free branch CI:** [#45025008917](https://github.com/IskanderAbdullin/Analytics/actions/runs/45025008917) exact SHA `32caf2c1` **75/75 Python PASS**, including the two fail-closed M2 overflow tests and all ten allocation-integrity tests with full project ledger. [Provenance #45025008831](https://github.com/IskanderAbdullin/Analytics/actions/runs/45025008831) SUCCESS. Other workflows may remain in progress; no source experiments, independent holdout, market p-values, true actors or real FDR established.


**Hypothetical source-free power negative:** [CI #45038045732](https://github.com/IskanderAbdullin/Analytics/actions/runs/45038045732) exact SHA `e085fac5` PASS 100/100; full 6×3×4 grid code plus [audited selected outcomes](docs/INDEPENDENT_POWER_FEASIBILITY_AUDIT_20261122.md). At n=100, assumed p_pos=.90/p_neg=.02, simultaneous gate power is bounded above by .1326 under any cohort dependence. NOT a measured market/source rate; no new seeds or ABIDES cases. Existing synthetic background false positives remain a larger science risk.


**New negative predictive result (constructed, source-free):** [Exact Python CI #45039673176](https://github.com/IskanderAbdullin/Analytics/actions/runs/45039673176) PASS 149/149 and complete aggregate-only output. [Full report](docs/CROSSMODEL_HELDOUT_LL_NEGATIVE_20261122.md): all 3 non-target tapes M0 LL −3, M2 identical (training chose amplitude 0), M1-v2 worse than M0 in all 3 (ΔLL −0.62266, −0.95913, −0.62266). This is a negative toy result, not independently validated FDR or actor signal.


**Real-source capability audit:** [2026-11-22 source rights/causal L2 report](docs/SOURCE_CAPABILITY_AND_CAUSAL_GATES_20261122.md), based on official LOBSTER output/sample docs, previous source QA and ABIDES evidence. Unverified 1ms event clock/full L2 continuity prevents treating a source-only M1-v2 toy as real-market validated; LOBSTER's book row i is POST-event i. No data/raw source export or new independent model validation.


**Major real historical source-quality negative:** [LOBSTER clock/lag run #45040590585](https://github.com/IskanderAbdullin/Analytics/actions/runs/45040590585), exact original pinned sample, aggregate-only artifact `14761716634`. [Complete report](docs/LOBSTER_PUBLIC_CLOCK_LAG_NEGATIVE_20261122.md): 269747/269748 sub-ms timestamps; 110818 distinct exact source timestamps would merge by floor-to-ms (42.4% groups); 8927/8974 visible executions locally eligible after fixed 1s post-event L2 lag, 43 no prior,4 stale; no labels/FDR. Source workflow manual-only after one run; no raw data export.
