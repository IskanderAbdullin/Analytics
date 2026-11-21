using System.IO.Compression;
using System.Globalization;
using System.Text;
using RobotDetector.Core;

namespace RobotDetector.SelfTests;

/// <summary>
/// Zero-NuGet deterministic checks; executable with dotnet run --project tests/RobotDetector.SelfTests.
/// Tests of real accuracy and broker connectivity are deliberately NOT claimed.
/// </summary>
internal static partial class Program
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
        Check("dense groups split without losing event identity", DenseGroup);
        Check("bounded windows prevent cross-hour evidence reuse", BoundedWindows);
        Check("strict parser quarantines invalid row", InvalidRow);
        Check("gzip archive auto-detected even with .csv extension", GzipCsv);
        Check("single-entry ZIP archive correctly parsed", ZipCsv);
        Check("source hash and ordered reading are repeatable", Determinism);
        Check("quote oscillation observable without any trades", QuoteWithoutTrades);
        Check("missing coverage is not proof", MissingCoverage);
        Check("config rejects impossible thresholds", BadConfig);
        Check("synthetic benchmark reproducible with hidden truth", BenchmarkReproducible);
        Check("walk-forward prediction never reads its future", WalkForwardPrediction);
        Check("FFT uses UTC bins and yields candidate periods", SpectrumTemporalBins);
        Check("size-shuffle preserves timestamps and per-block lot totals", SizeShufflePreservesMarketStructure);
        Check("size-shuffle results are deterministic and evidence-only", SizeShuffleDeterminism);
        Check("unchangeable size labels mark null as uninformative", SizeShuffleDegenerate);
        Check("fusion links one cadence crossing an hour boundary", FusionAcrossHour);
        Check("fusion refuses large time gaps and phase changes", FusionRejectsBadContinuation);
        Check("fusion does not cross trade source/mode boundaries", FusionSeparatesSourceMode);
        Check("fusion validates source hashes and exclusive evidence", FusionRejectsInvalidEvidence);
        Check("rotation null preserves local size runs and timestamps", RotationPreservesRuns);
        Check("null report includes conservative grouped comparison", NullReportIncludesGroups);
        Check("invalid null variant fails closed", InvalidNullVariant);
        Check("rolling forecast predicts later synthetic prints", RollingForecastHasHits);
        Check("rolling forecast placebo is shifted and does not look ahead", RollingForecastPlaceboAndTime);
        Check("rolling replay isolates venue/source groups", RollingForecastSourceIsolation);
        Check("rolling report rejects unverified confidence claims", RollingForecastUnverifiedCoverage);
        Check("post-hoc audit is empty of failure flags for exact clean cadence", DiagnosticCleanCadence);
        Check("post-hoc audit detects same-time size change", DiagnosticDifferentQuantity);
        Check("post-hoc audit detects same-size phase shift", DiagnosticTimingShift);
        Check("post-hoc audit detects stale candidate history", DiagnosticStaleCandidate);
        Check("post-hoc audit does not borrow other venue prints", DiagnosticSourceIsolation);
        Check("post-hoc audit rejects invalid source hashes", DiagnosticIntegrity);
        Check("recency gate suppresses stale forecast before future outcome inspection", RecencyGateSuppressesStale);
        Check("recency gate retains fresh synthetic cadence", RecencyGateKeepsFresh);
        Check("recency selection independent of whether future trade fills", RecencyGateIndependentOfOutcome);
        Check("invalid recency gate values are rejected", RecencyGateRejectsInvalid);
        Check("variable-size fixed-clock candidate is detected", VariableCadenceSynthetic);
        Check("variable-size scanner ignores fixed clip size", VariableCadenceRejectsConstantQuantity);
        Check("variable-size screen isolates EXCHANGE and DEALER", VariableCadenceSourceIsolation);
        Check("variable-size dense windows are split with unique evidence", VariableCadenceDenseWindow);
        Check("tiny trailing dense chunk is explicitly reported", VariableCadenceTinyRemainder);
        Check("temporal null preserves trade counts, sizes and session", TemporalNullPreservation);
        Check("temporal rotation preserves within-block relative phase", TemporalNullRotation);
        Check("temporal negative-control summary is deterministic and uncalibrated", TemporalNullComparison);
        Check("invalid variable-size configuration or temporal null mode fails closed", VariableCadenceInvalidConfiguration);
        Check("flow footprints summarize known signed and unsigned lots", FlowFootprintRegular);
        Check("flow footprints count bursts and empty bins without fabricating bots", FlowFootprintBurst);
        Check("flow footprints partition venues and 5min intervals", FlowFootprintPartition);
        Check("unknown reported side does not invent order direction", FlowFootprintUnknownSide);
        Check("flow footprint rejects invalid bin configuration", FlowFootprintConfigValidation);
        Check("activity observation flags expected synthetic burst after quiet baseline", ActivityEpisodeDetectsBurst);
        Check("activity observation refuses balanced-side high volume", ActivityEpisodeNeedsDirectionalDominance);
        Check("activity observation does not borrow baseline from other venue", ActivityEpisodeSourceIsolation);
        Check("activity observation resets after a missing bucket", ActivityEpisodeResetsOnGap);
        Check("activity observation is independent of later prints", ActivityEpisodeNoFutureLeakage);
        Check("activity observation thresholds reject invalid inputs", ActivityEpisodeInvalidSettings);
        Check("clock phase audit detects round-second concentration", ClockPhaseConcentrated);
        Check("clock audit recognizes evenly distributed intra-second controls", ClockPhaseEvenlyDistributed);
        Check("clock audit partitions venues and trading modes", ClockPhaseSourceSeparation);
        Check("clock audit refuses false certainty for small groups", ClockPhaseInsufficient);
        Check("clock audit random controls reproducible by seed", ClockPhaseDeterministic);
        Check("clock audit respects millisecond boundary precision", ClockPhaseBoundaryPrecision);
        Check("clock audit rejects invalid options and preserves uncertainty", ClockPhaseValidation);
        Check("phase maximum detects peaks outside the first 100ms", ClockPhasePeakBeyondStart);
        Check("phase maximum uses maximum statistic in every null trial", ClockPhaseMaxNullCompatibility);
        Check("phase maximum cannot create evidence on insufficient data", ClockPhaseMaxIneligible);
        Check("timestamp quality detects same-time collisions without dropping prints", TimestampQualityCollisions);
        Check("timestamp quality distinguishes millisecond and microsecond alignment", TimestampQualityGranularity);
        Check("timestamp quality isolates EXCHANGE/DEALER and sessions", TimestampQualitySourceIsolation);
        Check("timestamp quality preserves unknown coverage and owner status", TimestampQualityUncertainty);
        Check("timestamp quality handles empty and one-event sources", TimestampQualitySmallInputs);
        Check("observable cluster view preserves every original execution and lot", ClusterViewConservesEventsAndLots);
        Check("observable clusters never mix exchange source, direction or price", ClusterViewNoCrossAttribution);
        Check("cluster IDs and evidence mapping are deterministic under source reorder", ClusterViewDeterministic);
        Check("derived cluster regularity can differ from row-level regularity", ClusterViewCadenceSensitivity);
        Check("cluster comparison remains candidate-only, no owner identity", ClusterComparisonSafeState);
        Check("cluster grouping refuses duplicate original source event IDs", ClusterViewRejectsDuplicateIds);
        Check("dashboard conserves all public prints and observed lots", DashboardConservesCounts);
        Check("dashboard isolates trade sources and sessions", DashboardSourceIsolation);
        Check("dashboard does not deduplicate equal timestamps", DashboardTimestampCollisions);
        Check("dashboard highlights past-only activity windows", DashboardActivityWindows);
        Check("dashboard HTML escapes untrusted source labels", DashboardHtmlEscaping);
        Check("dashboard HTML is deterministic and contains no scripts", DashboardDeterministicOfflineHtml);
        Check("dashboard includes empty and different-width windows", DashboardEmptyAndWindowWidth);
        Check("dashboard refuses malformed aggregate reports", DashboardIntegrityGuard);
        Check("replay conserves source prints and lots", ReplayConservesSource);
        Check("replay reorders within watermark without false late flag", ReplayWithinGrace);
        Check("replay counts late prints without dropping them", ReplayLateAfterWatermark);
        Check("replay never loses prints when pending queue overflows", ReplayQueuePressure);
        Check("replay separates trade sources, sessions and clock windows", ReplaySourceIsolation);
        Check("replay handles empty input", ReplayEmpty);
        Check("replay aggregates independent of row arrival order", ReplayAggregateParity);
        Check("replay rejects invalid configuration and nonpositive quantities", ReplayRejectsInvalid);
        Check("ideal event-time baseline removes file-order artifacts without changing counts", ReplayIdealEventTimeReference);
        Check("multi-file comparison conserves all independent source summaries", CompareArchivesConservation);
        Check("multi-file comparison rejects duplicate archive fingerprints", CompareArchivesRejectDuplicate);
        Check("multi-file comparison rejects incompatible window widths", CompareArchivesRejectWidthMismatch);
        Check("multi-file comparison HTML escapes unsafe source labels", CompareArchivesHtmlEscaping);
        Check("multi-file comparison flags mixed data provenance", CompareArchivesMixedProvenance);
        Check("multi-file comparison handles empty sources", CompareArchivesEmptySource);
        Check("multi-file comparison HTML and JSON summaries deterministic", CompareArchivesDeterminism);
        Check("multi-file comparison refuses corrupted aggregate summaries", CompareArchivesTamperedReport);
        Check("blind benchmark creates opaque public IDs separate from private truth", BlindOpaquePublicIdentifiers);
        Check("blind benchmark distinguishes fixed and variable synthetic execution", BlindFixedAndVariableClips);
        Check("blind benchmark measures null false positives without recall denominator", BlindNullTruthUndefinedRecall);
        Check("blind benchmark models partial fills without owner leakage", BlindPartialFills);
        Check("blind benchmark demonstrates same public tape, different actual producer counts", BlindNonIdentifiability);
        Check("blind benchmark cannot report real-market identity or confidence", BlindNoRealIdentityClaim);
        Check("blind benchmark results are deterministic by seed", BlindDeterminism);
        Check("blind benchmark rejects invalid scenarios and seed counts", BlindRejectInvalid);
        Check("clocked null has no controlled execution truth", ClockedNullNoControlledExecution);
        Check("clocked null summaries conserve attributed false positives", ClockedNullSummaryConservation);
        Check("clocked null seeds deterministic and bounds validated", ClockedNullDeterministicAndValidated);
        Check("clocked null variable sizes preserve truth separation", ClockedNullVariableQuantityStress);

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
        Assert(report.CandidatePatternCount >= 1, "at least one bounded chunk should be analysed");
        Assert(report.Warnings.Any(w => w.StartsWith("SPLIT_DENSE_GROUP")), "must flag segmentation");
        Assert(report.Patterns.SelectMany(p => p.EvidenceEventIds).Distinct().Count() ==
               report.Patterns.Sum(p => p.MatchedCount), "no event may be double attributed");
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


    private static void WalkForwardPrediction()
    {
        var file = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var cutoff = new DateTimeOffset(2026, 11, 18, 7, 0, 20, TimeSpan.Zero)
            .AddMilliseconds(20);
        var report = WalkForward.Evaluate(file, cutoff, new DetectorConfig { MinMatches = 4 });
        Assert(report.TrainingPrints == 5 && report.FuturePrints == 2, "time split");
        Assert(report.ForecastsIssued == 1 && report.Hits == 1, "25s event should confirm prediction");
        Assert(report.Checks.Single().FutureMatchedEventId == "SYN006", "future event id");
        Assert(!report.Calibrated && !report.CoverageVerified, "not a probability claim");
    }


    private static void SpectrumTemporalBins()
    {
        var source = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var report = SpectralCandidates.Analyse(source, binMs: 500, thresholdSigma: 0);
        Assert(report.AnalysedGroups == 1, "must analyse the q100 and q40 series together");
        Assert(report.Peaks.All(x => x.CandidatePeriodMs >= 1000), "Nyquist limit at 500 ms bins");
        Assert(report.Peaks.All(x => x.Feature is "trade_count" or "lots"), "feature labels");
        Assert(report.Warnings.Any(x => x.StartsWith("SPECTRAL_PEAK_IS_NOT_BOT")),
            "must label spectral peaks as candidates only");
    }


    private static void BoundedWindows()
    {
        var first = CreateSequence("W1", "EXCHANGE", "SELL", 100, 5000, 7);
        var second = CreateSequence("W2", "EXCHANGE", "SELL", 100, 5000, 7)
            .Select(t => t with { ExchangeTimeUtc = t.ExchangeTimeUtc.AddHours(1) }).ToArray();
        var report = PeriodicDetector.Detect(From(first.Concat(second).ToArray()),
            new DetectorConfig { AnalysisWindowMinutes = 60 });
        Assert(report.CandidatePatternCount == 2, "two disjoint analysis episodes expected");
        Assert(report.Patterns.SelectMany(p => p.EvidenceEventIds).Distinct().Count() == 14,
            "event attribution must be disjoint");
        Assert(report.Warnings.Any(x => x.StartsWith("WINDOWED_EPISODES")),
            "must not confuse episodes with distinct physical bots");
    }


    private static void GzipCsv()
    {
        string temp = Path.Combine(Path.GetTempPath(), "rd-gzip-" + Guid.NewGuid() + ".csv");
        try
        {
            using (var file = File.Create(temp))
            using (var gzip = new GZipStream(file, CompressionMode.Compress))
            {
                byte[] bytes = File.ReadAllBytes(Fixture("synthetic_twap_5s.csv"));
                gzip.Write(bytes);
            }
            var result = CsvTradeReader.Read(temp);
            Assert(result.Trades.Count == 7, "gzip stream should decompress into 7 prints");
            Assert(result.RejectedRowTotal == 0, "valid gzip should not be quarantined");
        }
        finally { File.Delete(temp); }
    }

    private static void ZipCsv()
    {
        string temp = Path.Combine(Path.GetTempPath(), "rd-zip-" + Guid.NewGuid() + ".zip");
        try
        {
            using (var file = File.Create(temp))
            using (var zip = new ZipArchive(file, ZipArchiveMode.Create))
            {
                var item = zip.CreateEntry("trades.csv");
                using var target = item.Open();
                target.Write(File.ReadAllBytes(Fixture("synthetic_twap_5s.csv")));
            }
            var result = CsvTradeReader.Read(temp);
            Assert(result.Trades.Count == 7, "zip stream should extract 7 prints");
        }
        finally { File.Delete(temp); }
    }


    private static void SizeShufflePreservesMarketStructure()
    {
        var source = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var (tape, changed) = SizeShuffleNull.Shuffle(source, seed: 51, localWindowSeconds: 60);
        Assert(tape.Trades.Count == source.Trades.Count, "all prints must remain");
        Assert(tape.Trades.Select(t => t.EventId).SequenceEqual(source.Trades.Select(t => t.EventId)),
            "must preserve source identities");
        Assert(tape.Trades.Select(t => t.ExchangeTimeUtc).SequenceEqual(source.Trades.Select(t => t.ExchangeTimeUtc)),
            "must preserve true timestamps");
        Assert(tape.Trades.Sum(t => t.QuantityLots) == source.Trades.Sum(t => t.QuantityLots),
            "must preserve lot totals");
        Assert(tape.Trades.All(t => t.TradeSource == "EXCHANGE" && t.ReportedDirection == "SELL"),
            "must preserve source and side");
        Assert(changed >= 0, "changed count cannot be negative");
    }

    private static void SizeShuffleDeterminism()
    {
        var source = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var first = SizeShuffleNull.Compare(source, new DetectorConfig(), 5, 7, 60);
        var again = SizeShuffleNull.Compare(source, new DetectorConfig(), 5, 7, 60);
        Assert(first.Trials.SequenceEqual(again.Trials), "same seed should give same null trials");
        Assert(first.OriginalCandidateEpisodes == 1, "original synthetic stream expected");
        Assert(first.Trials.All(t => t.NullCandidateEpisodes >= 0), "counts not probabilities");
        Assert(first.Limitations.Any(s => s.Contains("EXPLORATORY_ONLY")),
            "must label source of uncertainty");
    }

    private static void SizeShuffleDegenerate()
    {
        var constant = From(CreateSequence("ALL", "EXCHANGE", "SELL", 100, 5000, 7));
        var result = SizeShuffleNull.Compare(constant, new DetectorConfig(), 3, 9, 60);
        Assert(result.Trials.All(t => t.ShuffledTradeCount == 0), "all sizes identical");
        Assert(result.EmpiricalGlobalTailProbability is null,
            "no useful shuffle means no comparable empirical tail");
    }


    private static MarketTrade[] SequenceAt(DateTimeOffset start, string idPrefix,
        int count, int periodMs = 5000, int phaseOffsetMs = 0,
        string source = "EXCHANGE", string mode = "TQBR")
    {
        return Enumerable.Range(0, count).Select(i =>
            new MarketTrade($"{idPrefix}{i}", start.AddMilliseconds(phaseOffsetMs + i * periodMs),
                "SYNTH-FUSION", "SYNTH", source, "SELL", 100m, 100,
                mode, "SESSION-1", "SYNTHETIC", i)).ToArray();
    }

    private static void FusionAcrossHour()
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 59, 30, TimeSpan.Zero);
        var source = From(SequenceAt(start, "CROSS", 13));
        var screen = PeriodicDetector.Detect(source, new DetectorConfig());
        Assert(screen.CandidatePatternCount == 2, "expected 6+7 prints across UTC hours");
        var fused = EpisodeFusion.Group(source, screen, new DetectorConfig());
        Assert(fused.CandidateEpisodeCount == 2, "two original candidate episodes");
        Assert(fused.ConservativelyLinkedGroupCount == 1, "one cautious observable cadence group");
        Assert(fused.LinkedEpisodeCount == 1, "one adjacency merge");
        Assert(fused.UniqueAttributedPrintCount == 13 && fused.UniqueAttributedLots == 1300,
            "no double count after fusion");
        Assert(fused.Groups.Single().EpisodeCount == 2, "one group contains two episodes");
        Assert(!fused.ActualBotCountKnown && fused.Groups.Single().ConfidenceCalibrated is null,
            "group is not proof of one actual robot");
        Assert(EpisodeFusion.Group(source, screen, new DetectorConfig()).Groups.Single().GroupId ==
            fused.Groups.Single().GroupId, "deterministic group identity");
    }

    private static void FusionRejectsBadContinuation()
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 59, 30, TimeSpan.Zero);
        var left = SequenceAt(start, "FIRST", 6);
        var right = SequenceAt(start.AddMinutes(30), "FAR", 7);
        var farSource = From(left.Concat(right).ToArray());
        var farScreen = PeriodicDetector.Detect(farSource, new DetectorConfig());
        Assert(farScreen.CandidatePatternCount == 2, "two independent candidate episodes");
        Assert(EpisodeFusion.Group(farSource, farScreen, new DetectorConfig()).ConservativelyLinkedGroupCount == 2,
            "no link across a 30-minute inactivity gap");

        var phaseRight = SequenceAt(new DateTimeOffset(2026, 11, 18, 8, 0, 2, TimeSpan.Zero),
            "OTHER", 7);
        var source = From(left.Concat(phaseRight).ToArray());
        var screen = PeriodicDetector.Detect(source, new DetectorConfig());
        Assert(screen.CandidatePatternCount == 2, "phase-changing sequence remains two episodes");
        var result = EpisodeFusion.Group(source, screen, new DetectorConfig());
        Assert(result.ConservativelyLinkedGroupCount == 2, "phase-incompatible episodes never link");
    }

    private static void FusionSeparatesSourceMode()
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 59, 30, TimeSpan.Zero);
        var exchange = SequenceAt(start, "EX", 13);
        var dealer = SequenceAt(start, "DEAL", 13, source: "DEALER");
        var otherMode = SequenceAt(start, "MODE", 13, mode: "OTHER_MODE");
        var source = From(exchange.Concat(dealer).Concat(otherMode).ToArray());
        var screen = PeriodicDetector.Detect(source, new DetectorConfig());
        var fused = EpisodeFusion.Group(source, screen, new DetectorConfig());
        Assert(screen.CandidatePatternCount == 6 && fused.ConservativelyLinkedGroupCount == 3,
            "source and trading mode partition the observed streams");
        Assert(fused.UniqueAttributedPrintCount == 39, "all print IDs preserved");
    }

    private static void FusionRejectsInvalidEvidence()
    {
        var input = From(SequenceAt(new DateTimeOffset(2026, 11, 18, 7, 59, 30, TimeSpan.Zero),
            "BAD", 13));
        var report = PeriodicDetector.Detect(input, new DetectorConfig());
        bool mismatchRejected = false;
        try
        {
            EpisodeFusion.Group(input with { FileSha256 = "changed" }, report, new DetectorConfig());
        }
        catch (ArgumentException) { mismatchRejected = true; }
        Assert(mismatchRejected, "must validate input report hash");

        bool doubleAttributionRejected = false;
        var repeatedPattern = report.Patterns[0];
        try
        {
            EpisodeFusion.Group(input, report with
            {
                Patterns = report.Patterns.Concat(new[] { repeatedPattern }).ToArray()
            }, new DetectorConfig());
        }
        catch (InvalidDataException) { doubleAttributionRejected = true; }
        Assert(doubleAttributionRejected, "must reject reused trade print IDs");
    }


    private static void RotationPreservesRuns()
    {
        var quantities = new long[] { 10, 10, 20, 20, 30, 30, 40, 40 };
        var trades = CreateSequence("ROT", "EXCHANGE", "SELL", 10, 1000, quantities.Length)
            .Select((t, i) => t with { QuantityLots = quantities[i] }).ToArray();
        var input = From(trades);
        var (shifted, moved) = SizeShuffleNull.Shuffle(input, 739, 60, "rotate");
        Assert(moved > 0, "non-uniform sizes should rotate to a different phase");
        Assert(trades.Select(t => t.ExchangeTimeUtc).SequenceEqual(
            shifted.Trades.Select(t => t.ExchangeTimeUtc)), "timestamps must stay unchanged");
        Assert(trades.Select(t => t.QuantityLots).OrderBy(x => x).SequenceEqual(
            shifted.Trades.Select(t => t.QuantityLots).OrderBy(x => x)),
            "local size multiset must be identical");
        int Transitions(IEnumerable<long> xs)
        {
            long[] a = xs.ToArray();
            return Enumerable.Range(1, a.Length - 1).Count(i => a[i] != a[i - 1]);
        }
        Assert(Transitions(shifted.Trades.Select(t => t.QuantityLots)) <=
            Transitions(quantities) + 1,
            "single circular seam can add at most one size transition");
    }

    private static void NullReportIncludesGroups()
    {
        var source = CsvTradeReader.Read(Fixture("synthetic_twap_5s.csv"));
        var original = PeriodicDetector.Detect(source, new DetectorConfig());
        var groups = EpisodeFusion.Group(source, original, new DetectorConfig());
        var report = SizeShuffleNull.Compare(source, new DetectorConfig(), 3, 42, 60, "rotate");
        Assert(report.OriginalConservativelyLinkedGroupCount ==
            groups.ConservativelyLinkedGroupCount, "real-data episode grouping baseline");
        Assert(report.Trials.All(t =>
            t.ConservativelyLinkedGroupCount <= t.NullCandidateEpisodes),
            "fusion cannot create extra groups");
        Assert(report.MeanNullConservativelyLinkedGroupCount >= 0, "group count nonnegative");
        Assert(report.NullFamily == "local_trade_quantity_rotate", "null family provenance");
    }

    private static void InvalidNullVariant()
    {
        bool threw = false;
        try { SizeShuffleNull.Shuffle(From(CreateSequence("X", "EXCHANGE", "SELL", 100, 5000, 7)),
            seed: 7, localWindowSeconds: 60, nullMode: "unsupported"); }
        catch (ArgumentException) { threw = true; }
        Assert(threw, "unknown null variant should be rejected");
    }


    private static MarketTrade[] LongCadence(string prefix, string source = "EXCHANGE")
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        return Enumerable.Range(0, 13).Select(i =>
            new MarketTrade($"{prefix}-{i}", start.AddMinutes(i * 5),
                "SYNTH-LONG", "LONG", source, "SELL", 100m, 100,
                "TQBR", "SESSION-1", "SYNTHETIC", i)).ToArray();
    }

    private static void RollingForecastHasHits()
    {
        var result = RollingForecast.Evaluate(From(LongCadence("LONG")),
            new DetectorConfig { MinMatches = 4 }, warmupMinutes: 20,
            strideMinutes: 10, maximumCutoffsPerSession: 4);
        Assert(result.CutoffsExamined == 4, "must evaluate four prospectively chosen cutoffs");
        Assert(result.ForecastsEvaluated >= 1, "must issue at least one scorable forecast");
        Assert(result.ObservedHits >= 1, "known synthetic periodic prints should be hit");
        Assert(result.ObservedHitRate > 0, "measured hit rate");
        Assert(!result.Calibrated && !result.ActualBotCountKnown,
            "forecast success cannot identify actual bots");
        Assert(result.Observations.All(o => DateTimeOffset.Parse(o.TargetUtc) >
            DateTimeOffset.Parse(o.CutoffUtc)), "targets must be strictly later than cutoff");
    }

    private static void RollingForecastPlaceboAndTime()
    {
        var result = RollingForecast.Evaluate(From(LongCadence("PHASE")),
            new DetectorConfig { MinMatches = 4 }, warmupMinutes: 20,
            strideMinutes: 10, maximumCutoffsPerSession: 4);
        Assert(result.PlaceboHits == 0, "half-period phase shift should miss clean 5min synthetic stream");
        Assert(result.Observations.All(o =>
            (DateTimeOffset.Parse(o.PhaseShiftPlaceboUtc) -
             DateTimeOffset.Parse(o.TargetUtc)).TotalMilliseconds ==
            o.PeriodMilliseconds / 2.0), "placebo phase must be a fixed half-period shift");
    }

    private static void RollingForecastSourceIsolation()
    {
        var source = From(LongCadence("EX", "EXCHANGE")
            .Concat(LongCadence("DEAL", "DEALER")).ToArray());
        var result = RollingForecast.Evaluate(source, new DetectorConfig { MinMatches = 4 },
            warmupMinutes: 20, strideMinutes: 10, maximumCutoffsPerSession: 4);
        Assert(result.SessionSourceGroups == 2, "trade sources must be analysed independently");
        Assert(result.Observations.Select(o => o.TradeSource).Distinct().Count() == 2,
            "both EXCHANGE and DEALER forecast checks must be present");
        Assert(result.Observations.Where(o => o.Hit).All(o =>
            o.MatchedEventId is not null), "hits must have actual future evidence ID");
    }

    private static void RollingForecastUnverifiedCoverage()
    {
        var source = From(LongCadence("UNKNOWN")) with { HasVerifiedFeedCoverage = false };
        var report = RollingForecast.Evaluate(source, new DetectorConfig { MinMatches = 4 },
            warmupMinutes: 20, strideMinutes: 10, maximumCutoffsPerSession: 4);
        Assert(!report.DataCoverageVerified, "read-only file cannot prove complete feed");
        Assert(!report.ActualBotCountKnown && !report.Calibrated, "never invent owner or probability");
        Assert(report.Warnings.Any(w => w.Contains("INCOMPLETE_FEED_CAVEAT")),
            "must explicitly mention missing coverage");
    }


    private static (RollingForecastReport Rolling, ForecastFailureDiagnosticReport Diagnostic)
        RunDiagnostic(MarketTrade[] trades, int warmupMinutes = 20)
    {
        var source = From(trades);
        var cfg = new DetectorConfig { MinMatches = 4 };
        var rolling = RollingForecast.Evaluate(source, cfg,
            warmupMinutes: warmupMinutes, strideMinutes: 30, maximumCutoffsPerSession: 1);
        var diagnostic = ForecastFailureDiagnostics.Analyse(source, rolling, cfg);
        return (rolling, diagnostic);
    }

    private static void DiagnosticCleanCadence()
    {
        var (rolling, diagnostics) = RunDiagnostic(LongCadence("CLEAN"));
        Assert(rolling.ForecastsEvaluated >= 1, "expected a target from clean development tape");
        Assert(diagnostics.ForecastsEvaluated == rolling.ForecastsEvaluated, "same frozen sample");
        Assert(diagnostics.Misses == 0 && diagnostics.ExactHits == rolling.ForecastsEvaluated,
            "clean cadence must not be labelled as a miss");
        Assert(diagnostics.HistoricalAgeBuckets.Sum(b => b.EvaluatedForecasts) ==
               rolling.ForecastsEvaluated, "each forecast belongs to exactly one age group");
        Assert(!diagnostics.StatisticalSignificanceEstablished && !diagnostics.ActualBotCountKnown,
            "do not invent statistical validation or owner IDs");
    }

    private static void DiagnosticDifferentQuantity()
    {
        var trades = LongCadence("CHANGE");
        trades[5] = trades[5] with { QuantityLots = 200 };
        var (rolling, d) = RunDiagnostic(trades);
        Assert(rolling.ForecastsEvaluated == 1 && d.Misses == 1,
            "known changed quantity at next print must miss original exact q");
        Assert(d.MissesWithDifferentSizeInsideExactWindow == 1,
            "same time but changed quantity is an observable hypothesis");
        Assert(d.MissesWithSameSizeOutsideExactWindow == 0,
            "do not invent nearby unchanged clip at a different time");
    }

    private static void DiagnosticTimingShift()
    {
        var trades = LongCadence("DRIFT");
        trades[5] = trades[5] with
        {
            ExchangeTimeUtc = trades[5].ExchangeTimeUtc.AddSeconds(5)
        };
        var (rolling, d) = RunDiagnostic(trades);
        Assert(rolling.ForecastsEvaluated == 1 && d.Misses == 1,
            "5 sec late print should be outside fixed 200ms cap");
        Assert(d.MissesWithSameSizeOutsideExactWindow == 1,
            "matching q but shifted time is a plausible descriptive finding");
        Assert(d.MissesWithDifferentSizeInsideExactWindow == 0,
            "no phantom quantity changes");
    }

    private static void DiagnosticStaleCandidate()
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var oldPrints = Enumerable.Range(0, 6).Select(i => new MarketTrade(
            $"OLD-{i}", start.AddMinutes(i * 5), "SYNTH-LONG", "LONG",
            "EXCHANGE", "SELL", 100m, 100, "TQBR", "SESSION-1", "SYNTHETIC", i));
        var laterPrint = new MarketTrade("UNRELATED", start.AddMinutes(130),
            "SYNTH-LONG", "LONG", "EXCHANGE", "SELL", 100m, 25,
            "TQBR", "SESSION-1", "SYNTHETIC", 100);
        var (rolling, d) = RunDiagnostic(oldPrints.Append(laterPrint).ToArray(), warmupMinutes: 80);
        Assert(rolling.ForecastsEvaluated >= 1, "stale hypothesis must still be scorable");
        Assert(d.MissesWithStaleTrainingPattern >= 1, "stale training evidence 11 periods old");
        Assert(d.HistoricalAgeBuckets.Single(b => b.Name == "stale_over_8_cycles")
            .EvaluatedForecasts >= 1, "stale bucket must reflect the cutoff-time age");
    }

    private static void DiagnosticSourceIsolation()
    {
        var trades = LongCadence("EX");
        trades[5] = trades[5] with { TradeSource = "DEALER" };
        var (rolling, d) = RunDiagnostic(trades);
        Assert(rolling.ForecastsEvaluated == 1 && d.Misses == 1,
            "dealer print must not confirm the exchange-only forecast");
        Assert(d.MissesWithDifferentSizeInsideExactWindow == 0 &&
               d.MissesWithSameSizeOutsideExactWindow == 0 &&
               d.MissesWithOppositeDirectionInsideExactWindow == 0,
            "dealer observations must not masquerade as exchange evidence");
        Assert(d.MissesWithNoSameSidePrintNearTarget == 1,
            "no relevant exchange print near target");
    }

    private static void DiagnosticIntegrity()
    {
        var trades = LongCadence("HASH");
        var source = From(trades);
        var config = new DetectorConfig { MinMatches = 4 };
        var rolling = RollingForecast.Evaluate(source, config, 20, 30, 1);
        bool mismatchRejected = false;
        try
        {
            ForecastFailureDiagnostics.Analyse(source, rolling with
            {
                SourceSha256 = "fake-history"
            }, config);
        }
        catch (ArgumentException) { mismatchRejected = true; }
        Assert(mismatchRejected, "must refuse comparisons against another file's forecasts");

        bool leakageRejected = false;
        var forged = rolling with
        {
            Observations = rolling.Observations.Select(o =>
                o with { LastTrainingEvidenceUtc = o.TargetUtc }).ToArray()
        };
        try { ForecastFailureDiagnostics.Analyse(source, forged, config); }
        catch (InvalidDataException) { leakageRejected = true; }
        Assert(leakageRejected, "must refuse training evidence timestamped after cutoff");
    }


    private static TradeImportResult StaleForecastFixture()
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var stale = Enumerable.Range(0, 6).Select(i => new MarketTrade(
            $"STALE-{i}", start.AddMinutes(i * 5), "SYNTH-LONG", "LONG",
            "EXCHANGE", "SELL", 100m, 100, "TQBR", "SESSION-1", "SYNTHETIC", i));
        var after = new MarketTrade("UNRELATED_AFTER", start.AddMinutes(130),
            "SYNTH-LONG", "LONG", "EXCHANGE", "SELL", 100m, 25,
            "TQBR", "SESSION-1", "SYNTHETIC", 100);
        return From(stale.Append(after).ToArray());
    }

    private static void RecencyGateSuppressesStale()
    {
        var source = StaleForecastFixture();
        var cfg = new DetectorConfig { MinMatches = 4 };
        var old = RollingForecast.Evaluate(source, cfg, 80, 30, 1);
        var gated = RollingForecast.Evaluate(source, cfg, 80, 30, 1,
            maximumTrainingAgeCycles: 2);
        Assert(old.ForecastsEvaluated >= 1, "baseline must contain stale forecasts");
        Assert(gated.ForecastsEvaluated == 0 && gated.MaximumTrainingAgeCycles == 2,
            "historical-only filter should suppress old forecast stream");
        Assert(!gated.Calibrated && !gated.ActualBotCountKnown, "not a confirmed trading signal");
        Assert(gated.Warnings.Any(x => x.StartsWith("DEVELOPMENT_POLICY")),
            "make intervention visible in report");
    }

    private static void RecencyGateKeepsFresh()
    {
        var source = From(LongCadence("FRESH"));
        var cfg = new DetectorConfig { MinMatches = 4 };
        var original = RollingForecast.Evaluate(source, cfg, 20, 10, 4);
        var gated = RollingForecast.Evaluate(source, cfg, 20, 10, 4,
            maximumTrainingAgeCycles: 2);
        Assert(gated.ForecastsEvaluated == original.ForecastsEvaluated &&
               gated.ObservedHits == original.ObservedHits &&
               gated.PlaceboHits == original.PlaceboHits,
               "all recent 5-minute print hypotheses should be unchanged");
        Assert(gated.MaximumTrainingAgeCycles == 2, "report the exact gate policy");
    }

    private static void RecencyGateIndependentOfOutcome()
    {
        var baseline = LongCadence("OUT");
        var changedFuture = LongCadence("OUT");
        changedFuture[5] = changedFuture[5] with { QuantityLots = 200 };
        var config = new DetectorConfig { MinMatches = 4 };
        var baselineReport = RollingForecast.Evaluate(From(baseline), config,
            20, 30, 1, maximumTrainingAgeCycles: 2);
        var changedReport = RollingForecast.Evaluate(From(changedFuture), config,
            20, 30, 1, maximumTrainingAgeCycles: 2);
        Assert(baselineReport.ForecastsEvaluated == 1 && changedReport.ForecastsEvaluated == 1,
            "same prefix must have same eligible prediction regardless of future volume");
        Assert(baselineReport.ObservedHits == 1 && changedReport.ObservedHits == 0,
            "only outcome differs; eligibility is frozen at the cutoff");
        Assert(baselineReport.Observations.Single().LastTrainingEvidenceUtc ==
               changedReport.Observations.Single().LastTrainingEvidenceUtc,
            "same historical last evidence");
    }

    private static void RecencyGateRejectsInvalid()
    {
        var input = From(LongCadence("PARAM"));
        bool threw = false;
        try { RollingForecast.Evaluate(input, new DetectorConfig { MinMatches = 4 },
            20, 10, 1, maximumTrainingAgeCycles: 0); }
        catch (ArgumentException) { threw = true; }
        Assert(threw, "zero cycles must be invalid");
        threw = false;
        try { WalkForward.Evaluate(input, new DateTimeOffset(2026, 11, 18, 7, 20, 0, TimeSpan.Zero),
            new DetectorConfig { MinMatches = 4 }, maximumTrainingAgeCycles: -1); }
        catch (ArgumentException) { threw = true; }
        Assert(threw, "negative cycles must be invalid");
    }


    private static MarketTrade[] VariableCadenceFixture(
        string prefix, string source = "EXCHANGE", string direction = "SELL", int count = 12)
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        long[] q = { 10, 20, 30, 40 };
        return Enumerable.Range(0, count).Select(i =>
            new MarketTrade($"{prefix}-{i}", start.AddSeconds(i * 5),
                "SYNTH-VARIABLE", "VAR", source, direction, 100m,
                q[i % q.Length], "TQBR", "SESSION-1", "SYNTHETIC", i)).ToArray();
    }

    private static void VariableCadenceSynthetic()
    {
        var source = CsvTradeReader.Read(Fixture("synthetic_variable_clip_5s.csv"));
        Assert(source.Trades.Count == 12, "synthetic clip fixture must contain 12 prints");
        var report = VariableSizeCadence.Detect(source, new VariableCadenceConfig());
        Assert(report.CandidateSequenceCount == 1,
            "12 regular variable-size prints should produce one observable candidate");
        var p = report.Candidates.Single();
        Assert(p.PeriodMs == 5000 && p.MatchedPrints == 12 && p.DistinctQuantities == 4,
            "known synthetic 5s, four clip sizes");
        Assert(p.CoverageRatio == 1 && p.ObservedLots == 300,
            "all 12 synthetic clips must be attributed once");
        Assert(p.State == "candidate" && !p.OwnerKnown && p.ConfidenceCalibrated is null,
            "cannot claim a physical robot identity or calibrated confidence");
        Assert(!report.PhysicalBotCountKnown && !report.StatisticalSignificanceEstablished,
            "research-only model status");
    }

    private static void VariableCadenceRejectsConstantQuantity()
    {
        var original = VariableCadenceFixture("CONSTANT");
        var fixedLots = original.Select(x => x with { QuantityLots = 100 }).ToArray();
        Assert(VariableSizeCadence.Detect(From(fixedLots), new VariableCadenceConfig())
               .CandidateSequenceCount == 0,
            "variable-clip experimental screen deliberately excludes one clip size");
    }

    private static void VariableCadenceSourceIsolation()
    {
        var a = VariableCadenceFixture("EX", "EXCHANGE");
        var b = VariableCadenceFixture("DL", "DEALER");
        var source = From(a.Concat(b).ToArray());
        var result = VariableSizeCadence.Detect(source, new VariableCadenceConfig());
        Assert(result.CandidateSequenceCount == 2, "sources must be analysed independently");
        Assert(result.Candidates.Select(p => p.TradeSource).Distinct().Count() == 2,
            "must not blend an exchange stream with a dealer stream");
        Assert(result.Candidates.SelectMany(p => p.EvidenceEventIds).Distinct().Count() == 24,
            "no double attribution of synthetic prints");
    }

    private static void VariableCadenceDenseWindow()
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var dense = Enumerable.Range(0, 2510).Select(i => new MarketTrade(
            $"DENSEVAR-{i}", start.AddMilliseconds(i * 100), "SYNTH-DENSE", "DENSE",
            "EXCHANGE", "SELL", 100m, (i % 4 + 1) * 10L,
            "TQBR", "SESSION-1", "SYNTHETIC", i)).ToArray();
        var report = VariableSizeCadence.Detect(From(dense), new VariableCadenceConfig());
        Assert(report.SplitDenseWindowCount == 1 && report.SkippedDenseWindowCount == 0,
            "large window must be split instead of losing the entire source");
        Assert(report.SkippedTinyRemainderCount == 0, "10-event tail is large enough to inspect");
        Assert(report.Warnings.Any(w => w.StartsWith("DENSE_WINDOW_SPLIT")),
            "show potential continuity loss across chunks");
        Assert(report.Candidates.SelectMany(x => x.EvidenceEventIds).Distinct().Count() ==
            report.UniqueAttributedPrints,
            "evidence must remain unique across the disjoint chunks");
    }


    private static void VariableCadenceTinyRemainder()
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var events = Enumerable.Range(0, 2505).Select(i => new MarketTrade(
            $"TAIL-{i}", start.AddMilliseconds(i * 100), "SYNTH-TAIL", "TAIL",
            "EXCHANGE", "SELL", 100m, (i % 3 + 1) * 10L,
            "TQBR", "SESSION-1", "SYNTHETIC", i)).ToArray();
        var result = VariableSizeCadence.Detect(From(events), new VariableCadenceConfig());
        Assert(result.SplitDenseWindowCount == 1 && result.SkippedTinyRemainderCount == 1,
            "5 leftover prints below 8-print threshold must be reported");
        Assert(result.Warnings.Any(w => w.StartsWith("TINY_CHUNK_NOT_EVALUATED")),
            "do not silently discard the final small chunk");
        Assert(result.UniqueAttributedPrints <= 2500,
            "no tail prints may be falsely attributed after explicit skip");
    }

    private static void TemporalNullPreservation()
    {
        var source = From(VariableCadenceFixture("TEMP"));
        var (resampled, changed) = TemporalCadenceNull.Resample(source, "uniform", 101, 60);
        Assert(changed > 0 && resampled.Trades.Count == source.Trades.Count,
            "all synthetic prints remain but timestamps move");
        Assert(resampled.Trades.Select(t => t.EventId).OrderBy(x => x).SequenceEqual(
            source.Trades.Select(t => t.EventId).OrderBy(x => x)),
            "event IDs and cardinality must remain identical");
        Assert(resampled.Trades.Sum(t => t.QuantityLots) == source.Trades.Sum(t => t.QuantityLots),
            "total lots are preserved");
        Assert(resampled.Trades.All(t => t.ExchangeTimeUtc.Minute == 0 &&
                    t.TradingMode == "TQBR" && t.TradeSource == "EXCHANGE"),
            "uniform resampling stays inside same calendar-minute/source/mode bucket");
    }

    private static void TemporalNullRotation()
    {
        var source = From(VariableCadenceFixture("ROTATE"));
        var (resampled, changed) = TemporalCadenceNull.Resample(source, "rotate", 10, 60);
        var byId = resampled.Trades.ToDictionary(t => t.EventId, StringComparer.Ordinal);
        long interval = TimeSpan.TicksPerMinute;
        var shifts = source.Trades.Select(t =>
            (byId[t.EventId].ExchangeTimeUtc.Ticks - t.ExchangeTimeUtc.Ticks + interval) % interval)
            .Distinct().ToArray();
        Assert(changed == source.Trades.Count && shifts.Length == 1 && shifts[0] > 0,
            "circular rotation must preserve one within-minute phase offset for every trade");
    }

    private static void TemporalNullComparison()
    {
        var source = From(VariableCadenceFixture("NULL"));
        var cfg = new VariableCadenceConfig();
        var first = TemporalCadenceNull.Compare(source, cfg, "uniform", 3, 17, 60);
        var second = TemporalCadenceNull.Compare(source, cfg, "uniform", 3, 17, 60);
        Assert(first.Trials.SequenceEqual(second.Trials), "null metrics reproducible by seed");
        Assert(first.OriginalCandidateSequences == 1 && first.TrialsRun == 3,
            "control must use same detector on original data and three shuffled tapes");
        Assert(first.Trials.All(t => t.CandidateSequences >= 0),
            "candidate count is nonnegative");
        Assert(!first.ActualBotCountKnown && !first.SignificanceCalibrated,
            "descriptive null cannot imply a probability or number of actual robots");
    }

    private static void VariableCadenceInvalidConfiguration()
    {
        bool rejected = false;
        try { new VariableCadenceConfig { MinDistinctQuantities = 1 }.Validate(); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "must reject trivial one-size variation");
        rejected = false;
        try { TemporalCadenceNull.Resample(From(VariableCadenceFixture("BAD")), "unknown", 5); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "unknown clock-null model must fail closed");
    }


    private static MarketTrade[] FlowSeries(
        string prefix, string source = "EXCHANGE", int secondOffset = 0)
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero)
            .AddSeconds(secondOffset);
        string[] directions = { "BUY", "BUY", "SELL", "SELL" };
        long[] quantities = { 10, 20, 10, 20 };
        return Enumerable.Range(0, 4).Select(i =>
            new MarketTrade($"{prefix}-{i}", start.AddSeconds(i),
                "SYN-FLOW", "FLOW", source, directions[i], 100m, quantities[i],
                "TQBR", "SESSION-1", "SYNTHETIC", i)).ToArray();
    }

    private static void FlowFootprintRegular()
    {
        var output = FlowFootprint.Describe(From(FlowSeries("FOOT")));
        Assert(output.WindowCount == 1 && output.InputPrints == 4,
            "four prints in one five-minute source/time window");
        var w = output.Windows.Single();
        Assert(w.TotalLots == 60 && w.BuyReportedLots == 30 &&
               w.SellReportedLots == 30 && w.UnknownDirectionLots == 0,
            "strict lot conservation");
        Assert(w.ReportedDirectionImbalance == 0, "reported buy and sell volumes are equal");
        Assert(w.LongestBuyReportedRun == 2 && w.LongestSellReportedRun == 2,
            "two consecutive known-side prints for each run");
        Assert(Math.Abs(w.LagOneReportedSignAgreement!.Value - 2.0 / 3) < 1e-12,
            "two adjacent same-side pairs out of three");
        Assert(w.MedianInterarrivalMs == 1000 && w.InterarrivalCoefficientOfVariation == 0,
            "equal one-second inter-arrival deltas");
        Assert(w.PrintCountFanoFactor == 0 && w.IncludedClockBins == 4,
            "all four equally occupied one-second bins imply Fano=0");
        Assert(w.NearWholeSecondPrints == 4 && w.NearWholeSecondPrintShare == 1,
            "all prints exactly on whole seconds");
        Assert(!output.ActualBotCountKnown && !output.StatisticalSignificanceEstablished,
            "counts are descriptive and no owner is known");
    }

    private static void FlowFootprintBurst()
    {
        var input = FlowSeries("CLUSTER");
        var start = input[0].ExchangeTimeUtc;
        for (int i = 0; i < 3; i++)
            input[i] = input[i] with { ExchangeTimeUtc = start };
        input[3] = input[3] with { ExchangeTimeUtc = start.AddSeconds(10) };
        var result = FlowFootprint.Describe(From(input));
        var w = result.Windows.Single();
        Assert(w.IncludedClockBins == 11, "include nine unoccupied internal bins");
        Assert(w.PrintCountFanoFactor > 2, "three same-time prints should yield clustering");
        Assert(w.MedianInterarrivalMs == 0 && w.InterarrivalCoefficientOfVariation > 1,
            "clock-time burst intervals show variability");
        Assert(w.PublicPrintCount == 4 && w.TotalLots == 60,
            "timestamps can collide without losing actual prints");
    }

    private static void FlowFootprintPartition()
    {
        var ex = FlowSeries("EX");
        var dealer = FlowSeries("DL", "DEALER");
        var later = FlowSeries("LATE", secondOffset: 301);
        var report = FlowFootprint.Describe(From(ex.Concat(dealer).Concat(later).ToArray()));
        Assert(report.WindowCount == 3, "one source 07:00, dealer 07:00, exchange 07:05");
        Assert(report.Windows.Select(w => w.PublicPrintCount).Sum() == 12,
            "all prints included, no attribution overlap");
        Assert(report.Windows.Select(w => w.TradeSource).Distinct().Count() == 2,
            "source/venue split");
        Assert(report.Windows.All(w => w.TotalLots == 60),
            "lot conservation in each independent window");
    }

    private static void FlowFootprintUnknownSide()
    {
        var input = FlowSeries("UN")
            .Select(t => t with { ReportedDirection = "UNKNOWN" }).ToArray();
        var w = FlowFootprint.Describe(From(input)).Windows.Single();
        Assert(w.BuyReportedLots == 0 && w.SellReportedLots == 0 &&
               w.UnknownDirectionLots == 60, "unknown quantity tracked separately");
        Assert(w.ReportedDirectionImbalance is null &&
               w.LagOneReportedSignAgreement is null &&
               w.LongestBuyReportedRun == 0 && w.LongestSellReportedRun == 0,
            "cannot imply trade direction where provider does not supply it");
    }

    private static void FlowFootprintConfigValidation()
    {
        bool rejected = false;
        try { new FlowFootprintConfig { WindowMinutes = 0 }.Validate(); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "zero-minute windows invalid");
        rejected = false;
        try { FlowFootprint.Describe(From(FlowSeries("INVALID")),
            new FlowFootprintConfig { ClockPhaseThresholdMilliseconds = 1000 }); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "phase beyond half-second invalid");
    }


    private static MarketTrade[] MakeActivityTape(
        bool balancedBurst = false, bool missingBucket = false,
        string baselineSource = "EXCHANGE", string burstSource = "EXCHANGE")
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var list = new List<MarketTrade>();
        for (int w = 0; w < 5; w++)
        {
            int actualWindow = missingBucket && w == 4 ? 5 : w;
            int count = w == 4 ? 20 : 5;
            for (int i = 0; i < count; i++)
            {
                bool burst = w == 4;
                list.Add(new MarketTrade($"ACT-{w}-{i}",
                    start.AddMinutes(actualWindow * 5).AddSeconds(i),
                    "SYNTH-ACT", "ACT",
                    burst ? burstSource : baselineSource,
                    burst ? balancedBurst && i % 2 == 1 ? "SELL" : "BUY"
                          : i % 2 == 0 ? "BUY" : "SELL",
                    100m, burst ? 100 : 10, "TQBR", "SESSION-1",
                    "SYNTHETIC", w * 100 + i));
            }
        }
        return list.ToArray();
    }

    private static void ActivityEpisodeDetectsBurst()
    {
        var tape = CsvTradeReader.Read(Fixture("synthetic_activity_episode.csv"));
        Assert(tape.Trades.Count == 40, "fixture must contain four 5-print baselines and 20-print burst");
        var footprints = FlowFootprint.Describe(tape);
        var result = FlowActivityEpisodes.Find(footprints);
        Assert(footprints.WindowCount == 5 && result.EvaluatedWindows == 1,
            "four quiet windows establish historical-only reference");
        Assert(result.ActivityWindowCount == 1 &&
               result.UnscorableWarmupOrGapWindows == 4, "one burst, four warmup windows");
        var activity = result.ActivityWindows.Single();
        Assert(activity.PublicPrintCount == 20 && activity.TotalLots == 2000,
            "observed burst public volume");
        Assert(activity.BaselineMedianPrintCount == 5 && activity.BaselineMedianLots == 50,
            "only four earlier windows used for baseline");
        Assert(activity.PrintCountRatio == 4 && activity.TotalLotsRatio == 40,
            "burst is four times as many prints and 40 times as many lots");
        Assert(activity.Label == "reported_buy_dominant_high_activity" &&
               activity.State == "unvalidated_observed_activity" && !activity.ActorIdentityKnown,
            "return descriptive reported-side label with no bot identity");
        Assert(!result.ActualBotCountKnown && !result.SignificanceCalibrated,
            "cannot invent owners or calibrated probability");
    }

    private static void ActivityEpisodeNeedsDirectionalDominance()
    {
        var footprints = FlowFootprint.Describe(From(MakeActivityTape(balancedBurst: true)));
        var result = FlowActivityEpisodes.Find(footprints);
        Assert(result.EvaluatedWindows == 1 && result.ActivityWindowCount == 0,
            "balanced buy/sell print volumes do not meet dominant-side rule");
    }

    private static void ActivityEpisodeSourceIsolation()
    {
        var footprints = FlowFootprint.Describe(From(
            MakeActivityTape(baselineSource: "EXCHANGE", burstSource: "DEALER")));
        var result = FlowActivityEpisodes.Find(footprints);
        Assert(result.EvaluatedWindows == 0 && result.ActivityWindowCount == 0,
            "dealer burst may not use exchange-only historical baseline");
    }

    private static void ActivityEpisodeResetsOnGap()
    {
        var footprints = FlowFootprint.Describe(From(MakeActivityTape(missingBucket: true)));
        var result = FlowActivityEpisodes.Find(footprints);
        Assert(result.EvaluatedWindows == 0 && result.ActivityWindowCount == 0,
            "a missing five-minute source bucket resets historical reference");
    }

    private static void ActivityEpisodeNoFutureLeakage()
    {
        var original = MakeActivityTape();
        var extra = original.Concat(new[]
        {
            new MarketTrade("SIXTH", new DateTimeOffset(2026, 11, 18, 7, 25, 0, TimeSpan.Zero),
                "SYNTH-ACT", "ACT", "EXCHANGE", "SELL", 101m, 1000,
                "TQBR", "SESSION-1", "SYNTHETIC", 999)
        }).ToArray();
        var first = FlowActivityEpisodes.Find(FlowFootprint.Describe(From(original)));
        var extended = FlowActivityEpisodes.Find(FlowFootprint.Describe(From(extra)));
        Assert(first.ActivityWindows.Count == 1,
            "baseline burst expected");
        Assert(extended.ActivityWindows.Any(x =>
            x.WindowStartUtc == first.ActivityWindows[0].WindowStartUtc &&
            x.PublicPrintCount == first.ActivityWindows[0].PublicPrintCount &&
            x.BaselineMedianLots == first.ActivityWindows[0].BaselineMedianLots),
            "later data cannot revise past episode's reference or label");
    }

    private static void ActivityEpisodeInvalidSettings()
    {
        bool rejected = false;
        try { new FlowActivityConfig { ReferenceWindows = 1 }.Validate(); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "one bucket is not enough historical reference");
        rejected = false;
        try { FlowActivityEpisodes.Find(FlowFootprint.Describe(From(MakeActivityTape())),
            new FlowActivityConfig { MinimumCountRatio = 1 }); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "ratio <=1 invalid");
    }

    private static void BadConfig()
    {
        bool threw = false;
        try { new DetectorConfig { MinCoverage = 1.5 }.Validate(); }
        catch (ArgumentException) { threw = true; }
        Assert(threw, "invalid coverage range not rejected");
    }
}
