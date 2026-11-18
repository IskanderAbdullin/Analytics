# Conservative cadence episode fusion — stage 2 development

**Status:** implemented, pending CI verification / empirical application. This feature links **observed candidate episodes** which may originate from the same uninterrupted cadence. It does NOT identify actual owners, distinct algorithms, or an exact count of physical bots.

## Rationale

Historical scanning is split into bounded UTC windows and, for dense sizes, fixed-size event chunks. One periodic stream crossing a window boundary can produce multiple `PatternHypothesis` results. Counting these results independently makes the reported *episode count* sensitive to an arbitrary window/chunk configuration.

This separate projection does not modify the original detector's candidate episodes. It produces another result `EpisodeFusionReport` with `ConservativelyLinkedGroupCount` and `LinkedEpisodeCount` for audit. Never label these as real bot counts.

## Link rules (intentionally strict)

Two consecutive episodes may link ONLY if:
1. Same `InstrumentUid`, `TradeSource` (EXCHANGE vs DEALER), `ReportedDirection`, `SessionId`, `TradingMode`, `ModelFamily`, `TypicalQuantityLots` and **exact** `PeriodMilliseconds`. Harmonics and near-matching periods are deliberately NOT fused in this version.
2. All events are disjoint, with original source event IDs and evidence timestamps validated against the input. The source SHA in the report must exactly match the tape's SHA.
3. There is no overlap in observed time ranges: `next.first > previous.last`.
4. For gap `G = next.first - previous.last` and period `T`, `G <= max_gap_cycles * T`. Default `max_gap_cycles=12`, bounded to 1..100.
5. The nearest positive integer multiple of `T` is within `2 * timing_tolerance` of `G`; factor 2 represents accumulated jitter of two observed prints. Each episode's observed clock may deviate by the screening tolerance, so the join uses no future events beyond existing selected evidence.

For ambiguous eligible chains, assign the new episode to the chain whose latest event is closest in past time (deterministic tie-break by earlier `pattern_id`). Never treat matching type/period/phase as a proof of one trading program.

## API / CLI

`EpisodeFusion.Group(TradeImportResult, DetectionReport, DetectorConfig, maxGapCycles)`.

```powershell
dotnet run --project src/RobotDetector.Cli -- fusion \
  --input fixtures/synthetic_cross_hour_5s.csv \
  --max-gap-cycles 12 --output data/results/fused.json
```

Expected synthetic result: `candidateEpisodeCount=2`, `conservativelyLinkedGroupCount=1`, `linkedEpisodeCount=1`, `uniqueAttributedPrintCount=13`, `uniqueAttributedLots=1300`, `actualBotCountKnown=false`. The upstream fixed-volume detector's candidate results are preserved; fusion only summarizes them.

A gap of 30 minutes between two 5-second period episodes must **not** merge. Episodes on different sides/sources/sessions/trading modes must not merge, nor should two phases differing by 2 seconds.

## Limitations and next experiments

- Group count is not necessarily a lower or upper bound on physical programs: one program can execute several behaviours; multiple programs can produce indistinguishable behaviour.
- Exact period equality can undermerge when observed periods drift by a 50ms quantization step. Widening this requires blinded tests to avoid false linking.
- Source `SessionId` must be accurate; the current CSV importer defaults to UTC date when the source lacks a session ID. This is **not** a fully verified exchange trading calendar.
- A large gap can reflect missing feed coverage, not program stop. The algorithm chooses not to bridge that uncertainty.
- Two chains overlapping in time cannot join; true repeated behaviours may remain separately labelled.
- Overlap checks prevent double-attribution of observed volume, but not erroneous assignment of one print to a behaviour, for which independent null/holdout validation is required.

**Acceptance:** synthetic 13 prints straddling an hour should link 2→1; 30-minute gap, 2-second phase shift, different source, different trading mode, mismatched file SHA and overlapping evidence must not link. CI must compile and run all regression tests. Then compare episode/group counts on the real SBER 2026-11-17 archive without publishing raw tape.
