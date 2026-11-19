using RobotDetector.Core;

namespace RobotDetector.SelfTests;

internal static partial class Program
{
    private static void ReplayConservesSource()
    {
        var input = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var replay = BoundedEventReplay.Analyse(input);
        Assert(replay.InputPrints == 7 && replay.ReplayedPrints == 7, "all prints must remain");
        Assert(replay.ReplayedLots == 640 && replay.PopulatedWindows == 1,
            "observed lots and window conserved");
        Assert(replay.Windows.Sum(x => x.ReplayedPrintCountForTest()) == 7,
            "window aggregates must cover all source events");
        Assert(replay.Windows.Sum(x => x.ObservedLots) == 640, "no volume loss");
        Assert(!replay.AnyPrintsDropped && !replay.ActualBotCountKnown, "no invisible loss or owner claim");
        Assert(!replay.SourceCoverageVerified && !replay.HasActualNetworkReceiveTimestamps,
            "offline archive cannot prove network-time or completeness");
    }

    private static int ReplayedPrintCountForTest(this ReplayObservedWindow w) => w.PublicPrints;

    private static MarketTrade[] OutOfOrderStream()
    {
        var t0 = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        return new[]
        {
            new MarketTrade("A", t0, "SYN-R", "R", "EXCHANGE", "BUY", 10m, 1, "TQBR", "S1", "SYNTHETIC", 0),
            new MarketTrade("B", t0.AddMilliseconds(300), "SYN-R", "R", "EXCHANGE", "BUY", 10m, 2, "TQBR", "S1", "SYNTHETIC", 1),
            new MarketTrade("C", t0.AddMilliseconds(100), "SYN-R", "R", "EXCHANGE", "BUY", 10m, 3, "TQBR", "S1", "SYNTHETIC", 2)
        };
    }

    private static void ReplayWithinGrace()
    {
        var replay = BoundedEventReplay.Analyse(From(OutOfOrderStream()),
            new ReplayAuditConfig { AllowedLatenessMilliseconds = 500, MaximumPendingEvents = 16 });
        Assert(replay.InputPrints == 3 && replay.ReplayedPrints == 3, "event count");
        Assert(replay.OutOfOrderArrivalCount == 1 && replay.LateAfterWatermarkCount == 0,
            "300ms to 100ms reversal within 500ms grace is not late");
        Assert(replay.ReplayedLots == 6 && replay.ForcedQueueFlushCount == 0, "volume and no pressure");
        Assert(replay.Windows.Single().ReportedBuyLots == 6, "source direction count");
    }

    private static void ReplayLateAfterWatermark()
    {
        var rows = OutOfOrderStream();
        rows[1] = rows[1] with { ExchangeTimeUtc = rows[1].ExchangeTimeUtc.AddMilliseconds(700) };
        var replay = BoundedEventReplay.Analyse(From(rows),
            new ReplayAuditConfig { AllowedLatenessMilliseconds = 100, MaximumPendingEvents = 16 });
        Assert(replay.LateAfterWatermarkCount == 1, "late event must be flagged");
        Assert(replay.OutOfOrderArrivalCount == 1, "arrival sequence out-of-order");
        Assert(replay.ReplayedPrints == 3 && replay.ReplayedLots == 6 &&
               !replay.AnyPrintsDropped, "late events must still be included in final window totals");
        Assert(replay.Warnings.Any(w => w.StartsWith("LATE_PRINTS:")), "explicit quality warning");
    }

    private static void ReplayQueuePressure()
    {
        var now = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var trades = Enumerable.Range(0, 40).Select(i =>
            new MarketTrade($"PRESS-{i}", now, "SYN-PRESS", "PRESS", "EXCHANGE",
                "BUY", 100m, 1, "TQBR", "S1", "SYNTHETIC", i)).ToArray();
        var result = BoundedEventReplay.Analyse(From(trades),
            new ReplayAuditConfig { AllowedLatenessMilliseconds = 500,
                MaximumPendingEvents = 16 });
        Assert(result.ReplayedPrints == 40 && result.ReplayedLots == 40,
            "all 40 simultaneous prints are retained");
        Assert(result.ForcedQueueFlushCount == 24, "one forced flush for each event beyond 16");
        Assert(result.MaximumPendingObserved <= 16, "hard pending-memory bound");
        Assert(result.Windows.Single().PublicPrints == 40, "same timestamp NOT deduplicated");
        Assert(!result.AnyPrintsDropped && result.Warnings.Any(w => w.StartsWith("QUEUE_PRESSURE:")),
            "queue pressure must not silently drop data");
    }

    private static void ReplaySourceIsolation()
    {
        var now = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var input = From(new[]
        {
            new MarketTrade("EX", now, "X", "X", "EXCHANGE", "BUY", 10m, 10, "TQBR", "D1", "SYNTHETIC", 0),
            new MarketTrade("DL", now, "X", "X", "DEALER", "SELL", 10m, 20, "TQBR", "D1", "SYNTHETIC", 1),
            new MarketTrade("SESSION", now.AddMinutes(5), "X", "X", "EXCHANGE", "BUY", 10m, 30, "TQBR", "D2", "SYNTHETIC", 2)
        });
        var r = BoundedEventReplay.Analyse(input);
        Assert(r.PopulatedWindows == 3, "venue/session/window separation");
        Assert(r.ReplayedPrints == 3 && r.ReplayedLots == 60, "source totals");
        Assert(r.Windows.Sum(w => w.ReportedBuyLots) == 40 &&
               r.Windows.Sum(w => w.ReportedSellLots) == 20,
            "provider direction preserved");
    }

    private static void ReplayEmpty()
    {
        var result = BoundedEventReplay.Analyse(From(Array.Empty<MarketTrade>()));
        Assert(result.PopulatedWindows == 0 && result.InputPrints == 0 &&
               result.ReplayedPrints == 0 && result.MaximumPendingObserved == 0,
            "no empty-history false positives");
        Assert(!result.ActualBotCountKnown, "no physical identities");
    }

    private static void ReplayAggregateParity()
    {
        var rows = OutOfOrderStream();
        var original = BoundedEventReplay.Analyse(From(rows));
        var reordered = rows.Reverse().Select((t, i) =>
            t with { ArrivalSequence = i }).ToArray();
        var other = BoundedEventReplay.Analyse(From(reordered));
        Assert(original.ReplayedPrints == other.ReplayedPrints &&
               original.ReplayedLots == other.ReplayedLots, "arrival order independent totals");
        Assert(original.Windows.SequenceEqual(other.Windows), "same event-time window aggregates");
        var dashboard = ResearchDashboard.Build(From(rows));
        Assert(original.Windows.Sum(w => w.PublicPrints) == dashboard.PublicPrints &&
               original.Windows.Sum(w => w.ObservedLots) == dashboard.ObservedLots,
            "independent flow dashboard must conserve same counts and lots");
    }

    private static void ReplayRejectsInvalid()
    {
        bool rejected = false;
        try { new ReplayAuditConfig { MaximumPendingEvents = 0 }.Validate(); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "reject unbounded/zero pending limits");
        rejected = false;
        try { BoundedEventReplay.Analyse(From(OutOfOrderStream()),
            new ReplayAuditConfig { AllowedLatenessMilliseconds = -1 }); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "negative watermark grace forbidden");
        var zero = OutOfOrderStream();
        zero[0] = zero[0] with { QuantityLots = 0 };
        rejected = false;
        try { BoundedEventReplay.Analyse(From(zero)); }
        catch (InvalidDataException) { rejected = true; }
        Assert(rejected, "invalid zero-size print is not a valid trade");
    }
}
