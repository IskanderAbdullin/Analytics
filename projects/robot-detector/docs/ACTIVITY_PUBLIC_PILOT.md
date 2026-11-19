# Public SBER activity episodes — first descriptive smoke

Predeclared 2026-11-19; this is an **engineering replay**, not an independent forecast validation.

Input: the **already analyzed** anonymized public SBER_TQBR trade tape for 2026-11-17, expected 121,920 original prints and compressed SHA-256 `0af872b1c9c861e7af40a1c40e5bbdf565f9161dd997337c08da584c4dafc782`. Read-only T-Invest API with a scope-limited pinned CA; no account token or trading API.

Code/config: [SIMPLE_ACTIVITY_EPISODES.md](SIMPLE_ACTIVITY_EPISODES.md), 5-minute UTC windows, four prior same-instrument/source/mode/session contiguous populated windows, minimum ten public prints, >=3× median prior print count, >=3× median prior lots, absolute provider-reported direction imbalance >=0.6. **No tuning after reading this archive**. The same tape is reused because this is only a parser/aggregation/algorithm smoke test.

Output only aggregate counts by label: total populated windows, windows with sufficient four-window uninterrupted history, warmup or gap-reset windows, high-activity windows split by provider BUY/SELL dominance. Do not log individual anonymous prints or source order events. Verify that raw counts are conserved, classification counts sum to total flagged windows and `actualBotCountKnown=false`, `significanceCalibrated=false`.

This cannot identify trading algorithms. In particular news bursts, common synchronized exchange timing, auctions, partial fills and feed gaps could produce the same pattern. No trading action or live alert is emitted.

GitHub Actions: [robot-detector-flow-public-replay.yml](../../../.github/workflows/robot-detector-flow-public-replay.yml), single PR/manual job. Raw files and scoped root certificate removed at end. No artifacts retained.

**Observed results:** only from completed CI run. Engineering success does not pass statistical or forecasting validation.
