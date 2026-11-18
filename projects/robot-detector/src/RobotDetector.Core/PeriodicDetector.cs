using System.Security.Cryptography;
using System.Text;

namespace RobotDetector.Core;

/// <summary>
/// Explainable fixed-volume periodicity screen. This is NOT a participant-identity
/// classifier and produces candidates, NOT validated or calibrated probabilities.
/// </summary>
public static class PeriodicDetector
{
    private sealed record Candidate(PatternHypothesis Pattern, double RankScore);

    public static DetectionReport Detect(TradeImportResult imported, DetectorConfig config)
    {
        config.Validate();
        var warnings = new List<string>
        {
            "SCREENER_ONLY: detected streams are unvalidated statistical candidates, not identified trading programs.",
            "NO_OWNER_IDENTIFIERS: physical bot count is unknown.",
            "COVERAGE_UNVERIFIED: gaps, auctions and missing prints can affect all estimates.",
            "DIRECTION_IS_PROVIDER_REPORTED: not necessarily the side of a passive limit order.",
            "WINDOWED_EPISODES: candidates in different UTC/event-count windows can belong to one algorithm; count is not distinct owners."
        };
        if (imported.RejectedRowTotal > 0) warnings.Add("REJECTED_ROWS: see diagnostics; do not infer a complete feed.");
        if (imported.Trades.Count == 0) warnings.Add("EMPTY_INPUT: no events to analyse.");
        if (imported.Trades.Any(t => t.ReportedDirection == "UNKNOWN"))
            warnings.Add("UNKNOWN_TRADE_SIDE: events with unknown direction are not attributable to BUY/SELL.");

        var allCandidates = new List<Candidate>();
        var groups = imported.Trades
            .Where(t => t.ReportedDirection != "UNKNOWN")
            .GroupBy(t => (t.InstrumentUid, t.TradeSource, t.ReportedDirection,
                           t.TradingMode, t.SessionId, t.QuantityLots))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.ReportedDirection, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal)
            .ThenBy(g => g.Key.QuantityLots);

        foreach (var group in groups)
        {

            var ordered = group.OrderBy(x => x.ExchangeTimeUtc)
                .ThenBy(x => x.ArrivalSequence).ToList();
            long windowMs = config.AnalysisWindowMinutes * 60_000L;
            var windows = ordered.GroupBy(x => x.ExchangeTimeUtc.ToUnixTimeMilliseconds() / windowMs)
                .OrderBy(w => w.Key);
            foreach (var window in windows)
            {
                var list = window.ToList();
                if (list.Count < config.MinMatches) continue;
                if (list.Count > config.MaximumEventsPerGroup)
                {
                    warnings.Add($"SPLIT_DENSE_GROUP: uid={group.Key.InstrumentUid}, q={group.Key.QuantityLots}," +
                                 $" side={group.Key.ReportedDirection}, utc_window={window.Key}," +
                                 $" count={list.Count}; split into contiguous no-overlap event chunks.");
                }
                for (int offset = 0; offset < list.Count; offset += config.MaximumEventsPerGroup)
                {
                    int chunkCount = Math.Min(config.MaximumEventsPerGroup, list.Count - offset);
                    if (chunkCount < config.MinMatches) break;
                    var chunk = list.GetRange(offset, chunkCount);
                    var candidates = GeneratePeriods(chunk, config);
                    foreach (int periodMs in candidates)
                    {
                        int anchors = Math.Min(chunk.Count, config.AnchorLimit);
                        for (int anchor = 0; anchor < anchors; anchor++)
                        {
                            var candidate = Evaluate(chunk, anchor, periodMs, config);
                            if (candidate is not null) allCandidates.Add(candidate);
                        }
                    }
                }
            }
        }

        var chosen = new List<PatternHypothesis>();
        var assignedIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (var candidate in allCandidates
                     .OrderByDescending(c => c.RankScore)
                     .ThenByDescending(c => c.Pattern.PeriodMilliseconds)
                     .ThenBy(c => c.Pattern.PhaseUtc, StringComparer.Ordinal)
                     .ThenBy(c => c.Pattern.PatternId, StringComparer.Ordinal))
        {
            // Deliberately conservative one-to-one event allocation, including
            // different hypothesised periods for the same observed prints.
            if (candidate.Pattern.EvidenceEventIds.Any(assignedIds.Contains)) continue;
            chosen.Add(candidate.Pattern);
            foreach (string id in candidate.Pattern.EvidenceEventIds) assignedIds.Add(id);
        }
        chosen = chosen.OrderBy(p => p.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(p => p.TradeSource, StringComparer.Ordinal)
            .ThenBy(p => p.SessionId, StringComparer.Ordinal)
            .ThenBy(p => p.ReportedDirection, StringComparer.Ordinal)
            .ThenByDescending(p => p.MatchedCount)
            .ThenBy(p => p.PhaseUtc, StringComparer.Ordinal)
            .ToList();

        var kinds = imported.Trades.Select(t => t.DataKind).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
        string kind = kinds.Count == 1 ? kinds[0] : "MIXED";
        return new DetectionReport("1.0", "0.1.0-screen", kind, imported.FileSha256,
            imported.Trades.Count, imported.RejectedRowTotal, imported.HasVerifiedFeedCoverage,
            chosen.Count, false, chosen, warnings.Distinct().ToList());
    }

    private static IReadOnlyList<int> GeneratePeriods(IReadOnlyList<MarketTrade> list, DetectorConfig cfg)
    {
        var counts = new Dictionary<int, int>();
        int length = Math.Min(list.Count, 1800);
        // At most a small lag neighborhood, not a quadratic full-trade search.
        for (int i = 0; i < length; i++)
        {
            for (int j = i + 1; j < Math.Min(length, i + cfg.CandidateLag + 1); j++)
            {
                double deltaMs = (list[j].ExchangeTimeUtc - list[i].ExchangeTimeUtc).TotalMilliseconds;
                for (int divisor = 1; divisor <= cfg.MaximumCycleGap; divisor++)
                {
                    double period = deltaMs / divisor;
                    if (period < cfg.MinimumPeriodMilliseconds || period > cfg.MaximumPeriodMilliseconds)
                        continue;
                    int quantized = (int)(Math.Round(period / cfg.PeriodGridMilliseconds,
                        MidpointRounding.AwayFromZero) * cfg.PeriodGridMilliseconds);
                    if (quantized < cfg.MinimumPeriodMilliseconds || quantized > cfg.MaximumPeriodMilliseconds)
                        continue;
                    counts[quantized] = counts.GetValueOrDefault(quantized) + 1;
                }
            }
        }
        return counts.OrderByDescending(x => x.Value)
            .ThenByDescending(x => x.Key)
            .Take(cfg.CandidateLimit).Select(x => x.Key).ToList();
    }

    private static Candidate? Evaluate(IReadOnlyList<MarketTrade> list, int anchorIndex,
        int periodMs, DetectorConfig cfg)
    {
        var anchor = list[anchorIndex].ExchangeTimeUtc;
        double toleranceMs = Math.Max(cfg.MinimumTimeToleranceMilliseconds,
            Math.Min(cfg.MaximumTimeToleranceMilliseconds, periodMs * cfg.RelativeTimeTolerance));
        // Cycle number => best aligned event of this group. Never use a print twice.
        var byCycle = new SortedDictionary<int, (MarketTrade Trade, double Residual)>();
        for (int index = anchorIndex; index < list.Count; index++)
        {
            var trade = list[index];
            double elapsedMs = (trade.ExchangeTimeUtc - anchor).TotalMilliseconds;
            int cycle = checked((int)Math.Round(elapsedMs / periodMs, MidpointRounding.AwayFromZero));
            if (cycle < 0) continue;
            double residual = Math.Abs(elapsedMs - cycle * (double)periodMs);
            if (residual > toleranceMs) continue;
            if (!byCycle.TryGetValue(cycle, out var previous) || residual < previous.Residual ||
                (residual == previous.Residual && trade.ArrivalSequence < previous.Trade.ArrivalSequence))
                byCycle[cycle] = (trade, residual);
        }
        if (byCycle.Count < cfg.MinMatches || !byCycle.ContainsKey(0)) return null;
        // Enforce a continuous cadence segment (a long gap must start a new segment).
        var continuous = new List<(int Cycle, MarketTrade Trade, double Residual)>();
        int? lastCycle = null;
        foreach (var pair in byCycle)
        {
            if (lastCycle.HasValue && pair.Key - lastCycle.Value > cfg.MaximumCycleGap)
                break;
            continuous.Add((pair.Key, pair.Value.Trade, pair.Value.Residual));
            lastCycle = pair.Key;
        }
        if (continuous.Count < cfg.MinMatches) return null;

        int expected = continuous[^1].Cycle + 1;
        double coverage = (double)continuous.Count / expected;
        if (coverage < cfg.MinCoverage) return null;

        var chosen = continuous.Select(x => x.Trade).ToList();
        string material = string.Join("|",
            chosen[0].InstrumentUid, chosen[0].TradeSource, chosen[0].TradingMode,
            chosen[0].SessionId, chosen[0].ReportedDirection, chosen[0].QuantityLots,
            periodMs, string.Join(",", chosen.Select(x => x.EventId)));
        string id = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(material)))[..16].ToLowerInvariant();
        // This is a ranking heuristic, NOT a p-value, probability or significance test.
        double meanResidual = continuous.Average(x => x.Residual);
        double score = continuous.Count * coverage -
                       meanResidual / Math.Max(1.0, toleranceMs) * 0.05;
        var hypothesis = new PatternHypothesis(id, chosen[0].InstrumentUid, chosen[0].Ticker,
            chosen[0].TradeSource, chosen[0].ReportedDirection, chosen[0].SessionId,
            chosen[0].QuantityLots, periodMs,
            anchor.ToUniversalTime().ToString("O"),
            continuous.Count, expected, expected - continuous.Count,
            chosen.Sum(x => x.QuantityLots), meanResidual, coverage,
            chosen.Select(x => x.EventId).ToArray(), "fixed_quantity_periodic",
            "candidate", null,
            "No owner/order IDs; unknown completeness; no out-of-sample statistical validation.");
        return new Candidate(hypothesis, score);
    }
}
