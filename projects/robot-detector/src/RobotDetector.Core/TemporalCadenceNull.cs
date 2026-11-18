namespace RobotDetector.Core;

/// <summary>
/// Exploratory temporal controls for variable-size cadence detection.
/// Both preserve the number of prints and their sizes in each UTC block.
/// They are NOT validated exchange microstructure models.
/// </summary>
public sealed record TemporalNullTrial(
    int Seed, int ChangedPrintTimestamps, int CandidateSequences);

public sealed record TemporalNullReport(
    string SchemaVersion, string NullMode, string SourceSha256,
    int SourcePrintCount, int OriginalCandidateSequences,
    int TrialsRun, double MeanNullCandidateSequences,
    int MaximumNullCandidateSequences, double? DescriptiveGlobalTailFrequency,
    IReadOnlyList<TemporalNullTrial> Trials,
    bool ActualBotCountKnown, bool SignificanceCalibrated,
    IReadOnlyList<string> Warnings
);

public static class TemporalCadenceNull
{
    public static TemporalNullReport Compare(
        TradeImportResult source, VariableCadenceConfig config, string mode = "uniform",
        int trials = 10, int seed = 1701, int blockSeconds = 60)
    {
        config.Validate();
        Validate(mode, blockSeconds);
        if (trials is < 1 or > 100) throw new ArgumentOutOfRangeException(nameof(trials));
        if (source.Trades.Count > 250_000)
            throw new ArgumentException("Split oversized source by instrument/date.");

        var baseline = VariableSizeCadence.Detect(source, config);
        var checks = new List<TemporalNullTrial>();
        for (int trial = 0; trial < trials; trial++)
        {
            int currentSeed = unchecked(seed + 1009 * trial);
            var (shuffled, changed) = Resample(source, mode, currentSeed, blockSeconds);
            var report = VariableSizeCadence.Detect(shuffled, config);
            checks.Add(new TemporalNullTrial(currentSeed, changed, report.CandidateSequenceCount));
        }
        double? frequency = checks.All(x => x.ChangedPrintTimestamps > 0)
            ? (1.0 + checks.Count(t => t.CandidateSequences >= baseline.CandidateSequenceCount))
                / (trials + 1.0)
            : null;

        return new TemporalNullReport("0.1-exploratory", mode, source.FileSha256,
            source.Trades.Count, baseline.CandidateSequenceCount, checks.Count,
            checks.Average(t => t.CandidateSequences), checks.Max(t => t.CandidateSequences),
            frequency, checks, false, false,
            new[]
            {
                "TEMPORAL_NULL_IS_EXPERIMENTAL: neither clock resampling mode establishes statistically valid bot detection.",
                "WITHIN_BLOCK_COUNTS: per-minute trade counts, direction, quantities, source and trading session are preserved.",
                mode == "uniform"
                    ? "UNIFORM_CLOCK: redistributes prints uniformly within a minute, destroying much realistic burstiness."
                    : "ROTATED_CLOCK: preserves relative within-minute gaps but changes cross-minute phase and clock anchoring.",
                "DEPENDENT_CANDIDATES: a global candidate-count tail frequency is not a per-pattern p-value or FDR.",
                "NO_OWNER_IDENTITY: a sequence of variable trade quantities is not an identified robot, account or parent order.",
                "NO_INSTRUMENT_QUALITY_CLAIM: observations and stream completeness are not independently established."
            });
    }

    public static (TradeImportResult Tape, int ChangedPrintTimestamps) Resample(
        TradeImportResult source, string mode, int seed, int blockSeconds = 60)
    {
        Validate(mode, blockSeconds);
        long blockTicks = checked((long)blockSeconds * TimeSpan.TicksPerSecond);
        var random = new Random(seed);
        var values = source.Trades.ToArray();
        int changed = 0;
        var groups = values.Select((print, index) => (print, index))
            .GroupBy(x => (
                x.print.InstrumentUid, x.print.TradeSource, x.print.ReportedDirection,
                x.print.TradingMode, x.print.SessionId,
                Block: x.print.ExchangeTimeUtc.ToUniversalTime().Ticks / blockTicks))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.ReportedDirection, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal)
            .ThenBy(g => g.Key.Block);
        foreach (var group in groups)
        {
            long startTicks = checked(group.Key.Block * blockTicks);
            long rotation = mode == "rotate" ? random.NextInt64(1, blockTicks) : 0;
            foreach (var entry in group)
            {
                long originalTicks = values[entry.index].ExchangeTimeUtc.ToUniversalTime().Ticks;
                long relative = originalTicks - startTicks;
                long newRelative = mode == "rotate"
                    ? (relative + rotation) % blockTicks
                    : random.NextInt64(blockTicks);
                long shiftedTicks = checked(startTicks + newRelative);
                var shifted = new DateTimeOffset(shiftedTicks, TimeSpan.Zero);
                if (shiftedTicks != originalTicks) changed++;
                values[entry.index] = values[entry.index] with
                {
                    ExchangeTimeUtc = shifted
                };
            }
        }
        Array.Sort(values, (a, b) =>
        {
            int time = a.ExchangeTimeUtc.CompareTo(b.ExchangeTimeUtc);
            return time == 0 ? a.ArrivalSequence.CompareTo(b.ArrivalSequence) : time;
        });
        return (new TradeImportResult(values, source.RejectedRows, source.FileName,
                source.FileSha256 + ":temporal-null:" + mode + ":" + seed,
                source.HasVerifiedFeedCoverage, source.RejectedRowTotal), changed);
    }

    private static void Validate(string mode, int blockSeconds)
    {
        if (mode is not ("uniform" or "rotate"))
            throw new ArgumentException("Temporal null mode must be uniform or rotate.");
        if (blockSeconds is < 1 or > 3600)
            throw new ArgumentException("Temporal-null block must be between 1 and 3600 seconds.");
    }
}
