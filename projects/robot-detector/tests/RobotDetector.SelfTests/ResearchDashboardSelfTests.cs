using RobotDetector.Core;

namespace RobotDetector.SelfTests;

internal static partial class Program
{
    private static void DashboardConservesCounts()
    {
        var input = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var report = ResearchDashboard.Build(input);
        Assert(report.PublicPrints == 7 && report.ObservedLots == 640, "source count and sum");
        Assert(report.DistinctInstruments == 1 && report.Groups.Count == 1, "source grouping");
        Assert(report.PopulatedWindows == 1 && report.WindowMinutes == 5, "clock window");
        Assert(report.Groups.Single().PublicPrints == 7, "group retains every print");
        Assert(report.Groups.Single().ObservedLots == 640, "group retains lots");
        Assert(report.Groups.Sum(g => g.PublicPrints) == report.Windows.Sum(w => w.PublicPrints),
            "group/window conservation");
        Assert(report.RejectedRows == 0 && !report.FeedCoverageVerified, "source quality flag");
        Assert(!report.ActualBotCountKnown && !report.StatisticalSignificanceEstablished,
            "not a bot identification result");
    }

    private static void DashboardSourceIsolation()
    {
        var a = CreateSequence("EX-DASH", "EXCHANGE", "BUY", 100, 5000, 7);
        var b = CreateSequence("DL-DASH", "DEALER", "BUY", 50, 5000, 7);
        var source = From(a.Concat(b).ToArray());
        var report = ResearchDashboard.Build(source);
        Assert(report.PublicPrints == 14 && report.Groups.Count == 2, "source split");
        Assert(report.Groups.Select(g => g.TradeSource).Distinct().Count() == 2,
            "DEALER must not mix with EXCHANGE");
        Assert(report.Groups.Sum(g => g.ObservedLots) == 1050, "lots conserved across sources");
        Assert(report.PrintsSharingTimestamp == 0,
            "same clock timestamps in DIFFERENT feeds must not form same-feed collisions");
        Assert(report.Groups.All(g => g.PopulatedWindows == 1), "each source has its own window");
    }

    private static void DashboardTimestampCollisions()
    {
        var now = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var rows = new[]
        {
            new MarketTrade("ONE", now, "X", "X", "EXCHANGE", "BUY", 100m, 11, "TQBR", "D1", "SYNTHETIC", 0),
            new MarketTrade("TWO", now, "X", "X", "EXCHANGE", "BUY", 100m, 13, "TQBR", "D1", "SYNTHETIC", 1),
            new MarketTrade("THREE", now.AddMilliseconds(10), "X", "X", "EXCHANGE", "SELL", 101m, 17, "TQBR", "D1", "SYNTHETIC", 2)
        };
        var report = ResearchDashboard.Build(From(rows));
        Assert(report.PublicPrints == 3 && report.ObservedLots == 41, "never drop prints or lots");
        Assert(report.PrintsSharingTimestamp == 2, "two distinct prints at same timestamp");
        Assert(Math.Abs(report.Groups.Single().TimestampCollisionShare - 2.0 / 3.0) < 1e-9,
            "same-timestamp proportion");
    }

    private static void DashboardActivityWindows()
    {
        var source = CsvTradeReader.Read(Fixture("synthetic_activity_episode.csv"));
        var report = ResearchDashboard.Build(source, 5);
        Assert(report.PopulatedWindows == 5, "synthetic five 5min windows");
        Assert(report.EvaluatedActivityWindows == 1, "first four windows are baseline only");
        Assert(report.ElevatedActivityWindows == 1, "fifth window is synthetic high-activity episode");
        Assert(report.Windows.Count(w => w.ElevatedActivityObserved) == 1,
            "activity marker shown on same data with no future leakage");
        Assert(report.Groups.Sum(g => g.ElevatedActivityWindows) == 1,
            "activity marker consistent across grouped and window views");
        var html = ResearchDashboard.ToStandaloneHtml(report);
        Assert(html.Contains("Наблюдался", StringComparison.Ordinal),
            "offline HTML displays observed high-activity window");
    }

    private static void DashboardHtmlEscaping()
    {
        string injection = "<script>alert('unsafe')</script><img src=x onerror=alert(1)>";
        var trades = CreateSequence("ESC", "EXCHANGE", "SELL", 100, 5000, 7)
            .Select(t => t with { Ticker = injection, InstrumentUid = injection }).ToArray();
        var input = From(trades) with { FileName = injection + ".csv" };
        var report = ResearchDashboard.Build(input);
        string html = ResearchDashboard.ToStandaloneHtml(report);
        Assert(!html.Contains("<script", StringComparison.OrdinalIgnoreCase),
            "no executable script tag from untrusted data");
        Assert(!html.Contains("<img", StringComparison.OrdinalIgnoreCase),
            "no injected image tags / resource requests");
        Assert(html.Contains("&lt;script&gt;", StringComparison.Ordinal) &&
               html.Contains("&lt;img", StringComparison.Ordinal),
            "escaped labels appear as inert visible text");
        Assert(html.Contains("Content-Security-Policy", StringComparison.Ordinal),
            "HTML must have restrictive local CSP");
        Assert(!html.Contains("http://", StringComparison.OrdinalIgnoreCase) &&
               !html.Contains("https://", StringComparison.OrdinalIgnoreCase),
            "offline report does not point to third party resources");
    }

    private static void DashboardDeterministicOfflineHtml()
    {
        var source = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var first = ResearchDashboard.Build(source);
        var again = ResearchDashboard.Build(source);
        string a = ResearchDashboard.ToStandaloneHtml(first, 10);
        string b = ResearchDashboard.ToStandaloneHtml(again, 10);
        Assert(a == b, "static HTML must be reproducible from same input");
        Assert(a.StartsWith("<!doctype html>", StringComparison.OrdinalIgnoreCase), "standalone HTML");
        Assert(!a.Contains("<script", StringComparison.OrdinalIgnoreCase), "script-free");
        Assert(!a.Contains("SYN001", StringComparison.Ordinal),
            "raw per-trade evidence IDs must not be copied into dashboard");
        Assert(a.Contains(source.FileSha256, StringComparison.Ordinal),
            "source SHA for reproducibility, not raw prints");
    }

    private static void DashboardEmptyAndWindowWidth()
    {
        var empty = From(Array.Empty<MarketTrade>());
        var report = ResearchDashboard.Build(empty, 10);
        Assert(report.PublicPrints == 0 && report.Groups.Count == 0 &&
               report.Windows.Count == 0 && report.WindowMinutes == 10, "empty input safe");
        string html = ResearchDashboard.ToStandaloneHtml(report);
        Assert(html.Contains("10-минутных окон", StringComparison.Ordinal),
            "HTML reports true configured width");

        bool invalid = false;
        try { ResearchDashboard.Build(empty, 0); }
        catch (ArgumentOutOfRangeException) { invalid = true; }
        Assert(invalid, "invalid window duration must be rejected");
        invalid = false;
        try { ResearchDashboard.ToStandaloneHtml(report, 0); }
        catch (ArgumentOutOfRangeException) { invalid = true; }
        Assert(invalid, "invalid display limit must be rejected");
    }

    private static void DashboardIntegrityGuard()
    {
        var input = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var report = ResearchDashboard.Build(input);
        bool rejected = false;
        try { ResearchDashboard.ToStandaloneHtml(report with { PublicPrints = 8 }); }
        catch (InvalidDataException) { rejected = true; }
        Assert(rejected, "corrupted event-count metadata must fail closed");

        rejected = false;
        try { ResearchDashboard.ToStandaloneHtml(report with { ElevatedActivityWindows = 5 }); }
        catch (InvalidDataException) { rejected = true; }
        Assert(rejected, "fabricated activity labels must not reach user-facing report");
    }
}
