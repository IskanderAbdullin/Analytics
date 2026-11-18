# Variable-size cadence: one-instrument archival smoke (predeclared)

**Protocol recorded:** 2026-11-18, before obtaining this market-data day.

- **Single instrument / day:** `MOEX_TQBR` (Moscow Exchange company equity, board TQBR), **2026-11-03**. Its availability is unverified; if the public T-Invest archive is absent, report `BLOCKED_BY_DATA` and **do not switch instruments** within this pilot. Do not use the earlier SBER development/held-out dates for tuning this model.
- Download exactly one anonymized public trade archive through the already tested T-Invest read-only endpoint. Use pinned official CA only within GitHub Actions process, no broker token, no orders, no private account.
- Frozen experimental settings in `VariableCadenceConfig`: 8 prints, >=3 distinct q, >=70% cycle coverage, 500ms–300s period, 50ms grid, source/side/session/mode isolation, at most 2500 source prints per UTC hour per source/side (otherwise mark window unavailable).
- Compare **two weak temporal null families** (uniform-minute and circular-minute rotation), **B=4** trials each, seed=1701, step=1009, blockSeconds=60; no threshold optimization on this data.
- Print aggregate only: input and rejected rows, raw SHA-256, accepted observed candidate sequences, count of dense skipped groups, unique attributed events, both null candidate counts/mean and changed timestamps, calibrated flag=false, physical bot count known=false.
- **Primary acceptance criterion:** confirm the parser, variable-cadence screen and at least one null model can process the actual archive or give an explicit `BLOCKED_BY_DATA` / `DENSE_WINDOW_NOT_EVALUATED`. There is **no** predeclared minimum candidate count, no expected advantage, no owner IDs and no predictive validation.
- Raw exchange tape and temporary CA are deleted after the job; never uploaded as artifacts.

**Interpretation:** Even if observed candidates exceed the nulls, B=4 gives minimum descriptive Monte Carlo frequency 1/5=0.2, far too coarse for statistical significance. Both nulls break different real microstructure properties; a clock-regular varied-size print sequence can be produced by many unrelated participants. A failed/no-candidate result is useful and must be reported.

See [VARIABLE_SIZE_CADENCE_PROTOTYPE.md](VARIABLE_SIZE_CADENCE_PROTOTYPE.md) and [STAGE_02_VALIDATION.md](STAGE_02_VALIDATION.md).

**Observed result:** not filled before a successful test run.
