using RobotDetector.Core;

namespace RobotDetector.SelfTests;

internal static partial class Program
{
    private static ResearchDashboardReport[] ComparisonFixtures()
    {
        var a = ResearchDashboard.Build(
            CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv")));
        var b = ResearchDashboard.Build(
            CsvTradeReader.Read(Fixture("synthetic_activity_episode.csv")));
        return new[] { a, b };
    }

    private static void CompareArchivesConservation()
    {
        var reports = ComparisonFixtures();
        var comparison = ResearchComparison.Compare(reports);
        Assert(comparison.InputArchiveCount == 2, "two independently hashed archives");
        Assert(comparison.TotalPublicPrints == 47, "7+40 public prints");
        Assert(comparison.TotalObservedLots == reports.Sum(x => x.ObservedLots),
            "each archive contributes its own observed lots");
        Assert(comparison.Archives.Sum(x => x.PublicPrints) == comparison.TotalPublicPrints,
            "all source prints preserved without cross-file deduplication");
        Assert(comparison.ComparableDataKinds, "two synthetic inputs are same provenance type");
        Assert(comparison.WindowMinutes == 5 &&
               !comparison.ActualBotCountKnown && !comparison.StatisticalSignificanceEstablished,
            "correct width, no owner or probability claims");
    }

    private static void CompareArchivesRejectDuplicate()
    {
        var report = ComparisonFixtures()[0];
        bool rejected = false;
        try { ResearchComparison.Compare(new[] { report, report }); }
        catch (InvalidDataException) { rejected = true; }
        Assert(rejected, "identical file SHA must not appear to be independent sources");

        rejected = false;
        try { ResearchComparison.Compare(new[] { report }); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "at least two different archives required");
    }

    private static void CompareArchivesRejectWidthMismatch()
    {
        var x = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var y = CsvTradeReader.Read(Fixture("synthetic_activity_episode.csv"));
        bool rejected = false;
        try
        {
            ResearchComparison.Compare(new[]
            {
                ResearchDashboard.Build(x, 5),
                ResearchDashboard.Build(y, 10)
            });
        }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "different clock-window widths cannot be directly compared");
    }

    private static void CompareArchivesHtmlEscaping()
    {
        const string untrusted = "<script>alert('bad')</script><img src=x>";
        var a = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var malicious = a with
        {
            FileName = untrusted + ".csv",
            FileSha256 = "comparison-unique-unsafe",
            Trades = a.Trades.Select(t => t with { Ticker = untrusted }).ToArray()
        };
        var b = CsvTradeReader.Read(Fixture("synthetic_activity_episode.csv"));
        var comparison = ResearchComparison.Compare(new[]
        {
            ResearchDashboard.Build(malicious),
            ResearchDashboard.Build(b)
        });
        string html = ResearchComparison.ToStandaloneHtml(comparison);
        Assert(!html.Contains("<script", StringComparison.OrdinalIgnoreCase) &&
               !html.Contains("<img", StringComparison.OrdinalIgnoreCase),
            "escaped user/source labels must be inert HTML");
        Assert(html.Contains("&lt;script&gt;", StringComparison.Ordinal) &&
               html.Contains("Content-Security-Policy", StringComparison.Ordinal),
            "safe HTML encoding and restrictive CSP");
        Assert(!html.Contains("SYN001", StringComparison.Ordinal),
            "no raw per-print IDs may appear");
    }

    private static void CompareArchivesMixedProvenance()
    {
        var original = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var changed = original with
        {
            FileSha256 = "different-historical-source",
            Trades = original.Trades.Select(t => t with
            {
                EventId = "PUBLIC-" + t.EventId,
                DataKind = "HISTORICAL_PUBLIC"
            }).ToArray()
        };
        var comparison = ResearchComparison.Compare(new[]
        {
            ResearchDashboard.Build(original),
            ResearchDashboard.Build(changed)
        });
        Assert(!comparison.ComparableDataKinds, "real/synthetic projection must be visibly mixed");
        Assert(comparison.Warnings.Any(x => x.StartsWith("MIXED_DATA_KINDS:")),
            "warn against interpreting source-type differences as robot behavior");
    }

    private static void CompareArchivesEmptySource()
    {
        var empty = ResearchDashboard.Build(From(Array.Empty<MarketTrade>()));
        var populated = ComparisonFixtures()[0];
        var comparison = ResearchComparison.Compare(new[] { empty, populated });
        Assert(comparison.InputArchiveCount == 2 &&
               comparison.Archives[0].PublicPrints == 0 &&
               comparison.Archives[0].TimestampCollisionShare is null,
            "empty source must not create fabricated 0% source quality");
        Assert(comparison.Archives[0].NearWholeSecondPrintShare is null &&
               comparison.TotalPublicPrints == 7, "nonempty archive remains unchanged");
        Assert(ResearchComparison.ToStandaloneHtml(comparison).Contains("—", StringComparison.Ordinal),
            "unknown per-empty-source ratio visibly displayed");
    }

    private static void CompareArchivesDeterminism()
    {
        var inputs = ComparisonFixtures();
        var a = ResearchComparison.Compare(inputs);
        var b = ResearchComparison.Compare(inputs);
        string htmlA = ResearchComparison.ToStandaloneHtml(a);
        string htmlB = ResearchComparison.ToStandaloneHtml(b);
        Assert(htmlA == htmlB, "offline comparison is deterministic");
        Assert(htmlA.StartsWith("<!doctype html>", StringComparison.OrdinalIgnoreCase),
            "must be standalone HTML");
        Assert(!htmlA.Contains("<script", StringComparison.OrdinalIgnoreCase) &&
               !htmlA.Contains("http://", StringComparison.OrdinalIgnoreCase) &&
               !htmlA.Contains("https://", StringComparison.OrdinalIgnoreCase),
            "offline report must contain no script or third-party references");
    }

    private static void CompareArchivesTamperedReport()
    {
        var comparison = ResearchComparison.Compare(ComparisonFixtures());
        bool rejected = false;
        try
        {
            ResearchComparison.ToStandaloneHtml(comparison with
            {
                TotalPublicPrints = comparison.TotalPublicPrints + 1
            });
        }
        catch (InvalidDataException) { rejected = true; }
        Assert(rejected, "rendering corrupted source print count must fail closed");

        rejected = false;
        try
        {
            ResearchComparison.Compare(new[]
            {
                ComparisonFixtures()[0] with { ElevatedActivityWindows = 99 },
                ComparisonFixtures()[1]
            });
        }
        catch (InvalidDataException) { rejected = true; }
        Assert(rejected, "fabricated activity statistics cannot be reported as ground truth");
    }
}
