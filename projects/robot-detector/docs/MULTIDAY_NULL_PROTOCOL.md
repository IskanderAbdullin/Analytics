# Multi-day SBER research pilot: two null models and conservative cadence continuity

**Created 2026-11-18.** Stage 2, exploratory. This is a predeclared protocol for two *specific* available trading days, **not** a claim that they have already been run.

## Scope

- Instrument: `SBER_TQBR`, source: public anonymized T-Invest trade-history archive.
- Test dates: Monday **2026-11-16** and Tuesday **2026-11-17**. Both in exchange-local historical past; archive access may differ.
- Data security: only two read-only public downloads, no broker token or trading account; no private MBO, no raw tape committed or uploaded.
- Source integrity: SHA-256 of the raw compressed response in each summary, validate parsed rows, preserve EXCHANGE and DEALER as different `TradeSource`.
- Time handling: UTC file timestamps, default importer session ID is UTC date; **does not** prove exchange trading-mode session boundaries.
- Deterministic parameters: `DetectorConfig` defaults, 60-minute analysis windows, max 5,000 same-size/side/source observations per chunk, `MaxFusionGapCycles=12`; no prior per-date tuning.
- Negative controls: **12** seeded trials each for two null variants per day, seed=9001, step=1009, 60-second local window, 24 independent detector re-runs per day.
- All screens use identical config; if a date is missing or parse fails, report `BLOCKED_BY_DATA` rather than `zero bots`.

## Primary descriptive outputs

For each day:
1. Total decoded prints, rejected rows, raw compressed SHA, reported source coverage status.
2. Candidate **episodes** before fusion; **observable groups** after conservative fusion; number of linked episode boundaries and events used (no duplicate prints).
3. *Permute* conditional null: full uniform shuffle of sizes within (instrument/source/direction/mode/session/minute) bins; preserves time and one-minute size multiset, disrupts most serial size order.
4. *Rotate* conditional null: nonzero circular shift of the same size sequence in each minute. Mostly preserves adjacent-size order (one seam) while changing the association with absolute event timestamps and phase.
5. For each null variant: raw candidate episode counts and conservatively linked group counts, arithmetic mean, max, null samples which actually changed trade size labels. For descriptive *global* comparisons only, calculate `(1+#{null_count>=original_count})/(B+1)`; at 12 repeats the smallest resolution is **1/13 ≈ 0.0769**, so no conventional 5%-significance claim is possible even if the null were perfect.
6. Explicit `actualBotCountKnown=false`; do not infer a specific robot/owner count.

## Why two null variants are important

An excess of candidates over a full permutation can reflect ordinary serial dependence in trade sizes rather than algo clock scheduling. A circular shift retains most size runs, making a better **stress test** for that confounder. Both nulls are imperfect: they do not preserve parent-order identities, causal queue dynamics, all clustering and market impact. Repeated testing and choosing the model yielding the most attractive number is prohibited; report both side-by-side.

## Acceptance and failure handling

- Build all .NET 10 projects and run offline regression tests before requesting the actual archives.
- Protect HTTP TLS with official root CA from https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt, pin the independently observed fingerprint `D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31`. Use process-scoped `SSL_CERT_FILE` only; do not disable certificate checks or update global trust.
- Limit each download to 250 MB compressed, 1 million decoded prints. Stop and label missing or inaccessible days as blocked.
- A job must not pass as a real-data success unless all parsers, fusion and both null comparisons produce readable JSON.
- No broker secrets, raw trade tape or per-trade logs stored as workflow artifacts. Only aggregate metrics in build logs; raw files deleted in `if: always()`.
- Both dates' results must be compared by the **same** code revision and configuration, while preserving SHA for audit.
- CI reliability does not validate statistical interpretation; use a later held-out date and an ABIDES-known-identity synthetic environment for actual quality gates.

## Next pre-registered extension (not in this pilot)

- Expand to 50+ seeds per null on one unseen day, using a larger shared-compute budget only after reviewing this pilot.
- Use block-bootstrap/Hawkes/null preserving trade clustering, and a market-wide 1s/60s rhythm control.
- Evaluate prediction success in strictly future windows, with null adjustment for selecting a candidate from many periods.
- Add data completeness, trading calendars, and model confidence calibration only once tested.

## References

- [Stage 2 detailed requirements](STAGE_02_VALIDATION.md).
- [First single-day real size shuffle pilot](NULL_CONTROL_PILOT.md) — 209 original candidate episodes versus 140/141/144/129 in four permutation controls.
- [Episode fusion explanation](EPISODE_FUSION.md).
- [Primary T-Invest archive documentation](https://developer.tbank.ru/invest/services/history-md/head-history-md).

**Results table:** to be filled ONLY after observed GitHub Actions logs; no numbers are inferred in advance.
