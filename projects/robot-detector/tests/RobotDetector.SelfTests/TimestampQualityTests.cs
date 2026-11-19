using RobotDetector.Core;

namespace RobotDetector.SelfTests;

internal static partial class Program
{
    private static MarketTrade[] TimestampTape()
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        long[] offsets = { 0, 0, 0, 5_000, 10_000, 10_000 };
        decimal[] prices = { 100m, 100m, 101m, 102m, 103m, 103m };
        return Enumerable.Range(0, offsets.Length).Select(i =>
            new MarketTrade($"TS-{i}", start.AddTicks(offsets[i]), "TS-SYNTH", "TS",
                "EXCHANGE", "SELL", prices[i], 10L + i, "TQBR",
                "SESSION-A", "SYNTHETIC", i)).ToArray();
    }

    private static void TimestampQualityCollisions()
    {
        var source = From(TimestampTape()) with { HasVerifiedFeedCoverage = false };
        var report = TimestampQualityAudit.Describe(source);
        var g = report.Groups.Single();
        Assert(report.SourcePrints == 6 && g.PublicPrintCount == 6,
            "all six public prints must be preserved");
        Assert(g.UniqueTimestampCount == 3 && g.SameTimestampClusters == 2,
            "one 3-print timestamp and one 2-print timestamp cluster");
        Assert(g.PrintsInSameTimestampClusters == 5 &&
               g.MaxPrintsAtSameTimestamp == 3,
            "simultaneous print clusters must count rows, not owners");
        Assert(g.PrintsInSameTimestampAndPriceClusters == 4,
            "same timestamp and price print clusters are not safe to deduplicate");
        Assert(Math.Abs(g.SameTimestampClusterPrintShare - 5.0 / 6) < 1e-12,
            "report collision fraction");
        Assert(g.SmallestPositiveGapMicroseconds == 500,
            "known minimum 500 microseconds between distinct timestamps");
        Assert(!report.OwnerCountKnown && !report.StatisticalSignificanceEstablished,
            "no owner count or confidence inference");
    }

    private static void TimestampQualityGranularity()
    {
        var g = TimestampQualityAudit.Describe(From(TimestampTape())).Groups.Single();
        Assert(g.WholeSecondTimestampPrints == 3 &&
               g.Whole100MillisecondTimestampPrints == 3 &&
               g.Whole10MillisecondTimestampPrints == 3,
            "only the three exact-second prints are on whole 100ms and 10ms boundaries");
        Assert(g.WholeMillisecondTimestampPrints == 5 &&
               g.SubMillisecondTimestampPrints == 1,
            "five prints are integer-millisecond, one is 500us");
        Assert(g.NotMicrosecondAlignedPrints == 0,
            "all synthetic timestamps are microsecond aligned");
        Assert(Math.Abs(g.WholeMillisecondPrintShare - 5.0 / 6) < 1e-12,
            "millisecond-aligned share should reconcile");

        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var nanos = TimestampTape();
        nanos[0] = nanos[0] with { ExchangeTimeUtc = start.AddTicks(1) };
        var subMicro = TimestampQualityAudit.Describe(From(nanos)).Groups.Single();
        Assert(subMicro.NotMicrosecondAlignedPrints == 1,
            "100ns-scale timestamp must not be mislabelled microsecond aligned");
    }

    private static void TimestampQualitySourceIsolation()
    {
        var a = TimestampTape();
        var b = TimestampTape().Select(t => t with
        {
            EventId = "DEALER-" + t.EventId,
            TradeSource = "DEALER"
        });
        var c = TimestampTape().Select(t => t with
        {
            EventId = "NEXTDAY-" + t.EventId,
            SessionId = "SESSION-B"
        });
        var d = TimestampTape().Select(t => t with
        {
            EventId = "OTHERMODE-" + t.EventId,
            TradingMode = "OTHER_MODE"
        });
        var report = TimestampQualityAudit.Describe(From(a.Concat(b).Concat(c).Concat(d).ToArray()));
        Assert(report.SourceGroups == 4 && report.SourcePrints == 24,
            "groups must isolate venue/source, trading mode and session");
        Assert(report.Groups.All(g => g.PublicPrintCount == 6 && g.UniqueTimestampCount == 3),
            "source-specific duplicate counts cannot borrow another source");
        Assert(report.Groups.Sum(g => g.PrintsInSameTimestampClusters) == 20,
            "preserve each of four independent collision groups");
    }

    private static void TimestampQualityUncertainty()
    {
        var input = From(TimestampTape()) with { HasVerifiedFeedCoverage = false };
        var report = TimestampQualityAudit.Describe(input);
        Assert(!report.FeedCoverageVerified && !report.SourceTimestampPrecisionVerified &&
               !report.OwnerCountKnown && !report.StatisticalSignificanceEstablished,
            "public CSV cannot verify clock precision or exchange data completeness");
        Assert(report.Groups.All(g => !g.FeedCoverageVerified &&
            !g.SourceTimestampPrecisionVerified), "all group claims must remain conservative");
        Assert(report.Warnings.Any(w => w.StartsWith("TIMESTAMP_COLLISIONS_ARE_NOT_DUPLICATES")),
            "make strict no-dedup rule explicit");
    }

    private static void TimestampQualitySmallInputs()
    {
        var empty = TimestampQualityAudit.Describe(From());
        Assert(empty.SourcePrints == 0 && empty.SourceGroups == 0 &&
            empty.Groups.Count == 0, "empty tape is not a false timestamp cluster");
        var one = TimestampQualityAudit.Describe(From(TimestampTape()[0]));
        var g = one.Groups.Single();
        Assert(g.PublicPrintCount == 1 && g.UniqueTimestampCount == 1 &&
               g.SameTimestampClusters == 0 && g.MaxPrintsAtSameTimestamp == 1 &&
               g.SmallestPositiveGapMicroseconds is null,
            "one print has no positive interarrival evidence");
    }
}
