namespace RobotDetector.Core;

/// <summary>
/// Read-only exchange timestamp granularity and collision diagnostics.
/// Identical timestamps/price are not duplicate trades and never merged.
/// They do not reveal child or parent order identity.
/// </summary>
public sealed record TimestampQualityGroup(
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string TradingMode,
    string SessionId,
    int PublicPrintCount,
    int UniqueTimestampCount,
    int SameTimestampClusters,
    int PrintsInSameTimestampClusters,
    int MaxPrintsAtSameTimestamp,
    int PrintsInSameTimestampAndPriceClusters,
    int WholeSecondTimestampPrints,
    int Whole100MillisecondTimestampPrints,
    int Whole10MillisecondTimestampPrints,
    int WholeMillisecondTimestampPrints,
    int SubMillisecondTimestampPrints,
    int NotMicrosecondAlignedPrints,
    double SameTimestampClusterPrintShare,
    double WholeMillisecondPrintShare,
    double SubMillisecondPrintShare,
    double? SmallestPositiveGapMicroseconds,
    int DistinctUtcMinuteBlocks,
    bool FeedCoverageVerified,
    bool SourceTimestampPrecisionVerified,
    string Interpretation
);

public sealed record TimestampQualityReport(
    string SchemaVersion,
    string SourceSha256,
    int SourcePrints,
    int SourceGroups,
    bool OwnerCountKnown,
    bool SourceTimestampPrecisionVerified,
    bool FeedCoverageVerified,
    bool StatisticalSignificanceEstablished,
    IReadOnlyList<TimestampQualityGroup> Groups,
    IReadOnlyList<string> Warnings
);

public static class TimestampQualityAudit
{
    public static TimestampQualityReport Describe(TradeImportResult source)
    {
        var output = new List<TimestampQualityGroup>();
        foreach (var group in source.Trades
            .GroupBy(t => (t.InstrumentUid, t.TradeSource, t.TradingMode, t.SessionId))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal))
        {
            var prints = group.ToArray();
            long[] times = prints.Select(t => t.ExchangeTimeUtc.ToUniversalTime().Ticks)
                .OrderBy(t => t).ToArray();
            int n = times.Length;
            int wholeSec = 0, whole100ms = 0, whole10ms = 0,
                wholeMs = 0, subMs = 0, nonMicro = 0;
            long[] uniqueTimes = times.Distinct().ToArray();
            long? minPositiveGap = null;
            for (int i = 1; i < uniqueTimes.Length; i++)
            {
                long gap = uniqueTimes[i] - uniqueTimes[i - 1];
                if (gap <= 0) throw new InvalidDataException("Sorted distinct timestamp sequence is invalid.");
                if (!minPositiveGap.HasValue || gap < minPositiveGap.Value)
                    minPositiveGap = gap;
            }
            foreach (long ticks in times)
            {
                if (ticks % TimeSpan.TicksPerSecond == 0) wholeSec++;
                if (ticks % (100L * TimeSpan.TicksPerMillisecond) == 0) whole100ms++;
                if (ticks % (10L * TimeSpan.TicksPerMillisecond) == 0) whole10ms++;
                if (ticks % TimeSpan.TicksPerMillisecond == 0) wholeMs++;
                else subMs++;
                // 1us is 10 ticks, while DateTimeOffset ticks are 100ns.
                if (ticks % 10L != 0) nonMicro++;
            }
            var timestampClusterSizes = prints.GroupBy(
                    t => t.ExchangeTimeUtc.ToUniversalTime().Ticks)
                .Select(g => g.Count()).ToArray();
            int clustered = timestampClusterSizes.Where(x => x >= 2).Sum();
            int clusters = timestampClusterSizes.Count(x => x >= 2);
            int maxCluster = timestampClusterSizes.Max();
            int sameTimePrice = prints.GroupBy(
                    t => (t.ExchangeTimeUtc.ToUniversalTime().Ticks, t.Price))
                .Select(g => g.Count()).Where(x => x >= 2).Sum();
            int minuteBlocks = uniqueTimes.Select(t => t / TimeSpan.TicksPerMinute)
                .Distinct().Count();
            output.Add(new TimestampQualityGroup(
                group.Key.InstrumentUid, prints[0].Ticker,
                group.Key.TradeSource, group.Key.TradingMode, group.Key.SessionId,
                n, uniqueTimes.Length, clusters, clustered,
                maxCluster, sameTimePrice, wholeSec, whole100ms, whole10ms,
                wholeMs, subMs, nonMicro, (double)clustered / n,
                (double)wholeMs / n, (double)subMs / n,
                minPositiveGap.HasValue ? minPositiveGap.Value / 10.0 : null,
                minuteBlocks, source.HasVerifiedFeedCoverage, false,
                "Timestamp granularity and simultaneous public prints, not owner/order IDs."));
        }
        return new TimestampQualityReport(
            "0.1-exploratory-timestamp-quality", source.FileSha256,
            source.Trades.Count, output.Count, false,
            false, source.HasVerifiedFeedCoverage, false,
            output, new[]
            {
                "TIMESTAMP_COLLISIONS_ARE_NOT_DUPLICATES: distinct exchange executions may have identical vendor timestamps and price.",
                "SOURCE_RESOLUTION_UNKNOWN: observed multiples of milliseconds or microseconds do not verify exchange or vendor clock precision.",
                "BATCH_OR_FILL_AMBIGUITY: one owner, many owners, partial fills and vendor grouping are observationally confounded.",
                "NO_TIMESTAMP_REPAIR: never rewrite/deduplicate original public prints based solely on a shared timestamp.",
                "EXCHANGE_DEALER_ISOLATION: compare each instrument, trade source, mode and session separately.",
                "DATA_COVERAGE_UNKNOWN: a historical archive does not prove no missing records, corrections, venue halts or auction artifacts.",
                "READ_ONLY: no account data, market orders, private identifiers, calibrated confidence or actual bot count."
            });
    }
}
