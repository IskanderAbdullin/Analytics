# Market Robot Detector — короткая карта восстановления

**Единственный проект:** `IskanderAbdullin/Analytics/projects/robot-detector/`. **Рабочая ветка:** `agent/robot-detector-l2-binphase-20261121`. Не создавать проект-дубль в `Info` или второй исследовательский checkpoint.

| Когда нужен | Единственный актуальный источник |
|---|---|
| Цель / научный release gate | [GOAL.md](GOAL.md), [master issue #72](https://github.com/IskanderAbdullin/Analytics/issues/72) |
| Ограничения и алгоритм восстановления | [AGENTS.md](AGENTS.md), [операционное ТЗ](docs/AUTONOMOUS_RESEARCH_TZ.md) |
| План, пререгистрации, решения и хронология | [MASTER_RESEARCH_PLAN.md](docs/MASTER_RESEARCH_PLAN.md), секции 2–8 и датированные append-only исследовательские записи |
| Машинный checkpoint и **один** следующий шаг | [research/autonomy_state.json](research/autonomy_state.json), поля `current_stage` и `resume_instruction`; отдельный расходящийся `NEXT_ACTION` **не создавать** |
| Занятые seeds / отсутствие независимости | [seed_registry.json](research/seed_registry.json) |
| Подтверждения, отрицательные результаты, границы | [EVIDENCE.md](EVIDENCE.md), документы `docs/*NEGATIVE*`, provenance CI и issue [#97](https://github.com/IskanderAbdullin/Analytics/issues/97) |
| Текущая научная гипотеза M0/M1/M2 | [M0 prereg](docs/CONDITIONAL_M0_TRAIN_ONLY_PREREG_20261122.md), [M1 prereg](docs/CONDITIONAL_M1_LAGGED_L2_PREREG_20261122.md), [allocation gate](docs/CONDITIONAL_INTENSITY_ALLOCATION_GATE_20261122.md), [run-integrity prereg](docs/CONDITIONAL_SOURCE_RUN_ALLOCATION_INTEGRITY_PREREG_20261122.md) |
| Данные / разрешения / источники | [ARCHITECTURE](docs/ARCHITECTURE.md), [REAL_SOURCE_LICENSE_GATES](docs/REAL_SOURCE_LICENSE_GATES.md), [исследовательский обзор](docs/RESEARCH.md) |

**Восстановление после остановки:** проверить remote HEAD/CI, прочитать AGENTS → state → нужный раздел живого плана и stage issue, затем сверить committed source tests с CI. Старая запись `active_run_time_log` описывает прошлую сессию, **не** является действующим lock. При конкурирующем агенте не перезаписывать его checkpoint: отдельная ветка/PR либо дождаться непересекающегося сеанса.

**История:** большой хронологический журнал уже встроен в MASTER_RESEARCH_PLAN и GitHub issues/commits; подробная историческая версия прежнего AGENTS хранится в [архиве](docs/AGENTS_LEGACY_20261122.md). Сжатый контекст этого чата не представляет собой полную дословную стенограмму (`history_gap: full chat transcript unavailable`).

## 2026-11-22 — exact ns type4-only source-free pipeline (new, nonexecuting)

**Fast one-command reproduction:** from the existing project root use:

    python -m tools.public_ns_repro_demo

It executes only fixed *constructed* two-train-source/one-eval-source public message/book fixtures, prints an allowlisted aggregate; does not contact external vendors, run ABIDES, read raw source, authorize market-data use, trade or claim actual FDR. On source-free CI [#45057011095](https://github.com/IskanderAbdullin/Analytics/actions/runs/45057011095) full **267/267** tests plus this command passed at SHA 366cd1c3. The expected output includes trained low=.75/s, high=.5/s and deterministic LL=-3.162682072451781 for exactly one visible type4 timestamp cluster from two visible execution rows, not a robot prediction.

**Module flow and scientific roles:**
- Source clock input: [public_lobster_ns_time.py](tools/public_lobster_ns_time.py) — bounded exact Decimal seconds→typed nanoseconds, explicit time unit, no ms truncation.
- Event/book projection: [public_ns_visible_exec_projector.py](tools/public_ns_visible_exec_projector.py) — ONLY visible type4 execution clusters, type5 hidden separate, all public post-event book messages as potential future quote source.
- Source identity: [public_ns_source_binding.py](tools/public_ns_source_binding.py) — canonical public-only SHA/replay/source ID structural guard, never a provider signature or physical owner identity.
- Train-only M1-v3: [public_ns_visible_train_only.py](tools/public_ns_visible_train_only.py) → [public_m1_v3_ns_l2.py](tools/public_m1_v3_ns_l2.py) — original-run disjoint visible-type4 training, complete asserted L2, +1s quote lag, age<=10s, exposure-weighted spread regimes.
- Heldout evaluation: [public_ns_visible_integrated_ll.py](tools/public_ns_visible_integrated_ll.py) → [public_ns_heldout_likelihood.py](tools/public_ns_heldout_likelihood.py) — exact ns public type4 clusters, causal full-window expected event intensity and predictive log-likelihood, never a physical bot classifier.
- Safety hard stop: [public_source_study_hard_stop.py](tools/public_source_study_hard_stop.py) — 9 external evidence states; **never authorizes new source/seed acquisition** from self-declarations, even when all say documented.
- Scientific releases: [NO-GO source readiness](docs/NS_VISIBLE_TYPE4_SOURCE_READINESS_AUDIT_20261122.md) and [independent original-world study DRAFT](docs/NS_VISIBLE_TYPE4_INDEPENDENT_STUDY_DRAFT_20261122.md). The draft has no allocated seeds, fitted decision threshold or license approval. [Source clock negative](docs/LOBSTER_PUBLIC_CLOCK_LAG_NEGATIVE_20261122.md): original 110818 milliseconds collisions apply to ALL message types, not measured separately for type4 trades. [Power negative](docs/INDEPENDENT_POWER_FEASIBILITY_AUDIT_20261122.md): n100 inadequate for hypothesized joint criteria. Physical owners / actual real-market FDR remain UNKNOWN.

**Recovery:** start from root AGENTS and live MASTER_RESEARCH_PLAN, then state resume_instruction, current GitHub remote SHA, and latest exact source-free CI. Old failed tests/negative outcomes are retained in the plan and preceding Git history. Do not create an alternate repository/checkpoint, or run prior original vendor/ABIDES workflows. Master #72 and scientific stage #97 OPEN.


## 2026-11-22 — separate ABIDES public Unix-ns source-free family (not LOBSTER type4)

[Scientific ABIDES source-family readiness NO-GO](docs/ABIDES_SOURCE_FAMILY_CAUSAL_READINESS_AUDIT_20261122.md) is the current source context; [exact Python CI 335/335 and two safe aggregate-only CLIs](https://github.com/IskanderAbdullin/Analytics/actions/runs/45061407632) verify source-free engineering only. New ABIDES family modules: [exact epoch clock](tools/public_abides_epoch_ns_clock.py), [public exec/sparse L2 causal screen](tools/public_abides_sparse_l2_screen.py), [full observation-time exposure](tools/public_abides_full_window_exposure.py), [M0/M1v4 LL](tools/public_abides_m0_m1v4_ll.py), [all-nontarget panel](tools/public_abides_m1v4_nontarget_panel.py), [old 160-case compact insufficiency gate](tools/public_abides_compact_160_eligibility.py). Original ABIDES 160-case source metadata retains spent 40 seeds but cannot reproduce new model LL from counts; source-capture external proof/independent study remain BLOCKED. Do not reuse LOBSTER type4 time units, run new source jobs or infer owners/FDR.


**Latest ABIDES clock/source-readiness evidence:** [strict original-source public profile NO-GO](tools/public_abides_source_capture_preflight.py); [source-free exact-ns versus lossy microsecond CSV LL counterexample](tools/public_abides_export_precision_ll.py); [one-microsecond-bucket algebraic LL partial-identification set](tools/public_abides_us_clock_ll_bounds.py). [Exact public Python CI 364/364](https://github.com/IskanderAbdullin/Analytics/actions/runs/45062183157) at b6836560, source-free only. Full interpretation and no real source/FDR in [ABIDES scientific NO-GO audit](docs/ABIDES_SOURCE_FAMILY_CAUSAL_READINESS_AUDIT_20261122.md). Canonical NEXT_ACTION and active-run clock remain only in research/autonomy_state.json; do not create a new project/seed registry/source workflow.
