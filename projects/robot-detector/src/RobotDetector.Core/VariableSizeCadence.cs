using System.Security.Cryptography;
using System.Text;

namespace RobotDetector.Core;

/// <summary>
/// Experimental period-of-trades screen allowing different clip sizes.
/// It identifies candidate event sequences, NEVER a specific algorithm/owner.
/// </summary>
public sealed class VariableCadenceConfig
{
    public int MinMatches { get; init; } = 8;
    public int MinDistinctQuantities { get; init; } = 3;
    public double MinCoverage { get; init; } = 0.70;
    public int MinimumPeriodMs { get; init; } = 500;
    public int MaximumPeriodMs { get; init; } = 300_000;
    public int PeriodGridMs { get; init; } = 50;
    public int MinTimeToleranceMs { get; init; } = 25;
    public int MaxTimeToleranceMs { get; init; } = 250;
    public double RelativeTolerance { get; init; } = 0.015;
    public int MaxCycleGap { get; init; } = 4;
    public int AnalysisWindowMinutes { get; init; } = 60;
    public int MaxEventsPerWindow { get; init; } = 2500;
    public int PeriodCandidateLimit { get; init; } = 48;
    public int PairCandidateLag { get; init; } = 18;
    public int AnchorLimit { get; init; } = 40;

    public void Validate()
    {
        if (MinMatches < 4 || MinDistinctQuantities < 2 ||
            MinDistinctQuantities > MinMatches ||
            MinCoverage <= 0 || MinCoverage > 1 ||
            MinimumPeriodMs < 100 || MaximumPeriodMs < MinimumPeriodMs ||
            PeriodGridMs <= 0 || MinTimeToleranceMs < 0 ||
            MaxTimeToleranceMs < MinTimeToleranceMs ||
            RelativeTolerance is < 0 or > 0.25 ||
            MaxCycleGap < 1 || AnalysisWindowMinutes is < 1 or > 1440 ||
            MaxEventsPerWindow < MinMatches ||
            PeriodCandidateLimit < 1 || PairCandidateLag < 1 || AnchorLimit < 1)
            throw new ArgumentException("Invalid experimental variable-size screen configuration.");
    }
}

public sealed record VariableCadenceHypothesis(
    string PatternId,
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string ReportedDirection,
    string TradingMode,
    string SessionId,
    string FirstObservedUtc,
    string LastObservedUtc,
    int PeriodMs,
    int MatchedPrints,
    int ExpectedCycles,
    int MissedCycles,
    int DistinctQuantities,
    long SmallestQuantityLots,
    long LargestQuantityLots,
    long ObservedLots,
    double CoverageRatio,
    double MeanAbsTimingErrorMs,
    IReadOnlyList<string> EvidenceEventIds,
    string State,
    double? ConfidenceCalibrated,
    bool OwnerKnown,
    string Interpretation
);

public sealed record VariableCadenceReport(
    string SchemaVersion,
    string SourceSha256,
    int InputPrints,
    int CandidateSequenceCount,
    int SkippedDenseWindowCount,
    int UniqueAttributedPrints,
    bool PhysicalBotCountKnown,
    bool StatisticalSignificanceEstablished,
    IReadOnlyList<VariableCadenceHypothesis> Candidates,
    IReadOnlyList<string> Warnings,
    int SplitDenseWindowCount = 0,
    int SkippedTinyRemainderCount = 0
);

public static class VariableSizeCadence
{
    private sealed record Candidate(VariableCadenceHypothesis Pattern, double Score);

    public static VariableCadenceReport Detect(TradeImportResult source, VariableCadenceConfig config)
    {
        config.Validate();
        var warnings = new List<string>
        {
            "RESEARCH_ONLY: time-regular prints with different lot sizes are not identified trading programs.",
            "NO_OWNER_ORDER_IDS: publicly observed prints do not identify parents, algorithms or physical traders.",
            "NO_CONFIDENCE_CALIBRATION: candidate periods must be tested against burst/clock-dependent nulls and future data.",
            "WINDOW_EPISODES: source/window segmentation can split a single hidden execution algorithm into multiple candidates.",
            "SIDE_IS_REPORTED: do not infer a passive-order owner's side from the reported trade direction.",
            "CHUNKED_DENSE_WINDOWS: one program spanning two capped chunks may become two observed sequences."
        };
        var all = new List<Candidate>();
        int skipped = 0, split = 0, tinyRemainders = 0;
        long windowMs = config.AnalysisWindowMinutes * 60_000L;
        var groups = source.Trades
            .Where(t => t.ReportedDirection is "BUY" or "SELL")
            .GroupBy(t => (t.InstrumentUid, t.TradeSource, t.ReportedDirection,
                           t.TradingMode, t.SessionId,
                           Window: t.ExchangeTimeUtc.ToUnixTimeMilliseconds() / windowMs))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.ReportedDirection, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal)
            .ThenBy(g => g.Key.Window);
        foreach (var group in groups)
        {
            var events = group.OrderBy(t => t.ExchangeTimeUtc)
                .ThenBy(t => t.ArrivalSequence).ToArray();
            if (events.Length < config.MinMatches) continue;
            if (events.Length > config.MaxEventsPerWindow)
            {
                split++;
                warnings.Add($"DENSE_WINDOW_SPLIT: uid={group.Key.InstrumentUid}, " +
                    $"source={group.Key.TradeSource}, mode={group.Key.TradingMode}, " +
                    $"window={group.Key.Window}, count={events.Length}, maxChunk={config.MaxEventsPerWindow}; " +
                    "time/evidence continuity across chunks is not evaluated.");
            }
            for (int offset = 0; offset < events.Length; offset += config.MaxEventsPerWindow)
            {
                int chunkCount = Math.Min(config.MaxEventsPerWindow, events.Length - offset);
                if (chunkCount < config.MinMatches)
                {
                    tinyRemainders++;
                    warnings.Add($"TINY_CHUNK_NOT_EVALUATED: uid={group.Key.InstrumentUid}, " +
                        $"window={group.Key.Window}, trailingPrints={chunkCount}");
                    break;
                }
                var chunk = new MarketTrade[chunkCount];
                Array.Copy(events, offset, chunk, 0, chunkCount);
                var periods = ProposePeriods(chunk, config);
                foreach (int period in periods)
                {
                    int n = Math.Min(chunk.Length, config.AnchorLimit);
                    for (int i = 0; i < n; i++)
                    {
                        var candidate = Evaluate(chunk, i, period, config);
                        if (candidate is not null) all.Add(candidate);
                    }
                }
            }
        }

        var ids = new HashSet<string>(StringComparer.Ordinal);
        var chosen = new List<VariableCadenceHypothesis>();
        foreach (var c in all.OrderByDescending(x => x.Score)
                     .ThenByDescending(x => x.Pattern.PeriodMs)
                     .ThenBy(x => x.Pattern.FirstObservedUtc, StringComparer.Ordinal)
                     .ThenBy(x => x.Pattern.PatternId, StringComparer.Ordinal))
        {
            if (c.Pattern.EvidenceEventIds.Any(ids.Contains)) continue;
            chosen.Add(c.Pattern);
            foreach (string id in c.Pattern.EvidenceEventIds) ids.Add(id);
        }
        chosen = chosen
            .OrderBy(x => x.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(x => x.TradeSource, StringComparer.Ordinal)
            .ThenBy(x => x.SessionId, StringComparer.Ordinal)
            .ThenBy(x => x.FirstObservedUtc, StringComparer.Ordinal)
            .ThenBy(x => x.PatternId, StringComparer.Ordinal)
            .ToList();

        return new VariableCadenceReport(
            "0.2-experimental", source.FileSha256, source.Trades.Count,
            chosen.Count, skipped, ids.Count, false, false, chosen, warnings,
            split, tinyRemainders);
    }

    private static IReadOnlyList<int> ProposePeriods(
        IReadOnlyList<MarketTrade> events, VariableCadenceConfig config)
    {
        var counts = new Dictionary<int, int>();
        int len = Math.Min(events.Count, 450);
        for (int i = 0; i < len; i++)
        {
            for (int j = i + 1; j < Math.Min(len, i + config.PairCandidateLag + 1); j++)
            {
                double delta = (events[j].ExchangeTimeUtc - events[i].ExchangeTimeUtc).TotalMilliseconds;
                if (delta <= 0) continue;
                for (int divisor = 1; divisor <= config.MaxCycleGap; divisor++)
                {
                    double p = delta / divisor;
                    if (p < config.MinimumPeriodMs || p > config.MaximumPeriodMs) continue;
                    int ms = (int)(Math.Round(p / config.PeriodGridMs,
                        MidpointRounding.AwayFromZero) * config.PeriodGridMs);
                    if (ms < config.MinimumPeriodMs || ms > config.MaximumPeriodMs) continue;
                    counts[ms] = counts.GetValueOrDefault(ms) + 1;
                }
            }
        }
        return counts.OrderByDescending(x => x.Value)
            .ThenByDescending(x => x.Key)
            .Take(config.PeriodCandidateLimit)
            .Select(x => x.Key).ToArray();
    }

    private static Candidate? Evaluate(
        IReadOnlyList<MarketTrade> events, int anchorIndex, int periodMs, VariableCadenceConfig config)
    {
        var anchor = events[anchorIndex].ExchangeTimeUtc;
        double tolerance = Math.Max(config.MinTimeToleranceMs,
            Math.Min(config.MaxTimeToleranceMs, periodMs * config.RelativeTolerance));
        var byCycle = new SortedDictionary<int, (MarketTrade Trade, double ErrorMs)>();
        for (int i = anchorIndex; i < events.Count; i++)
        {
            var item = events[i];
            double elapsed = (item.ExchangeTimeUtc - anchor).TotalMilliseconds;
            int cycle = checked((int)Math.Round(elapsed / periodMs, MidpointRounding.AwayFromZero));
            if (cycle < 0) continue;
            double error = Math.Abs(elapsed - cycle * (double)periodMs);
            if (error > tolerance) continue;
            if (!byCycle.TryGetValue(cycle, out var prev) ||
                error < prev.ErrorMs ||
                (error == prev.ErrorMs && item.ArrivalSequence < prev.Trade.ArrivalSequence))
                byCycle[cycle] = (item, error);
        }
        if (!byCycle.ContainsKey(0) || byCycle.Count < config.MinMatches) return null;
        var consecutive = new List<(int Cycle, MarketTrade Trade, double ErrorMs)>();
        int? lastCycle = null;
        foreach (var e in byCycle)
        {
            if (lastCycle.HasValue && e.Key - lastCycle.Value > config.MaxCycleGap)
                break;
            consecutive.Add((e.Key, e.Value.Trade, e.Value.ErrorMs));
            lastCycle = e.Key;
        }
        if (consecutive.Count < config.MinMatches) return null;
        int expected = consecutive[^1].Cycle + 1;
        double coverage = (double)consecutive.Count / expected;
        if (coverage < config.MinCoverage) return null;
        int sizes = consecutive.Select(x => x.Trade.QuantityLots).Distinct().Count();
        if (sizes < config.MinDistinctQuantities) return null;

        var prints = consecutive.Select(e => e.Trade).ToArray();
        double meanError = consecutive.Average(e => e.ErrorMs);
        string identity = string.Join("|", prints[0].InstrumentUid,
            prints[0].TradeSource, prints[0].ReportedDirection, prints[0].TradingMode,
            prints[0].SessionId, periodMs, string.Join(",", prints.Select(x => x.EventId)));
        string id = Convert.ToHexString(
            SHA256.HashData(Encoding.UTF8.GetBytes(identity)))[..16].ToLowerInvariant();
        var hypothesis = new VariableCadenceHypothesis(id, prints[0].InstrumentUid,
            prints[0].Ticker, prints[0].TradeSource, prints[0].ReportedDirection,
            prints[0].TradingMode, prints[0].SessionId,
            prints[0].ExchangeTimeUtc.ToUniversalTime().ToString("O"),
            prints[^1].ExchangeTimeUtc.ToUniversalTime().ToString("O"),
            periodMs, prints.Length, expected, expected - prints.Length,
            sizes, prints.Min(x => x.QuantityLots), prints.Max(x => x.QuantityLots),
            prints.Sum(x => x.QuantityLots), coverage, meanError,
            prints.Select(x => x.EventId).ToArray(),
            "candidate", null, false,
            "Same-source time-regular varied quantities; not a parent order, identified bot or validated signal.");
        double rank = consecutive.Count * coverage + Math.Min(sizes, 10) * 0.01 -
                      meanError / Math.Max(tolerance, 1) * 0.05;
        return new Candidate(hypothesis, rank);
    }
}
