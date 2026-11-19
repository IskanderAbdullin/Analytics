using RobotDetector.Core;

namespace RobotDetector.SelfTests;

internal static partial class Program
{
    private static MarketTrade[] ClusterRegularSequence()
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        long[] firstLots = { 30, 40, 45, 20, 35, 25, 10 };
        var prints = new List<MarketTrade>();
        for (int i = 0; i < firstLots.Length; i++)
        {
            var time = start.AddSeconds(i * 5);
            for (int j = 0; j < 2; j++)
            {
                long q = j == 0 ? firstLots[i] : 100 - firstLots[i];
                prints.Add(new MarketTrade($"CLIP-{i}-{j}", time,
                    "CLUSTER-SYNTH", "CLIP", "EXCHANGE", "SELL",
                    100m, q, "TQBR", "SESSION-A", "SYNTHETIC", 2 * i + j));
            }
        }
        return prints.ToArray();
    }

    private static void ClusterViewConservesEventsAndLots()
    {
        var source = From(TimestampTape()) with { HasVerifiedFeedCoverage = false };
        var result = ObservablePrintClusters.Build(source);
        Assert(result.Summary.SourcePublicPrints == 6 &&
               result.Summary.DerivedObservableClusters == 4,
            "two exact time/price groups should collapse into traceable views");
        Assert(result.Summary.MultiPrintClusters == 2 &&
               result.Summary.SourcePrintsInMultiPrintClusters == 4,
            "only same time AND price AND side source prints belong to the multi-print clusters");
        Assert(result.Summary.TotalSourceLots == 75 &&
               result.Summary.TotalDerivedLots == 75, "exact lots conservation");
        Assert(result.Clusters.SelectMany(c => c.OriginalPublicEventIds)
            .OrderBy(x => x).SequenceEqual(source.Trades.Select(t => t.EventId).OrderBy(x => x)),
            "every original event must survive once in the cluster audit mapping");
        Assert(result.DerivedTape.Trades.All(x => x.DataKind == "DERIVED_PUBLIC_PRINT_CLUSTER"),
            "derived tape must be visibly different from actual source prints");
        Assert(!result.DerivedTape.HasVerifiedFeedCoverage &&
               !result.Summary.ActualParentOrderKnown && !result.Summary.ActualBotCountKnown,
            "cluster formation cannot improve source completeness or identify owners");
    }

    private static void ClusterViewNoCrossAttribution()
    {
        var start = TimestampTape()[0];
        var variants = new[]
        {
            start with { EventId = "V1" },
            start with { EventId = "V2", Price = 101m },
            start with { EventId = "V3", ReportedDirection = "BUY" },
            start with { EventId = "V4", TradeSource = "DEALER" },
            start with { EventId = "V5", TradingMode = "OTHER_MODE" },
            start with { EventId = "V6", SessionId = "OTHER_SESSION" }
        };
        var result = ObservablePrintClusters.Build(From(variants));
        Assert(result.Summary.DerivedObservableClusters == 6 &&
               result.Summary.MultiPrintClusters == 0,
            "never aggregate same-time events with different source, price, side, mode or session");
        Assert(result.Clusters.All(c => c.PublicPrintCount == 1),
            "only exactly matching source/public print attributes allow one group");
    }

    private static void ClusterViewDeterministic()
    {
        var source = ClusterRegularSequence();
        var a = ObservablePrintClusters.Build(From(source));
        var b = ObservablePrintClusters.Build(From(source.Reverse().ToArray()));
        Assert(a.Summary.DerivedTapeProvenanceSha256 == b.Summary.DerivedTapeProvenanceSha256,
            "identical original source identity yields the same derived provenance");
        Assert(a.Clusters.Select(c => c.ClusterId).SequenceEqual(
            b.Clusters.Select(c => c.ClusterId)), "stable cluster identity independent of input row order");
        Assert(a.Clusters.All(c => c.PublicPrintCount == 2 && c.TotalLots == 100),
            "all seven derived clusters retain pair sizes");
        Assert(a.DerivedTape.Trades.Count == 7 &&
               a.DerivedTape.Trades.All(x => x.QuantityLots == 100),
            "derived observation tape consists of seven aggregated 100-lot snapshots");
    }

    private static void ClusterViewCadenceSensitivity()
    {
        var source = From(ClusterRegularSequence());
        var screen = new DetectorConfig { MinMatches = 6 };
        var raw = PeriodicDetector.Detect(source, screen);
        var derived = ObservablePrintClusters.Build(source);
        var grouped = PeriodicDetector.Detect(derived.DerivedTape, screen);
        Assert(raw.CandidatePatternCount == 0,
            "distinct public child sizes do not generate a six-match fixed-volume row-level cadence");
        Assert(grouped.CandidatePatternCount == 1 &&
               grouped.Patterns.Single().TypicalQuantityLots == 100 &&
               grouped.Patterns.Single().MatchedCount == 7,
            "derived exact-time price-side clusters expose one synthetic 5-second 100-lot rhythm");
        Assert(derived.Summary.TotalSourceLots == derived.Summary.TotalDerivedLots,
            "new candidate must not be the result of missing or duplicated lots");
    }

    private static void ClusterComparisonSafeState()
    {
        var compare = ObservablePrintClusters.CompareFixedSize(
            From(ClusterRegularSequence()), new DetectorConfig { MinMatches = 6 });
        Assert(compare.OriginalPublicPrints == 14 &&
               compare.DerivedObservableClusters == 7 &&
               compare.PublicPrintsInMultiPrintClusters == 14,
            "comparison must expose change of observation unit");
        Assert(compare.OriginalFixedSizeCandidateEpisodes == 0 &&
               compare.DerivedClusterSizeCandidateEpisodes == 1,
            "two algorithms may yield different observational candidate counts");
        Assert(compare.OriginalTotalLots == 700 && compare.DerivedTotalLots == 700,
            "conservation of economic lot count");
        Assert(!compare.ActualParentOrdersIdentified &&
               !compare.PhysicalBotCountKnown &&
               !compare.StatisticalSignificanceEstablished,
            "derived time/price clustering never proves a parent order or bot");
    }

    private static void ClusterViewRejectsDuplicateIds()
    {
        var originals = TimestampTape();
        originals[1] = originals[1] with { EventId = originals[0].EventId };
        bool rejected = false;
        try { ObservablePrintClusters.Build(From(originals)); }
        catch (InvalidDataException) { rejected = true; }
        Assert(rejected, "ambiguous repeated source event identity must fail closed");

        var empty = ObservablePrintClusters.Build(From());
        Assert(empty.Summary.SourcePublicPrints == 0 &&
               empty.Summary.DerivedObservableClusters == 0 &&
               empty.Summary.TotalDerivedLots == 0,
            "empty source file must have an empty derived view");
    }
}
