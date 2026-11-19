namespace RobotDetector.Core;

/// <summary>
/// Market-wide clock synchrony diagnostic. Not an individual trader classifier.
/// Clock-phase null: each UTC minute receives a shared, random 1..999 ms phase
/// rotation, preserving the original within-minute spacings up to circular wrap.
/// </summary>
public sealed class ClockPhaseConfig
{
    public int FirstMilliseconds { get; init; } = 100;
    public int MinPrintsPerGroup { get; init; } = 100;
    public int NullTrials { get; init; } = 99;
    public int Seed { get; init; } = 20261119;

    public void Validate()
    {
        if (FirstMilliseconds is < 1 or > 500 ||
            MinPrintsPerGroup is < 1 or > 1_000_000 ||
            NullTrials is < 1 or > 1000)
            throw new ArgumentException("Invalid market-clock phase analysis settings.");
    }
}

public sealed record ClockPhasePeakControl(
    int Peak100MsBin,
    int ObservedPeakBinCount,
    double ObservedPeakBinShare,
    double? NullMeanMaximumBinShare,
    double? Null95MaximumBinShare,
    double? DescriptiveAnyBinTailFrequency,
    IReadOnlyList<int> RotatedMaximumBinCounts
);

public sealed record ClockPhaseGroup(
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string TradingMode,
    string SessionId,
    int PublicPrintCount,
    int UtcMinuteBlocks,
    int FirstMilliseconds,
    int PrintsInFirstMilliseconds,
    double ObservedFirstPhaseShare,
    IReadOnlyList<int> PhaseHistogram100Ms,
    bool EligibleForControls,
    double? NullMeanFirstPhaseShare,
    double? Null95FirstPhaseShare,
    double? DescriptiveGlobalTailFrequency,
    IReadOnlyList<int> RotatedControlCounts,
    bool FeedCoverageVerified,
    string Interpretation,
    ClockPhasePeakControl MaximumBinControl
);

public sealed record ClockPhaseReport(
    string SchemaVersion,
    string SourceSha256,
    int InputPrints,
    int SourceGroups,
    int EligibleSourceGroups,
    int IneligibleSourceGroups,
    int FirstMilliseconds,
    int NullTrials,
    bool OwnerCountKnown,
    bool StatisticalSignificanceEstablished,
    IReadOnlyList<ClockPhaseGroup> Groups,
    IReadOnlyList<string> Warnings
);

public static class ClockPhaseAudit
{
    public static ClockPhaseReport Analyse(TradeImportResult source, ClockPhaseConfig? config = null)
    {
        config ??= new ClockPhaseConfig();
        config.Validate();

        var groups = source.Trades
            .GroupBy(t => (t.InstrumentUid, t.TradeSource, t.TradingMode, t.SessionId))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal)
            .ToArray();
        var results = new List<ClockPhaseGroup>(groups.Length);
        int groupIndex = 0;
        foreach (var group in groups)
        {
            // Millisecond phase is sufficient for this prespecified 100ms-bin
            // diagnostic, but retain original sub-ms timestamps in source data.
            var minuteToPhases = new SortedDictionary<long, List<int>>();
            var histogram = new int[10];
            int hits = 0;
            var first = group.First();
            foreach (var trade in group)
            {
                long utcTicks = trade.ExchangeTimeUtc.ToUniversalTime().Ticks;
                long minute = utcTicks / TimeSpan.TicksPerMinute;
                int phase = checked((int)((utcTicks % TimeSpan.TicksPerSecond) /
                    TimeSpan.TicksPerMillisecond));
                if (phase < config.FirstMilliseconds) hits++;
                histogram[phase / 100]++;
                if (!minuteToPhases.TryGetValue(minute, out var phases))
                {
                    phases = new List<int>();
                    minuteToPhases.Add(minute, phases);
                }
                phases.Add(phase);
            }

            int n = group.Count();
            bool eligible = n >= config.MinPrintsPerGroup && minuteToPhases.Count >= 2;
            int observedPeakCount = histogram.Max();
            int observedPeakIndex = Array.IndexOf(histogram, observedPeakCount);
            int[] controls = Array.Empty<int>();
            int[] maxBinControls = Array.Empty<int>();
            double? nullMean = null, null95 = null, tail = null;
            double? maxMean = null, max95 = null, maxTail = null;
            if (eligible)
            {
                var minuteArrays = minuteToPhases.Values.Select(x => x.ToArray()).ToArray();
                controls = new int[config.NullTrials];
                maxBinControls = new int[config.NullTrials];
                for (int trial = 0; trial < config.NullTrials; trial++)
                {
                    var rng = new Random(unchecked(config.Seed + groupIndex * 1_000_003 +
                        trial * 1_009));
                    int count = 0;
                    var rotatedHistogram = new int[10];
                    foreach (int[] minutePhases in minuteArrays)
                    {
                        // Shared offset within the minute: retains relative
                        // local bursts, unlike independent per-print resampling.
                        int shiftMs = rng.Next(1, 1000);
                        foreach (int phase in minutePhases)
                        {
                            int shiftedPhaseMs = (phase + shiftMs) % 1000;
                            rotatedHistogram[shiftedPhaseMs / 100]++;
                            if (shiftedPhaseMs < config.FirstMilliseconds) count++;
                        }
                    }
                    controls[trial] = count;
                    // Use the maximum over all ten bins for EACH null trial,
                    // not the first-bin null after observing which bin peaks.
                    maxBinControls[trial] = rotatedHistogram.Max();
                }
                nullMean = controls.Average(x => (double)x / n);
                var sorted = controls.OrderBy(x => x).ToArray();
                int percentileIndex = Math.Max(0, (int)Math.Ceiling(0.95 * sorted.Length) - 1);
                null95 = (double)sorted[percentileIndex] / n;
                tail = (1.0 + controls.Count(x => x >= hits)) / (config.NullTrials + 1.0);
                maxMean = maxBinControls.Average(x => (double)x / n);
                int[] sortedMax = maxBinControls.OrderBy(x => x).ToArray();
                max95 = (double)sortedMax[percentileIndex] / n;
                maxTail = (1.0 + maxBinControls.Count(x => x >= observedPeakCount)) /
                    (config.NullTrials + 1.0);
            }

            results.Add(new ClockPhaseGroup(
                group.Key.InstrumentUid, first.Ticker, group.Key.TradeSource,
                group.Key.TradingMode, group.Key.SessionId, n,
                minuteToPhases.Count, config.FirstMilliseconds, hits, (double)hits / n,
                histogram, eligible, nullMean, null95, tail, controls,
                source.HasVerifiedFeedCoverage,
                "Common absolute-second alignment in public prints, NOT a distinct execution bot.",
                new ClockPhasePeakControl(observedPeakIndex, observedPeakCount,
                    (double)observedPeakCount / n, maxMean, max95, maxTail,
                    maxBinControls)));
            groupIndex++;
        }

        return new ClockPhaseReport(
            "0.2-exploratory-market-clock", source.FileSha256, source.Trades.Count,
            results.Count, results.Count(x => x.EligibleForControls),
            results.Count(x => !x.EligibleForControls),
            config.FirstMilliseconds, config.NullTrials, false, false,
            results, new[]
            {
                "CLOCK_RHYTHM_NOT_OWNER: second-boundary timing may reflect market-wide execution scheduling and shared infrastructure.",
                "SHARED_MINUTE_ROTATION: the null rotates each UTC minute's whole cluster by one random millisecond phase.",
                "BURST_DEPENDENCE: within-minute relative timing is mostly retained, but wrap boundaries and cross-minute dynamics are altered.",
                "DESCRIPTIVE_FREQUENCY_ONLY: Monte Carlo exceedance is not a validated statistical p-value, per-bot confidence or FDR.",
                "MAXIMUM_BIN_CONTROL: after examining ten 100ms bins, use the maximum of those ten bins in EACH resampled trial.",
                "SELECTION_CORRECTED_STATISTIC_NOT_VALIDATED_NULL: matching max statistics handles bin selection but does not make minute rotations an exact exchange null.",
                "SECOND_CLOCK_AND_PRECISION: provider timestamp resolution, rounding and auction/halts require independent verification.",
                "SESSION_MODE_ISOLATION: never pool instruments, EXCHANGE/DEALER, trading modes or reported sessions.",
                "PHASE_HISTOGRAM_IS_AGGREGATE: no raw trade print identities or account information.",
                "READ_ONLY: no orders, tokens, portfolios or owner identification."
            });
    }
}
