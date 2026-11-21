# Research seed provenance and anti-leakage ledger

**Date:** 2026-11-21. **Purpose:** prevent recycled simulator seeds from being presented as unused, independent blind evaluation. This is **project-local provenance**, not a globally verifiable registry of all simulator runs.

## Problem addressed

Multiple Market Robot Detector stages have executed genuine ABIDES matching-engine runs for development, null controls and frozen evaluations. Some earlier seeds were intentionally re-used to **reproduce the same simulated tape**. Calling an already inspected seed a "new holdout" would contaminate experimental design. Previous experiments also selected quote/flow bin widths and models after exploratory work; a strict historical ledger helps avoid data snooping and unjustified claims.

`research/seed_registry.json` lists previously inspected **canonical seed sets** with their purposes:

| Group | Known spent seeds |
|---|---|
| Early public execution studies | 41–44 |
| Public volume-response development | 61–63 |
| Public directional-shift development | 71–73 |
| Original frozen execution evaluation | 901–904 |
| Directional-shift independent replication | 1101–1104 |
| Unchanged execution strategy baseline | 1301–1304 |
| Genuine L2 feasibility | 1401 |
| Public L2 timing and later bin reanalysis | 1501 |
| Constructed **non-ABIDES** common factor example | 1701 |
| Genuine L2 background-only nulls | 1801–1802 |
| Public L2 bin-width sensitivity | 1901–1902 |

A later lagged-bin reanalysis of **the same seed 1501** is recorded separately as a `non_independent_development_replay`. It does not magically create a second independent study. The constructed toy seed 1701 is separately identified as **not a genuine matching-engine run**.

## Automated source audit

`tools/research_seed_registry.py` uses the Python standard library only. It validates:
- Schema, unique canonical study IDs and unique seed lists, without overlaps between independent canonical studies;
- Explicit non-independent replay referencing the exact canonical study seed set;
- Exactly matched seed constants via Python **AST literal inspection**, without importing or running the ABIDES experiment scripts, for four frozen source plans: `directional_shift_frozen_replication.py`, `abides_execution_baseline_holdout.py`, `abides_l2_background_nulls.py`, and `abides_l2_binwidth_sensitivity.py`;
- A changed frozen constant or missing/duplicated seed is an **error**, not silent success;
- Future `--candidate-seeds` proposals are checked against known spent values, and any collision returns a nonzero exit code.

Example:

```bash
cd projects/robot-detector
python -m unittest discover -s tests_research -p 'test_*.py' -v
python tools/research_seed_registry.py
python tools/research_seed_registry.py --candidate-seeds 1801 1901
```

The last command intentionally **fails** with a known-spent seed collision. A proposal not in the ledger is reported only as **"not previously listed in this project ledger"**, *never* as globally fresh, unused or valid for blind evaluation. An independent provenance record and precommitted evaluation procedure are still required.

## CI and boundaries

The lightweight [`robot-detector-seed-ledger.yml`](../../.github/workflows/robot-detector-seed-ledger.yml) workflow runs only Python source checks and seven deterministic tests. It triggers on changes to the registry, validator, tests, or any of the four mapped frozen scripts. **No simulated markets are rerun by this job**, preserving GitHub Actions minutes.

The ledger is a guard against **known** reuse; it cannot detect all evaluation runs in unrelated branches, notebooks or external projects. Never claim it proves a new seed was globally unseen. Historical source evidence is frozen: to add a truly new experiment, first register its design in a new code review before executing it, and after observing results mark that cohort as spent. Do not rewrite historical labels to manufacture validation.

No broker accounts, trading signals, private maker/taker attribution or actual trading occurs here. **Scientific identity and real-market significance gates remain CLOSED.**
