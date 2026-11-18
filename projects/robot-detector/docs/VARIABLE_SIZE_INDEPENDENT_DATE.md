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

**Results:** only to be appended after GitHub Actions reports observed values.
