namespace RobotDetector.Core;

/// <summary>
/// Exploratory negative control: shuffle trade SIZE labels within local
/// (instrument/source/direction/mode/session/time-bin) blocks, retaining
/// timestamp, price, direction and the complete original event sequence.
/// This null is NOT calibrated significance or evidence of an actual owner.
/// </summary>
public sealed record SizeShuffleTrial(int Seed, int ShuffledTradeCount,
    int NullCandidateEpisodes, int UniqueEvidencePrints);

public sealed record SizeShuffleReport(
    string SchemaVersion,
    string NullFamily,
    string SourceSha256,
    int OriginalPrintCount,
    int OriginalCandidateEpisodes,
    int LocalWindowSeconds,
    int NullTrials,
    double NullMeanCandidateEpisodes,
    double NullMaximumCandidateEpisodes,
    double? EmpiricalGlobalTailProbability,
    IReadOnlyList<SizeShuffleTrial> Trials,
    IReadOnlyList<string> Limitations
);

public static class SizeShuffleNull
{
    public static SizeShuffleReport Compare(TradeImportResult original, DetectorConfig config,
        int trials = 10, int seed = 42, int localWindowSeconds = 60)
    {
        config.Validate();
        if (trials is < 1 or > 100)
            throw new ArgumentOutOfRangeException(nameof(trials), "Use 1..100 shuffles.");
        if (localWindowSeconds is < 1 or > 3600)
            throw new ArgumentOutOfRangeException(nameof(localWindowSeconds));
        if (original.Trades.Count > 250_000)
            throw new ArgumentException("For larger inputs, explicitly split by instrument/date.");

        var observed = PeriodicDetector.Detect(original, config);
        var nullResults = new List<SizeShuffleTrial>();
        for (int trial = 0; trial < trials; trial++)
        {
            int effectiveSeed = unchecked(seed + trial * 1009);
            var shuffled = Shuffle(original, effectiveSeed, localWindowSeconds);
            var report = PeriodicDetector.Detect(shuffled.Tape, config);
            int count = report.Patterns.SelectMany(p => p.EvidenceEventIds)
                .Distinct(StringComparer.Ordinal).Count();
            nullResults.Add(new SizeShuffleTrial(effectiveSeed, shuffled.ChangedTradeCount,
                report.CandidatePatternCount, count));
        }

        double mean = nullResults.Average(x => x.NullCandidateEpisodes);
        double maximum = nullResults.Max(x => x.NullCandidateEpisodes);
        // This is a descriptive global count comparison, NOT a per-hypothesis
        // p-value or calibrated false discovery probability. In particular,
        // the null does not preserve all features of real order-flow dynamics.
        double? tail = nullResults.All(x => x.ShuffledTradeCount > 0)
            ? (1.0 + nullResults.Count(x => x.NullCandidateEpisodes >= observed.CandidatePatternCount))
                / (trials + 1.0)
            : null;

        var limitations = new List<string>
        {
            "EXPLORATORY_ONLY: this is a conditional size-label shuffle, not calibrated bot-detection significance.",
            "Preserves timestamps and the total size distribution of each local block, but not size autocorrelation or individual order splitting.",
            "The original pattern count and shuffled pattern counts are dependent on detector version, episode boundaries and configuration.",
            "A global candidate-count tail frequency does NOT estimate per-pattern false discovery rates, real number of bots, or investor identities.",
            "A small number of null trials has poor p-value resolution and should not be used as an investment signal.",
            "The source completeness, market session mapping, and direction semantics remain unverified unless independently established."
        };
        if (nullResults.Any(x => x.ShuffledTradeCount == 0))
            limitations.Add("UNINFORMATIVE_NULL: one or more shuffles moved no size labels; no tail estimate is produced.");
        return new SizeShuffleReport("0.1-exploratory", "local_trade_quantity_shuffle",
            original.FileSha256, original.Trades.Count,
            observed.CandidatePatternCount, localWindowSeconds, trials,
            mean, maximum, tail, nullResults, limitations);
    }

    public static (TradeImportResult Tape, int ChangedTradeCount) Shuffle(
        TradeImportResult original, int seed, int localWindowSeconds)
    {
        if (localWindowSeconds < 1) throw new ArgumentOutOfRangeException(nameof(localWindowSeconds));
        var random = new Random(seed);
        var events = original.Trades.ToArray();
        int changed = 0;
        // Sort group traversal for repeatable PRNG sequence across OS/runtime.
        var groups = events.Select((trade, index) => (trade, index))
            .GroupBy(x => (
                x.trade.InstrumentUid, x.trade.TradeSource, x.trade.ReportedDirection,
                x.trade.TradingMode, x.trade.SessionId,
                TimeBlock: x.trade.ExchangeTimeUtc.ToUnixTimeSeconds() / localWindowSeconds))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.ReportedDirection, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TimeBlock);
        foreach (var g in groups)
        {
            var idx = g.Select(x => x.index).ToArray();
            if (idx.Length < 2) continue;
            var amounts = idx.Select(i => events[i].QuantityLots).ToArray();
            for (int i = amounts.Length - 1; i > 0; i--)
            {
                int j = random.Next(i + 1);
                (amounts[i], amounts[j]) = (amounts[j], amounts[i]);
            }
            for (int i = 0; i < idx.Length; i++)
            {
                if (events[idx[i]].QuantityLots != amounts[i]) changed++;
                events[idx[i]] = events[idx[i]] with { QuantityLots = amounts[i] };
            }
        }
        // Preserve full market event timestamps, source and IDs. The synthetic
        // shuffle is never written back to the immutable original raw file.
        var tape = new TradeImportResult(events, original.RejectedRows,
            original.FileName, original.FileSha256 + ":shuffle:" + seed,
            original.HasVerifiedFeedCoverage, original.RejectedRowTotal);
        return (tape, changed);
    }
}
