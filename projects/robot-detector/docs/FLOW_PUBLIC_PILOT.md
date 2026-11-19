# SBER anonymous trade-flow footprint: descriptive real-data pilot

**Predeclared 2026-11-19**, before running the new read-only flow-footprint analysis against this file. This is deliberately **not** a validation of distinct trading bots.

## Immutable input and metrics

- Source: public T-Invest anonymized trade archive `SBER_TQBR`, `2026-11-17`, previously accessed successfully by the original periodicity detector. The date is reused **only to verify new simple features and processing**, so it is **not** an unseen statistical test.
- The exact archive compressed SHA-256 must match the previously observed `0af872b1c9c861e7af40a1c40e5bbdf565f9161dd997337c08da584c4dafc782` or the change must be investigated. Previously seen print count: 121,920; source market completeness still unknown.
- Method: [TRADE_FLOW_FOOTPRINT.md](TRADE_FLOW_FOOTPRINT.md), no cadence fitting, no ML, no predictions and no owner identification. Group by UID, source, mode, session and 5-minute UTC window; count-bin width 1s, round-second phase threshold 100ms.
- Output: original print count; source file hash; number of 5-minute populated windows; total lots; maximum prints per window; median and maximum per-window one-second count Fano; fraction of prints near whole-second UTC boundaries; median provider-reported side imbalance.
- Invariant checks: sum of per-window print counts equals original print count; total lot quantities equal sum of BUY/SELL/UNKNOWN reported quantities in every window; no Fano on single bin; source feed coverage flag remains unverified; `actualBotCountKnown=false`, `statisticalSignificanceEstablished=false`.
- GitHub Actions: [robot-detector-flow-public-replay.yml](../../../.github/workflows/robot-detector-flow-public-replay.yml), an isolated manual/PR-only workflow, **NOT an hourly runner**. Official CA pinned by SHA-256 for this process only, TLS verification never disabled. Raw downloaded prints and temporary CA deleted at the end; no artifacts retained.

## Interpretation and next steps

The report measures **trade-flow structure**, not the number of market-making or TWAP robots. Fano >1 and round-second clustering are features of public order-flow activity and may reflect many participants or common exchange timing. Signed imbalance refers only to the exchange provider's reported direction; do not label it an aggressor or passive side without further semantics verification.

If the basic replay succeeds, implement a simple stateful high-activity *episode* comparator using a deliberately transparent rolling baseline and test against synthetic bursts and quiet periods. Validate that detector on an independent source/day and document any session or liquidity confounders. Retain the original failure to demonstrate a fixed-cadence prospective forecast advantage.

**Observed metrics:** append only from actual CI results, not estimates.
