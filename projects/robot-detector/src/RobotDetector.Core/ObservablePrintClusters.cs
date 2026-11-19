using System.Security.Cryptography;
using System.Text;

namespace RobotDetector.Core;

/// <summary>
/// An OPTIONAL derived view of raw anonymous exchange prints, NOT economic
/// parent orders. Raw trade prints remain immutable, uniquely traceable and
/// are never deduplicated or destroyed.
/// </summary>
public sealed record ObservablePrintCluster(
    string ClusterId,
    string InstrumentUid,
    string TradeSource,
    string ReportedDirection,
    string TradingMode,
    string SessionId,
    DateTimeOffset ExchangeTimeUtc,
    decimal Price,
    int PublicPrintCount,
    long TotalLots,
    IReadOnlyList<string> OriginalPublicEventIds
);

public sealed record PrintClusterSummary(
    string SchemaVersion,
    string SourceSha256,
    string DerivedTapeProvenanceSha256,
    int SourcePublicPrints,
    int DerivedObservableClusters,
    int MultiPrintClusters,
    int SourcePrintsInMultiPrintClusters,
    long TotalSourceLots,
    long TotalDerivedLots,
    bool SourceEventsAllTraceable,
    bool ActualParentOrderKnown,
    bool ActualBotCountKnown,
    bool StatisticalSignificanceEstablished,
    IReadOnlyList<string> Warnings
);

public sealed record ObservableClusterTape(
    TradeImportResult DerivedTape,
    IReadOnlyList<ObservablePrintCluster> Clusters,
    PrintClusterSummary Summary
);

public sealed record ClusterCandidateComparison(
    string SchemaVersion,
    string OriginalSourceSha256,
    string DerivedProvenanceSha256,
    int OriginalPublicPrints,
    int DerivedObservableClusters,
    int PublicPrintsInMultiPrintClusters,
    int OriginalFixedSizeCandidateEpisodes,
    int DerivedClusterSizeCandidateEpisodes,
    long OriginalTotalLots,
    long DerivedTotalLots,
    bool ActualParentOrdersIdentified,
    bool PhysicalBotCountKnown,
    bool StatisticalSignificanceEstablished,
    IReadOnlyList<string> Warnings
);

public static class ObservablePrintClusters
{
    public static ObservableClusterTape Build(TradeImportResult source)
    {
        var originalIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (var trade in source.Trades)
        {
            if (string.IsNullOrWhiteSpace(trade.EventId) || !originalIds.Add(trade.EventId))
                throw new InvalidDataException("Original print IDs must be present and unique.");
            if (trade.QuantityLots <= 0)
                throw new InvalidDataException("Print lot size must be positive.");
        }

        var groups = source.Trades
            .GroupBy(t => (
                t.InstrumentUid,
                t.TradeSource,
                t.ReportedDirection,
                t.TradingMode,
                t.SessionId,
                UtcTicks: t.ExchangeTimeUtc.ToUniversalTime().Ticks,
                t.Price))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal)
            .ThenBy(g => g.Key.UtcTicks)
            .ThenBy(g => g.Key.Price)
            .ThenBy(g => g.Key.ReportedDirection, StringComparer.Ordinal);

        var clusters = new List<ObservablePrintCluster>();
        var derived = new List<MarketTrade>();
        var assigned = new HashSet<string>(StringComparer.Ordinal);
        var generated = new HashSet<string>(StringComparer.Ordinal);
        int sourceInMulti = 0, multi = 0;
        long rawLots = 0, derivedLots = 0;
        foreach (var t in source.Trades)
            rawLots = checked(rawLots + t.QuantityLots);

        foreach (var g in groups)
        {
            var members = g.OrderBy(t => t.ArrivalSequence)
                .ThenBy(t => t.EventId, StringComparer.Ordinal).ToArray();
            foreach (var item in members)
            {
                if (!assigned.Add(item.EventId))
                    throw new InvalidDataException("Original event would be attributed to multiple groups.");
            }
            long lots = 0;
            foreach (var m in members) lots = checked(lots + m.QuantityLots);
            derivedLots = checked(derivedLots + lots);
            if (members.Length >= 2)
            {
                multi++;
                sourceInMulti = checked(sourceInMulti + members.Length);
            }

            string stableKey = string.Join("|", g.Key.InstrumentUid, g.Key.TradeSource,
                g.Key.ReportedDirection, g.Key.TradingMode, g.Key.SessionId,
                g.Key.UtcTicks, g.Key.Price,
                string.Join(",", members.Select(t => t.EventId).OrderBy(x => x, StringComparer.Ordinal)));
            string id = "CLUSTER_" + Convert.ToHexString(
                SHA256.HashData(Encoding.UTF8.GetBytes(stableKey)))[..20];
            if (!generated.Add(id))
                throw new InvalidDataException("Derived cluster identity collision.");
            var cluster = new ObservablePrintCluster(id, g.Key.InstrumentUid,
                g.Key.TradeSource, g.Key.ReportedDirection, g.Key.TradingMode,
                g.Key.SessionId, new DateTimeOffset(g.Key.UtcTicks, TimeSpan.Zero),
                g.Key.Price, members.Length, lots,
                members.Select(t => t.EventId).ToArray());
            clusters.Add(cluster);
            var first = members[0];
            derived.Add(new MarketTrade(
                id, cluster.ExchangeTimeUtc, first.InstrumentUid, first.Ticker,
                first.TradeSource, first.ReportedDirection, first.Price, lots,
                first.TradingMode, first.SessionId, "DERIVED_PUBLIC_PRINT_CLUSTER",
                members.Min(t => t.ArrivalSequence)));
        }

        if (assigned.Count != source.Trades.Count || rawLots != derivedLots ||
            derived.Count != clusters.Count)
            throw new InvalidDataException("Derived grouping lost prints or changed total lots.");

        derived.Sort((a, b) =>
        {
            int t = a.ExchangeTimeUtc.CompareTo(b.ExchangeTimeUtc);
            if (t != 0) return t;
            int seq = a.ArrivalSequence.CompareTo(b.ArrivalSequence);
            return seq != 0 ? seq : string.CompareOrdinal(a.EventId, b.EventId);
        });

        string derivedSha = Convert.ToHexString(
            SHA256.HashData(Encoding.UTF8.GetBytes(
                source.FileSha256 + "|exact_time_price_side_source_mode_session_cluster_v1")))
            .ToLowerInvariant();
        var derivedTape = new TradeImportResult(derived, source.RejectedRows,
            source.FileName + ":DERIVED_OBSERVABLE_CLUSTER",
            derivedSha, source.HasVerifiedFeedCoverage, source.RejectedRowTotal);
        var warnings = new[]
        {
            "DERIVED_ANALYTICAL_VIEW: every cluster is a group of public prints, NOT an identified parent order.",
            "CLUSTER_BY_EXACT_TIME_PRICE_SIDE_SOURCE_MODE_SESSION: identical timestamps alone never justify deduplication.",
            "RAW_EVENTS_IMMUTABLE: all original public event IDs remain traceable in the in-memory cluster mapping.",
            "NO_OWNER_OR_ORDER_IDS: one or many market participants could account for any cluster.",
            "MODEL_SENSITIVITY: cadence detector results after aggregation cannot be directly compared as the same event definition.",
            "INDEPENDENT_VALIDATION_REQUIRED: changes to observed fixed-size candidates are not predictive performance or confirmed bots."
        };
        var summary = new PrintClusterSummary(
            "0.1-derived-observable-clusters", source.FileSha256, derivedSha,
            source.Trades.Count, clusters.Count, multi, sourceInMulti,
            rawLots, derivedLots, true, false, false, false, warnings);
        return new ObservableClusterTape(derivedTape, clusters, summary);
    }

    public static ClusterCandidateComparison CompareFixedSize(
        TradeImportResult original, DetectorConfig? config = null)
    {
        config ??= new DetectorConfig();
        config.Validate();
        var clustered = Build(original);
        var raw = PeriodicDetector.Detect(original, config);
        var onClusters = PeriodicDetector.Detect(clustered.DerivedTape, config);
        return new ClusterCandidateComparison(
            "0.1-exploratory-cluster-compare", original.FileSha256,
            clustered.Summary.DerivedTapeProvenanceSha256,
            original.Trades.Count, clustered.Summary.DerivedObservableClusters,
            clustered.Summary.SourcePrintsInMultiPrintClusters,
            raw.CandidatePatternCount, onClusters.CandidatePatternCount,
            clustered.Summary.TotalSourceLots, clustered.Summary.TotalDerivedLots,
            false, false, false,
            new[]
            {
                "NOT_PARENT_ORDERS: grouping by exact time, price and side does not prove common agent or execution order.",
                "DIFFERENT_OBSERVATION_UNIT: print rows and derived clusters are not directly comparable participant counts.",
                "CANDIDATES_NOT_BOTS: both detector runs are uncalibrated research-only fixed-volume screens.",
                "SAME_DATA_NOT_INDEPENDENT: comparing two views of one archive is a sensitivity study, not out-of-sample validation.",
                "RAW_PRINTS_REMAIN_AVAILABLE: source file and event IDs are never deleted by the derived view."
            });
    }
}
