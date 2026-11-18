using System.Globalization;
using System.Text;
using RobotDetector.Core;

namespace RobotDetector.SelfTests;

/// <summary>
/// Zero-NuGet deterministic checks; executable with dotnet run --project tests/RobotDetector.SelfTests.
/// Tests of real accuracy and broker connectivity are deliberately NOT claimed.
/// </summary>
internal static class Program
{
    private static int _passed;
    private static int _failed;

    private static void Main()
    {
        Check("reference T-Invest-shaped CSV fixture", ReferenceFixture);
        Check("two distinct buy/sell streams", TwoStreams);
        Check("unknown side never becomes owner", UnknownSide);
        Check("same periodic prints cannot be double counted", IdenticalEvents);
        Check("too few observations not labelled", TooFew);
        Check("source separation", SeparateSources);
        Check("dense groups refuse silent downsampling", DenseGroup);
        Check("strict parser quarantines invalid row", InvalidRow);
        Check("source hash and ordered reading are repeatable", Determinism);
        Check("quote oscillation observable without any trades", QuoteWithoutTrades);
        Check("missing coverage is not proof", MissingCoverage);
        Check("config rejects impossible thresholds", BadConfig);
        Check("synthetic benchmark reproducible with hidden truth", BenchmarkReproducible);

        Console.WriteLine($"SelfTests: passed={_passed}, failed={_failed}");
        if (_failed != 0) Environment.ExitCode = 1;
    }

    private static void Check(string name, Action test)
    {
        try
        {
            test();
            Console.WriteLine("PASS " + name);
            _passed++;
        }
        catch (Exception e)
        {
            _failed++;
            Console.Error.WriteLine($"FAIL {name}: {e}");
        }
    }

    private static void Assert(bool value, string message)
    {
        if (!value) throw new Exception(message);
    }

    private static string Fixture(string file)
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            string candidate = Path.Combine(directory.FullName, "fixtures", file);
            if (File.Exists(candidate)) return candidate;
            directory = directory.Parent;
        }
        throw new FileNotFoundException("Cannot find fixture: " + file);
    }

    private static void ReferenceFixture()
    {
        var source = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        Assert(source.Trades.Count == 7, "expected seven prints");
        Assert(source.RejectedRows.Count == 0, "malformed reference fixture");
        var report = PeriodicDetector.Detect(source, new DetectorConfig());
        Assert(report.CandidatePatternCount == 1, "expected one distinct candidate");
        var pattern = report.Patterns.Single();
        Assert(pattern.TypicalQuantityLots == 100, "q");
        Assert(pattern.PeriodMilliseconds == 5000, "T");
        Assert(pattern.MatchedCount == 6, "six matching trades");
        Assert(pattern.ExpectedCycles == 7 && pattern.MissedCycles == 1, "missing cycle");
        Assert(pattern.ObservedLots == 600, "volume");
        Assert(pattern.EvidenceEventIds.SequenceEqual(new[]
            { "SYN001", "SYN002", "SYN003", "SYN005", "SYN006", "SYN007" }), "event IDs");
        Assert(pattern.State == "candidate" && pattern.ConfidenceCalibrated is null, "not calibrated");
        Assert(!report.PhysicalBotCountKnown && !report.CoverageVerified, "unknown owner/coverage");
    }

    private static MarketTrade[] CreateSequence(string prefix, string source, string side,
        long quantity, int everyMs, int count, int offsetMs = 0)
    {
        var zero = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        return Enumerable.Range(0, count).Select(i =>
            new MarketTrade($"{prefix}-{i}", zero.AddMilliseconds(offsetMs + i * everyMs),
                "SYNTH-1", "SYNTH", source, side, 100m, quantity, "TQBR",
                "SESSION-1", "SYNTHETIC", i)).ToArray();
    }

    private static TradeImportResult From(params MarketTrade[] trades) =>
        new(trades, Array.Empty<BadRow>(), "synthetic", "synthetic-sha", true);

    private static void TwoStreams()
    {
        var buy = CreateSequence("BUY", "EXCHANGE", "BUY", 100, 5000, 7);
        var sell = CreateSequence("SELL", "EXCHANGE", "SELL", 50, 8000, 7, 500);
        var report = PeriodicDetector.Detect(From(buy.Concat(sell).ToArray()), new DetectorConfig());
        Assert(report.CandidatePatternCount == 2, "must separate distinct streams");
        Assert(report.Patterns.Sum(x => x.ObservedLots) == 1050, "total assigned lots");
        Assert(report.Patterns.SelectMany(x => x.EvidenceEventIds).Distinct().Count() == 14, "no overlap");
    }

    private static void UnknownSide()
    {
        var unknown = CreateSequence("UNK", "EXCHANGE", "UNKNOWN", 100, 5000, 8);
        var result = PeriodicDetector.Detect(From(unknown), new DetectorConfig());
        Assert(result.Patterns.Count == 0, "unknown direction must not invent buy/sell");
        Assert(result.Warnings.Any(x => x.Contains("UNKNOWN_TRADE_SIDE")), "missing warning");
    }

    private static void IdenticalEvents()
    {
        var source = CreateSequence("A", "EXCHANGE", "SELL", 100, 5000, 7);
        var duplicates = CreateSequence("B", "EXCHANGE", "SELL", 100, 5000, 7);
        var report = PeriodicDetector.Detect(From(source.Concat(duplicates).ToArray()), new DetectorConfig());
        Assert(report.Patterns.Count <= 1, "identical time/size streams are not separable");
        Assert(report.Patterns.SelectMany(x => x.EvidenceEventIds).Distinct().Count() ==
               report.Patterns.Sum(x => x.MatchedCount), "event attribution collision");
    }

    private static void TooFew()
    {
        var report = PeriodicDetector.Detect(From(CreateSequence("SMALL", "EXCHANGE", "SELL", 100, 5000, 5)),
            new DetectorConfig());
        Assert(report.CandidatePatternCount == 0, "less than min matches");
    }

    private static void SeparateSources()
    {
        var a = CreateSequence("EX", "EXCHANGE", "BUY", 100, 5000, 7);
        var b = CreateSequence("DL", "DEALER", "BUY", 100, 5000, 7);
        var result = PeriodicDetector.Detect(From(a.Concat(b).ToArray()), new DetectorConfig());
        Assert(result.Patterns.Count == 2, "different sources may not be mixed");
    }

    private static void DenseGroup()
    {
        var report = PeriodicDetector.Detect(From(CreateSequence("DENSE", "EXCHANGE", "BUY", 100, 1000, 50)),
            new DetectorConfig { MaximumEventsPerGroup = 20 });
        Assert(report.CandidatePatternCount == 0, "cannot silently sample dense group");
        Assert(report.Warnings.Any(w => w.StartsWith("SKIPPED_DENSE_GROUP")), "must expose limit");
    }

    private static void InvalidRow()
    {
        string temp = Path.Combine(Path.GetTempPath(), "robot-detector-test-" + Guid.NewGuid() + ".csv");
        try
        {
            File.WriteAllText(temp,
                "TRADE_TS,TICKER_CC,DIRECTION,PRICE,QUANTITY,TRADE_SOURCE,INSTRUMENT_UID\n" +
                "2026-11-18T07:00:00Z,SYN_TQBR,BUY,100,10,EXCHANGE,SYN-1\n" +
                "2026-11-18T07:00:05Z,SYN_TQBR,BUY,nope,10,EXCHANGE,SYN-1\n", Encoding.UTF8);
            var result = CsvTradeReader.Read(temp);
            Assert(result.Trades.Count == 1 && result.RejectedRows.Count == 1,
                "bad line should be quarantined");
        }
        finally { File.Delete(temp); }
    }

    private static void Determinism()
    {
        var import1 = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var import2 = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var report1 = PeriodicDetector.Detect(import1, new DetectorConfig());
        var report2 = PeriodicDetector.Detect(import2, new DetectorConfig());
        Assert(import1.FileSha256 == import2.FileSha256, "hash");
        Assert(report1.Patterns.Single().PatternId == report2.Patterns.Single().PatternId, "pattern ID");
    }

    private static void QuoteWithoutTrades()
    {
        var values = new decimal[] { 101.00m, 101.01m, 101.00m, 101.01m, 101.00m };
        var zero = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var quotes = values.Select((ask, i) =>
            new BestQuote(zero.AddMilliseconds(i * 100), "SYN-Q", 100.99m, ask, 0.01m, 300, 100)).ToArray();
        var result = QuoteOscillation.Calculate(quotes, false);
        Assert(result.AskCarry == 0.04m && result.AskNetMove == 0m, "ask travel");
        Assert(result.AskNormalized == 4m && result.BidNormalized == 0m, "normalization");
        Assert(result.AskReversals == 3 && result.BidReversals == 0, "reversal count");
        Assert(result.Classification == "ask_only_quote_oscillation_observed", "signature");
        Assert(!result.CoverageVerified && !result.PhysicalBotCountKnown, "no owner inference");
    }

    private static void MissingCoverage()
    {
        var import = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        Assert(!import.HasVerifiedFeedCoverage, "single CSV cannot verify completeness");
        Assert(PeriodicDetector.Detect(import, new DetectorConfig()).Patterns.Single().State == "candidate",
            "must not confirm without holdout");
    }


    private static void BenchmarkReproducible()
    {
        var c = new DetectorConfig();
        var a = SyntheticBenchmark.Run(3, c, noiseTrades: 50);
        var b = SyntheticBenchmark.Run(3, c, noiseTrades: 50);
        Assert(a.NumberOfTrials == 6 && a.InjectedTrials == 3 && a.NullTrials == 3,
            "must compare injected vs null");
        Assert(a.Trials.SequenceEqual(b.Trials), "same seeds should produce same trial results");
        Assert(a.Trials.All(x => !x.PhysicalCountInferred), "must not infer real identities");
        Assert(a.Trials.Where(x => x.TrueGeneratorCount == 1).All(x => x.TotalInjectedEvents == 12),
            "internal ground truth count");
    }

    private static void BadConfig()
    {
        bool threw = false;
        try { new DetectorConfig { MinCoverage = 1.5 }.Validate(); }
        catch (ArgumentException) { threw = true; }
        Assert(threw, "invalid coverage range not rejected");
    }
}
