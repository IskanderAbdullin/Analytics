# Public SBER activity episodes — first descriptive smoke

Predeclared 2026-11-19; this is an **engineering replay**, not an independent forecast validation.

Input: the **already analyzed** anonymized public SBER_TQBR trade tape for 2026-11-17, expected 121,920 original prints and compressed SHA-256 `0af872b1c9c861e7af40a1c40e5bbdf565f9161dd997337c08da584c4dafc782`. Read-only T-Invest API with a scope-limited pinned CA; no account token or trading API.

Code/config: [SIMPLE_ACTIVITY_EPISODES.md](SIMPLE_ACTIVITY_EPISODES.md), 5-minute UTC windows, four prior same-instrument/source/mode/session contiguous populated windows, minimum ten public prints, >=3× median prior print count, >=3× median prior lots, absolute provider-reported direction imbalance >=0.6. **No tuning after reading this archive**. The same tape is reused because this is only a parser/aggregation/algorithm smoke test.

Output only aggregate counts by label: total populated windows, windows with sufficient four-window uninterrupted history, warmup or gap-reset windows, high-activity windows split by provider BUY/SELL dominance. Do not log individual anonymous prints or source order events. Verify that raw counts are conserved, classification counts sum to total flagged windows and `actualBotCountKnown=false`, `significanceCalibrated=false`.

This cannot identify trading algorithms. In particular news bursts, common synchronized exchange timing, auctions, partial fills and feed gaps could produce the same pattern. No trading action or live alert is emitted.

GitHub Actions: [robot-detector-flow-public-replay.yml](../../../.github/workflows/robot-detector-flow-public-replay.yml), single PR/manual job. Raw files and scoped root certificate removed at end. No artifacts retained.

## Observed engineering smoke — 2026-11-19

[GitHub Actions run 44543584480](https://github.com/IskanderAbdullin/Analytics/actions/runs/44543584480) completed successfully, including **62/62** offline .NET self-tests, safe public archive download, automatic cleanup and the new activity-window checks.

| Observed property | Value |
|---|---:|
| Original public SBER prints | **121,920** |
| Populated windows across trade source/mode/session and 5-minute UTC bins | **203** |
| Windows with sufficient four-window historical baseline | **199** |
| Warmup / gap reset windows | **4** |
| **Flagged high-activity windows** | **1** |
| Flagged with provider-reported BUY dominance | **1** |
| Flagged with provider-reported SELL dominance | **0** |
| Actual independent bot programs identified | **Unknown** |
| Statistical significance / economic predictive edge | **Not established** |

The archive compressed SHA-256 matched the previous engineering source:
`0af872b1c9c861e7af40a1c40e5bbdf565f9161dd997337c08da584c4dafc782`.

**Interpretation:** with fixed heuristic thresholds and contiguous past-only reference, the simple approach is selective on this already studied SBER day: it flagged **1 of 199 scorable windows**. That one window is evidence of **aggregate anonymous trading intensity with strong reported-side imbalance**, not a count of one algorithm/trader. No claim is made that a user could profitably trade that signal, that it is manipulation, or that it would repeat on another day. A separate untouched instrument/day and an exchange-wide clock/auction/halts control are still required before considering alerts.

The step successfully demonstrates a simple alternative can process the entire public tape without the dense-window exclusions of the period detector. Its hypothesis is different: **"unusual activity relative to immediately prior local history"** rather than **"one actor trading every T seconds."**

