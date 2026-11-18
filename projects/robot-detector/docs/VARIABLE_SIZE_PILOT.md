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

## Measured real-data pilot — executed 2026-11-18

**Run:** [GitHub Actions 44306311739](https://github.com/IskanderAbdullin/Analytics/actions/runs/44306311739), successfully completed with **50/50** .NET self-tests and all temporary source files removed.

- Prespecified instrument **MOEX_TQBR** (Moscow Exchange equity), date **2026-11-03**.
- Imported **19,086** public anonymized trade prints. Raw compressed file SHA-256: `de06494756164573dc4e87398b987f9f39bf08e22d4acc4b606b82441fecc143`.
- Detected **7 variable-clip time-regular candidate sequences**, assigning a total of **374 distinct observed public prints** (no double attribution). **0** densely populated windows were skipped under the 2,500 print limit.
- In four `uniform-minute` timestamp controls, candidate counts were **1, 1, 1, 1**, mean **1.0**. All 19,086 timestamps changed each time.
- In four `rotate-minute` timestamp controls, candidate counts were **0, 0, 0, 1**, mean **0.25**. All 19,086 timestamps changed each time.
- Descriptive global count tail frequency for both controls: `1/(4+1)=0.2`. This is not a formal significance test, calibrated p-value, FDR, or posterior probability that there are 7 robots.
- **Actual bot/owner count remains unknown.** No identifiable order/participant IDs or verified market-data feed completeness; none of these observations is a validated next-trade prediction.

**Interpretation:** first independent real-world data-access/screening smoke succeeded and identifies **more candidate timed varied-q print sequences** than these weak 4-run time controls. However, this does **not** identify seven bots: several independent traders may create the same rhythm, or one program may create several sequences. The controls alter exchange clustering and market-clock structure; B=4 is too small for any meaningful significance claim.

**Next predeclared study:** freeze all method parameters unchanged, choose a new MOEX archive date (e.g. 2026-11-02) and use at least 24 controls per family (minimum descriptive tail 1/25=0.04, still not valid inference without proper null assumptions). Include event-level future-only forecast performance after full calibration and a controlled known-agent simulation; do not enable live signals based on this pilot.

### Decision

**Data-access and synthetic correctness gate PASSED. Statistical validity/forecasting gate NOT PASSED.** The implementation remains research-only and cannot report a confirmed number of actual robot programs.

