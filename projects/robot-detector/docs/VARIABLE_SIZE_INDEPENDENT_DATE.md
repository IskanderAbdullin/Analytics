# Variable-size cadence: independent fixed-configuration MOEX date

**Protocol registered 2026-11-18 before obtaining this file.** Research-only. No live trades, trading signals, owner identities or calibrated probabilities.

## Inputs and frozen method

- Exactly one additional public T-Invest anonymized history archive for **MOEX_TQBR, 2026-11-02** (Monday). We have not previously analyzed this date for the variable-size prototype. If unavailable, report `BLOCKED_BY_DATA` and **do not switch to another instrument or date** during this test.
- Code: released in [Variable-size prototype](VARIABLE_SIZE_CADENCE_PROTOTYPE.md). **No changes to algorithm/configuration** after initial 2026-11-03 MOEX development pilot.
- Frozen settings: 8 or more public prints, at least 3 distinct `QuantityLots`, period 0.5–300 s, 50 ms grid, 70% cycle coverage, conservative 250ms maximum time tolerance, EXCHANGE/DEALER, direction, session and mode isolation, 60-minute UTC windows, skip groups with >2,500 prints.
- Exact source hash and imported row count logged. No raw market tapes, tokens or participant data stored in GitHub.
- Two exploratory temporal controls: `uniform-minute` and `rotate-minute` from `TemporalCadenceNull`. Each uses **24** independent seeds (start 90210, step 1009) and 60-second source/source-direction/mode/session blocks, with no manual selection or re-run until a favorable outcome is found.
- Output original candidate sequences, unique attributed prints, skipped dense windows, all 24 control candidate counts, control mean/max, number of changed timestamps and descriptive global count exceedance frequency.

## Primary question

Does a time-regular variable-size candidate excess persist on another date without parameter tuning? We previously observed on MOEX_TQBR 2026-11-03: **7** candidates from 19,086 public prints; weak B=4 `uniform` controls all had **1**, and `rotate` controls produced `0,0,0,1`. Source and limits: [VARIABLE_SIZE_PILOT.md](VARIABLE_SIZE_PILOT.md).

There is no required minimum candidate count and no success threshold. The second day's results must be retained even when they contradict the first date. At B=24, the smallest possible additive-one Monte Carlo global count frequency is `1/25=0.04`, **but this is not a valid p-value or statistical guarantee unless the conditional null model is appropriate**. Our simple nulls alter or omit real market clustering, round-clock events, parent/child executions and quote dynamics.

## Acceptance and stop conditions

- GitHub Actions independently compiles C#/.NET 10, runs all offline self-tests and only then downloads the read-only public archive.
- Confirms the output has `PhysicalBotCountKnown=false`, `StatisticalSignificanceEstablished=false` and each candidate has `OwnerKnown=false`, `ConfidenceCalibrated=null`.
- Guard against missing data, bad CSV, inactive session, dense-window skip, timeout and partial coverage; report the exact limitation and don't call it zero robots.
- Delete temporary archive and CA on job completion, never upload artifacts containing the raw trade data.
- **Never** turn a candidate count into a claimed number of actual independent bots or an automated trading signal.

## Observed results — 2026-11-18

**CI:** [GitHub Actions run 44306984217](https://github.com/IskanderAbdullin/Analytics/actions/runs/44306984217), completed successfully. **50/50** offline .NET self-tests passed; raw public tape and CA deleted.

- Actual public anonymized prints: **26,960** on **MOEX_TQBR, 2026-11-02**.
- Raw compressed source SHA-256: `dc3cc890e1605d0bceeb5b20474032c088b039fa807322b65b9b3806d6e64a74`.
- Variable-size cadence candidates: **1** with **8** uniquely attributed prints.
- **2** dense source/side/hour windows skipped because source density exceeded the predeclared 2,500 print cap. The candidate screen is **coverage-limited** on this day.
- Uniform-minute null, 24 candidate counts: `0,0,1,0,0,0,0,1,2,0,1,1,0,0,0,0,0,0,0,0,1,0,0,0`; mean **0.2917**, observed-or-higher controls **6/24**, descriptive additive-one tail **7/25 = 0.28**.
- Minute-rotation null, 24 candidate counts: **all 0**, mean **0.0**, observed-or-higher controls **0/24**, descriptive additive-one tail **1/25=0.04**.
- Every print timestamp changed in each control trial; the source instrument, side, mode, minute counts and clip sizes remained within the intended null constraints.
- Actual independently identified robot programs: **UNKNOWN**. Statistical significance established: **FALSE**.

### Interpretation and decision

**No consistent result across null families:** the original 1 candidate is **not unusual** under the uniform-minute control (global descriptive frequency 0.28); it exceeds all rotation-only controls (minimum descriptive 0.04) but those controls preserve a different set of arrival-time correlations and can underrepresent common exchange-phase structure. Neither is a validated microstructure null, and the two dense windows were not examined. **Do not claim p=0.04 as a formal statistical significance level.**

Compared with the earlier 2026-11-03 MOEX developmental pilot (19,086 prints; 7 candidates; no skipped dense windows), the same model produced substantially fewer observable candidate sequences on this second date. This is not proof of model instability or absence of bots by itself: activity, liquidity and source coverage differ, while 2 dense windows were excluded. It does show **insufficient independent repeatability for a validated trading robot counter.**

### Next engineering versus research actions

1. **Engineering:** model version 0.2 introduces bounded disjoint event-count chunks for dense UTC windows. It replaces old version 0.1 skips but may split a single observable flow at a chunk boundary. The historical 2026-11-02 result is **no longer untouched validation** for any changes prompted by it; a repeated engineering comparison must be explicitly labelled diagnostic, not a new independent test.
2. **Research:** develop nulls preserving real exchange round-second clock and clustered/Hawkes-type arrivals, rather than relying only on uniform/rotation controls.
3. **Known-agent validation:** blind ABIDES/NASDAQ-like simulator truth to public prints, estimate recoverable patterns and false positives rather than physical bot count.
4. **Release safety:** no confidence, automated alerts, trading signal, or physical owner/bot count until the full Stage 2 scientific gate passes.

**Decision:** technical archive processing and independent repeated evaluation **PASSED**; identification and prediction quality **NOT VALIDATED**.

