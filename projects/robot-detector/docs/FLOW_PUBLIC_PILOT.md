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

## Actual first real-data replay (2026-11-19)

Confirmed by [GitHub Actions run 44542121317](https://github.com/IskanderAbdullin/Analytics/actions/runs/44542121317), **all steps successful** and **56/56** full offline tests. The same previously observed archive hash `0af872b1c9c861e7af40a1c40e5bbdf565f9161dd997337c08da584c4dafc782` was read. Raw prints and scoped root certificate deleted at the end.

| Aggregate reported feature | Observed value |
|---|---:|
| Anonymized SBER public prints | **121,920** |
| Populated 5-minute source/mode/session windows | **203** |
| Sum of observed public lots | **19,769,931** |
| Maximum prints in a single window | **2,883** |
| Windows with computable 1-second Fano | **202** |
| Median Fano across computable windows | **8.883** |
| Maximum Fano | **287.111** |
| Windows with calculable provider-reported side imbalance | **203** |
| Median provider-reported side imbalance | **0.0351** |
| Share of prints in first 100ms after each UTC second | **10.837%** |
| Known physical robot count | **Unknown** |
| Calibrated statistical significance | **None** |

**Interpretation:** every original print and its volume was allocated to exactly one output window; the detailed CI check verified `TotalLots = BuyLots + SellLots + UnknownDirectionLots` for every populated group. Fano factors substantially above 1 indicate bursts in public-print arrivals at this 1-second bin width; they are **not estimates of trader count or proof of active bots**. The 10.837% first-100ms clock share is a descriptive fraction, without an exchange-aware null, independence assumption, or significance test. Median imbalance near zero says only that the provider-reported BUY/SELL volumes are nearly balanced at the per-window median; it does not identify passive sides or institutions.

The 203 populated windows are grouped by source, mode and session as well as 5-minute UTC bucket: **do not** interpret that as 203 distinct five-minute time intervals or as 203 algorithms.

### Decision

**Read-only source and descriptive integrity gate: PASSED.** This simpler method has no skipped dense windows or bot-owner claims, making it suitable as an input for a future exploratory activity-episode visualizer. **No predictive or calibrated detection gate has passed.** The next stage must separate exchange-wide clocks, trading halts, and burst clustering before producing any operational signals.

