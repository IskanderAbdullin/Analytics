using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;
using RobotDetector.Core;

namespace RobotDetector.Cli;

internal static class Program
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true,
        Converters = { new JsonStringEnumConverter() }
    };

    public static async Task<int> Main(string[] args)
    {
        if (args.Length == 0 || args[0] is "--help" or "-h" or "help")
        {
            PrintHelp();
            return 0;
        }

        try
        {
            var options = ParseOptions(args.Skip(1).ToArray());
            switch (args[0].ToLowerInvariant())
            {
                case "detect":
                    return Detect(options);
                case "fetch":
                    return await FetchAsync(options);
                case "quote":
                    return Quote(options);
                case "benchmark":
                    return Benchmark(options);
                case "walkforward":
                    return Walkforward(options);
                case "spectrum":
                    return Spectrum(options);
                case "null-shuffle":
                    return NullShuffle(options);
                case "fusion":
                    return Fusion(options);
                case "rolling-forecast":
                    return RollingForecastCommand(options);
                case "diagnose-forecast":
                    return DiagnoseForecastCommand(options);
                case "variable-cadence":
                    return VariableCadenceCommand(options);
                case "variable-temporal-null":
                    return VariableTemporalNullCommand(options);
                case "flow-footprint":
                    return FlowFootprintCommand(options);
                case "activity-episodes":
                    return ActivityEpisodesCommand(options);
                case "clock-phase-audit":
                    return ClockPhaseCommand(options);
                case "timestamp-quality":
                    return TimestampQualityCommand(options);
                case "cluster-compare":
                    return ClusterCompareCommand(options);
                case "dashboard":
                    return DashboardCommand(options);
                case "replay-audit":
                    return ReplayAuditCommand(options);
                case "compare-archives":
                    return CompareArchivesCommand(options);
                case "benchmark-blind":
                    return BlindBenchmarkCommand(options);
                case "benchmark-clock-null":
                    return ClockNullBenchmarkCommand(options);
                case "benchmark-abides-blind":
                    return AbidesBlindCommand(options);
                default:
                    Console.Error.WriteLine($"Unknown command: {args[0]}");
                    PrintHelp();
                    return 2;
            }
        }
        catch (Exception ex) when (ex is ArgumentException or IOException or FormatException
                                     or HttpRequestException or InvalidDataException or JsonException)
        {
            Console.Error.WriteLine($"ERROR: {ex.Message}");
            return 2;
        }
    }

    private static int Detect(Dictionary<string, string> options)
    {
        string input = Required(options, "input");
        int maxRows = Integer(options, "max-rows", 1_000_000);
        var imported = CsvTradeReader.Read(input, maxRows);
        var config = new DetectorConfig
        {
            MinMatches = Integer(options, "min-matches", 6),
            MinCoverage = Double(options, "min-coverage", 0.55),
            MinimumPeriodMilliseconds = Integer(options, "min-period-ms", 200),
            MaximumPeriodMilliseconds = Integer(options, "max-period-ms", 600000),
            MaximumEventsPerGroup = Integer(options, "max-group-events", 5000),
            AnalysisWindowMinutes = Integer(options, "window-minutes", 60)
        };
        var report = PeriodicDetector.Detect(imported, config);
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out var output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Report saved to {output}");
        }
        else Console.WriteLine(json);

        if (options.TryGetValue("rejects", out var rejects))
        {
            EnsureNewFile(rejects);
            File.WriteAllText(rejects, JsonSerializer.Serialize(imported.RejectedRows, JsonOptions));
        }

        Console.Error.WriteLine($"Trades={report.SourceTradeCount}; rejected_total={report.RejectedRowCount};" +
                                $" candidates={report.CandidatePatternCount}; physical_bot_count=UNKNOWN");
        return imported.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static async Task<int> FetchAsync(Dictionary<string, string> options)
    {
        string date = Required(options, "date");
        string instrumentId = Required(options, "instrument-id");
        string output = Required(options, "output");
        if (!DateOnly.TryParseExact(date, "yyyy-MM-dd", CultureInfo.InvariantCulture,
                DateTimeStyles.None, out var parsed))
            throw new ArgumentException("Use --date YYYY-MM-DD.");
        if (parsed > DateOnly.FromDateTime(DateTime.UtcNow))
            throw new ArgumentException("Future archive date is invalid.");
        if (instrumentId.Length > 128 || instrumentId.Length < 2 ||
            !instrumentId.All(c => char.IsAsciiLetterOrDigit(c) || c is '_' or '-'))
            throw new ArgumentException("Instrument ID must be a T-Invest UID or ticker_classCode.");
        if (!output.EndsWith(".zip", StringComparison.OrdinalIgnoreCase) &&
            !output.EndsWith(".csv", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Output must end in .csv or .zip.");
        EnsureNewFile(output);

        // T-Invest public archive endpoint; read-only historical data.
        var uri = new Uri($"https://invest-public-api.tbank.ru/history-trades/{date}" +
                          $"?instrumentId={Uri.EscapeDataString(instrumentId)}");
        using var client = new HttpClient { Timeout = TimeSpan.FromMinutes(3) };
        client.DefaultRequestHeaders.UserAgent.ParseAdd("RobotDetector-ReadOnly/0.1");
        using var reply = await client.GetAsync(uri, HttpCompletionOption.ResponseHeadersRead);
        if (reply.StatusCode == System.Net.HttpStatusCode.NotFound)
            throw new HttpRequestException("History archive not available (HTTP 404).");
        if ((int)reply.StatusCode == 429)
            throw new HttpRequestException("Rate limited (HTTP 429); no automatic retry, respect provider limit.");
        reply.EnsureSuccessStatusCode();
        if (reply.Content.Headers.ContentLength is > 250_000_000)
            throw new InvalidDataException("Archive too large (>250 MB).");

        string temp = output + ".part";
        try
        {
            await using (var source = await reply.Content.ReadAsStreamAsync())
            await using (var destination = new FileStream(temp, FileMode.CreateNew, FileAccess.Write))
            {
                byte[] buffer = new byte[65536];
                long total = 0;
                int read;
                while ((read = await source.ReadAsync(buffer)) != 0)
                {
                    total += read;
                    if (total > 250_000_000)
                        throw new InvalidDataException("Archive exceeds 250 MB download bound.");
                    await destination.WriteAsync(buffer.AsMemory(0, read));
                }
            }

            byte[] magic = new byte[4];
            using (var file = File.OpenRead(temp))
            {
                if (file.Read(magic) < 2)
                    throw new InvalidDataException("Downloaded archive is empty.");
            }
            bool isZip = magic[0] == 0x50 && magic[1] == 0x4b;
            if (isZip != output.EndsWith(".zip", StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException(isZip
                    ? "Received ZIP; choose a .zip output path."
                    : "Received CSV; choose a .csv output path.");
            File.Move(temp, output);
        }
        finally { if (File.Exists(temp)) File.Delete(temp); }

        Console.WriteLine($"Downloaded {uri.GetLeftPart(UriPartial.Path)} into {output}.");
        Console.WriteLine("Archive coverage, license and trade-side semantics are not verified by a successful download.");
        return 0;
    }











    private static int AbidesBlindCommand(Dictionary<string, string> options)
    {
        var report = AbidesBlindEvaluation.Score(
            Required(options, "public"), Required(options, "truth"));
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out var path))
        {
            EnsureNewFile(path);
            File.WriteAllText(path, json + Environment.NewLine);
            Console.WriteLine($"ABIDES-NG blind evidence assessment saved to {path}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine($"ABIDES-NG simulated public prints={report.PublicPrints}; " +
            "private execution-agent labels were used only for post-detection scoring; " +
            "real market accuracy and physical identities are NOT established.");
        return 0;
    }

    private static int ClockNullBenchmarkCommand(Dictionary<string, string> options)
    {
        var report = MarketClockNullStress.Run(
            trials: Integer(options, "trials", 20),
            backgroundPrints: Integer(options, "background-prints", 120),
            cycles: Integer(options, "cycles", 12),
            periodMilliseconds: Integer(options, "period-ms", 5000),
            clipMode: options.GetValueOrDefault("clip-mode", "fixed"));
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out var path))
        {
            EnsureNewFile(path);
            File.WriteAllText(path, json + Environment.NewLine);
            Console.WriteLine($"Clocked negative-control research saved to {path}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine($"Clocked synthetic null trials={report.Trials}; " +
            "false alarms are toy-background measurements, NOT calibrated market precision.");
        return 0;
    }

    private static int BlindBenchmarkCommand(Dictionary<string, string> options)
    {
        var report = BlindExecutionBenchmark.Run(
            seedsPerKind: Integer(options, "seeds", 5),
            backgroundPrints: Integer(options, "background-prints", 120));
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out var path))
        {
            EnsureNewFile(path);
            File.WriteAllText(path, json + Environment.NewLine);
            Console.WriteLine($"Hidden-truth synthetic comparison saved to {path}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine($"Blinded synthetic cases={report.Cases}; " +
            "no real-market bot or owner identification, no calibrated accuracy.");
        return 0;
    }

    private static int CompareArchivesCommand(Dictionary<string, string> options)
    {
        var paths = Required(options, "inputs").Split(';',
            StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        if (paths.Length is < 2 or > 20)
            throw new ArgumentException("Provide 2..20 semicolon-separated --inputs file paths.");
        if (paths.Select(Path.GetFullPath)
                .Distinct(StringComparer.OrdinalIgnoreCase).Count() != paths.Length)
            throw new ArgumentException("An input path is repeated.");
        int maxRows = Integer(options, "max-rows", 1_000_000);
        int width = Integer(options, "window-minutes", 5);
        var reports = paths.Select(path =>
            ResearchDashboard.Build(CsvTradeReader.Read(path, maxRows), width)).ToArray();
        var comparison = ResearchComparison.Compare(reports);
        string outputHtml = Required(options, "html");
        if (!outputHtml.EndsWith(".html", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("--html output must end in .html.");
        string? outputJson = options.GetValueOrDefault("json");
        if (outputJson is not null && !outputJson.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("--json output must end in .json.");
        if (outputJson is not null &&
            Path.GetFullPath(outputHtml).Equals(Path.GetFullPath(outputJson),
                StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("HTML and JSON paths must differ.");

        string html = ResearchComparison.ToStandaloneHtml(comparison);
        string? json = outputJson is null ? null :
            JsonSerializer.Serialize(comparison, JsonOptions);
        EnsureNewFile(outputHtml);
        if (outputJson is not null) EnsureNewFile(outputJson);
        File.WriteAllText(outputHtml, html);
        if (outputJson is not null) File.WriteAllText(outputJson, json);
        Console.WriteLine($"Offline comparison saved to {outputHtml}");
        if (outputJson is not null) Console.WriteLine($"Aggregate comparison JSON saved to {outputJson}");
        Console.Error.WriteLine(
            $"Distinct source archives={comparison.InputArchiveCount}, " +
            $"public prints={comparison.TotalPublicPrints}; " +
            "not a count of physical robots, no trading or network access");
        return reports.Any(r => r.RejectedRows > 0) ? 3 : 0;
    }

    private static int ReplayAuditCommand(Dictionary<string, string> options)
    {
        var imported = CsvTradeReader.Read(Required(options, "input"),
            Integer(options, "max-rows", 1_000_000));
        var replay = BoundedEventReplay.Analyse(imported, new ReplayAuditConfig
        {
            AllowedLatenessMilliseconds = Integer(options, "lateness-ms", 500),
            MaximumPendingEvents = Integer(options, "max-pending", 10_000),
            WindowMinutes = Integer(options, "window-minutes", 5),
            ReceiptOrdering = options.GetValueOrDefault("receipt-order", "archive_row")
        });
        string json = JsonSerializer.Serialize(replay, JsonOptions);
        if (options.TryGetValue("output", out var path))
        {
            EnsureNewFile(path);
            File.WriteAllText(path, json + Environment.NewLine);
            Console.WriteLine($"Event-time replay audit saved to {path}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine(
            $"Replayed={replay.ReplayedPrints}/{replay.InputPrints}, " +
            $"late={replay.LateAfterWatermarkCount}, " +
            $"outOfOrder={replay.OutOfOrderArrivalCount}, " +
            $"forcedFlushes={replay.ForcedQueueFlushCount}, " +
            "feed completeness UNVERIFIED, no owner inference");
        return imported.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static int DashboardCommand(Dictionary<string, string> options)
    {
        var imported = CsvTradeReader.Read(Required(options, "input"),
            Integer(options, "max-rows", 1_000_000));
        string htmlPath = Required(options, "html");
        if (!htmlPath.EndsWith(".html", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("--html output must have .html extension.");
        string? jsonPath = options.GetValueOrDefault("json");
        if (jsonPath is not null && !jsonPath.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("--json output must have .json extension.");
        if (jsonPath is not null &&
            Path.GetFullPath(jsonPath).Equals(Path.GetFullPath(htmlPath),
                StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("HTML and JSON output paths must be different.");

        var report = ResearchDashboard.Build(imported,
            windowMinutes: Integer(options, "window-minutes", 5));
        string html = ResearchDashboard.ToStandaloneHtml(report,
            maximumVisibleWindows: Integer(options, "max-visible-windows", 240));
        string? json = jsonPath is null ? null : JsonSerializer.Serialize(report, JsonOptions);
        EnsureNewFile(htmlPath);
        if (jsonPath is not null) EnsureNewFile(jsonPath);
        File.WriteAllText(htmlPath, html);
        if (jsonPath is not null) File.WriteAllText(jsonPath, json);
        Console.Error.WriteLine(
            $"Offline dashboard: public prints={report.PublicPrints}, " +
            $"populated windows={report.PopulatedWindows}, " +
            $"timestamp-colliding prints={report.PrintsSharingTimestamp}, " +
            $"reported elevated-activity windows={report.ElevatedActivityWindows}; " +
            "actual physical bot count UNKNOWN, no network or trading calls");
        Console.WriteLine($"HTML report saved to {htmlPath}");
        if (jsonPath is not null) Console.WriteLine($"Aggregated JSON saved to {jsonPath}");
        return imported.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static int ActivityEpisodesCommand(Dictionary<string, string> options)
    {
        var source = CsvTradeReader.Read(Required(options, "input"),
            Integer(options, "max-rows", 1_000_000));
        var flow = FlowFootprint.Describe(source, new FlowFootprintConfig
        {
            WindowMinutes = Integer(options, "window-minutes", 5),
            CountBinSeconds = Integer(options, "bin-seconds", 1)
        });
        var result = FlowActivityEpisodes.Find(flow, new FlowActivityConfig
        {
            ReferenceWindows = Integer(options, "reference-windows", 4),
            MinimumPrintCount = Integer(options, "min-prints", 10),
            MinimumCountRatio = Double(options, "min-count-ratio", 3),
            MinimumLotRatio = Double(options, "min-lot-ratio", 3),
            MinimumAbsoluteReportedImbalance = Double(options, "min-abs-imbalance", 0.6)
        });
        string json = JsonSerializer.Serialize(result, JsonOptions);
        if (options.TryGetValue("output", out var output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Research-only high-activity window observations saved to {output}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine($"Evaluated windows={result.EvaluatedWindows}; " +
            $"flagged observable activity windows={result.ActivityWindowCount}; " +
            "actual physical bot count UNKNOWN");
        return source.RejectedRowTotal > 0 ? 3 : 0;
    }




    private static int ClusterCompareCommand(Dictionary<string, string> options)
    {
        var input = CsvTradeReader.Read(Required(options, "input"));
        var config = new DetectorConfig
        {
            MinMatches = Integer(options, "min-matches", 6),
            AnalysisWindowMinutes = Integer(options, "window-minutes", 60),
            MaximumEventsPerGroup = Integer(options, "max-group-events", 5000)
        };
        var comparison = ObservablePrintClusters.CompareFixedSize(input, config);
        string json = JsonSerializer.Serialize(comparison, JsonOptions);
        if (options.TryGetValue("output", out string? path))
        {
            EnsureNewFile(path);
            File.WriteAllText(path, json + Environment.NewLine);
            Console.WriteLine($"Derived-versus-raw candidate comparison saved to {path}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine(
            $"Public prints={comparison.OriginalPublicPrints}; " +
            $"derived observational clusters={comparison.DerivedObservableClusters}; " +
            $"raw candidates={comparison.OriginalFixedSizeCandidateEpisodes}; " +
            $"derived-view candidates={comparison.DerivedClusterSizeCandidateEpisodes}; " +
            "neither number is a confirmed bot count");
        return input.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static int TimestampQualityCommand(Dictionary<string, string> options)
    {
        var input = CsvTradeReader.Read(Required(options, "input"));
        var report = TimestampQualityAudit.Describe(input);
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out string? path))
        {
            EnsureNewFile(path);
            File.WriteAllText(path, json + Environment.NewLine);
            Console.WriteLine($"Read-only timestamp quality report saved to {path}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine(
            $"Time-source groups={report.SourceGroups}; public prints={report.SourcePrints}; " +
            "equal timestamps are not duplicate prints or bot identities.");
        return input.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static int ClockPhaseCommand(Dictionary<string, string> options)
    {
        var input = CsvTradeReader.Read(Required(options, "input"));
        var report = ClockPhaseAudit.Analyse(input, new ClockPhaseConfig
        {
            FirstMilliseconds = Integer(options, "first-ms", 100),
            MinPrintsPerGroup = Integer(options, "min-prints", 100),
            NullTrials = Integer(options, "trials", 99),
            Seed = Integer(options, "seed", 20261119)
        });
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out string? path))
        {
            EnsureNewFile(path);
            File.WriteAllText(path, json + Environment.NewLine);
            Console.WriteLine($"Read-only market-clock phase report saved to {path}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine(
            $"Clock source groups={report.SourceGroups}; " +
            $"controlled={report.EligibleSourceGroups}; " +
            "common timestamp rhythm is not an individual bot identity");
        return input.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static int FlowFootprintCommand(Dictionary<string, string> options)
    {
        var input = CsvTradeReader.Read(Required(options, "input"),
            Integer(options, "max-rows", 1_000_000));
        var report = FlowFootprint.Describe(input, new FlowFootprintConfig
        {
            WindowMinutes = Integer(options, "window-minutes", 5),
            CountBinSeconds = Integer(options, "bin-seconds", 1),
            ClockPhaseThresholdMilliseconds = Integer(options, "clock-phase-ms", 100)
        });
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out var output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Descriptive trade-flow footprints saved to {output}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine(
            $"Public prints={report.InputPrints}; windows={report.WindowCount}; physical_bot_count=UNKNOWN");
        return input.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static VariableCadenceConfig VariableCadenceOptions(Dictionary<string, string> options) => new()
    {
        MinMatches = Integer(options, "min-matches", 8),
        MinDistinctQuantities = Integer(options, "min-distinct-sizes", 3),
        AnalysisWindowMinutes = Integer(options, "window-minutes", 60),
        MaxEventsPerWindow = Integer(options, "max-window-events", 2500)
    };

    private static int VariableCadenceCommand(Dictionary<string, string> options)
    {
        var imported = CsvTradeReader.Read(Required(options, "input"));
        var config = VariableCadenceOptions(options);
        var result = VariableSizeCadence.Detect(imported, config);
        string json = JsonSerializer.Serialize(result, JsonOptions);
        if (options.TryGetValue("output", out var output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Unvalidated variable-clip cadence report saved to {output}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine($"Variable-size candidates={result.CandidateSequenceCount}; " +
            $"split dense windows={result.SplitDenseWindowCount}; " +
            $"tiny trailing chunks={result.SkippedTinyRemainderCount}; actual bot count UNKNOWN");
        return imported.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static int VariableTemporalNullCommand(Dictionary<string, string> options)
    {
        var imported = CsvTradeReader.Read(Required(options, "input"));
        var config = VariableCadenceOptions(options);
        var result = TemporalCadenceNull.Compare(imported, config,
            mode: options.GetValueOrDefault("mode", "uniform"),
            trials: Integer(options, "trials", 6),
            seed: Integer(options, "seed", 1701),
            blockSeconds: Integer(options, "block-seconds", 60));
        string json = JsonSerializer.Serialize(result, JsonOptions);
        if (options.TryGetValue("output", out var output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Experimental temporal-null report saved to {output}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine("WARNING: this null is not calibrated; do not infer independent robots or trading signals.");
        return imported.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static int DiagnoseForecastCommand(Dictionary<string, string> options)
    {
        var source = CsvTradeReader.Read(Required(options, "input"));
        var config = new DetectorConfig
        {
            MinMatches = Integer(options, "min-matches", 6),
            AnalysisWindowMinutes = Integer(options, "window-minutes", 60),
            MaximumEventsPerGroup = Integer(options, "max-group-events", 5000)
        };
        int warmup = Integer(options, "warmup-minutes", 60);
        int stride = Integer(options, "stride-minutes", 30);
        int maxCutoffs = Integer(options, "max-cutoffs", 12);
        var rolling = RollingForecast.Evaluate(source, config, warmup, stride, maxCutoffs,
            maximumTrainingAgeCycles: options.TryGetValue("max-training-age-cycles", out var diagnosticAge)
                ? int.Parse(diagnosticAge, CultureInfo.InvariantCulture) : null);
        var report = ForecastFailureDiagnostics.Analyse(source, rolling, config);
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out string? output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Post-hoc forecast diagnostic report saved to {output}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine(
            $"Forecasts={report.ForecastsEvaluated}; misses={report.Misses}; " +
            $"staleHistoryMisses={report.MissesWithStaleTrainingPattern}; " +
            "descriptive-only; no confirmed bot count");
        return source.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static int RollingForecastCommand(Dictionary<string, string> options)
    {
        var source = CsvTradeReader.Read(Required(options, "input"));
        var config = new DetectorConfig
        {
            MinMatches = Integer(options, "min-matches", 6),
            AnalysisWindowMinutes = Integer(options, "window-minutes", 60),
            MaximumEventsPerGroup = Integer(options, "max-group-events", 5000)
        };
        var report = RollingForecast.Evaluate(source, config,
            warmupMinutes: Integer(options, "warmup-minutes", 20),
            strideMinutes: Integer(options, "stride-minutes", 15),
            maximumCutoffsPerSession: Integer(options, "max-cutoffs", 24),
            maximumTrainingAgeCycles: options.TryGetValue("max-training-age-cycles", out var maxAge)
                ? int.Parse(maxAge, CultureInfo.InvariantCulture) : null);
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out string? output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Chronological forecast and placebo report saved to {output}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine(
            $"Future checks={report.ForecastsEvaluated}; observed hits={report.ObservedHits}; " +
            $"phase-shift placebo hits={report.PlaceboHits}; " +
            "uncalibrated and not proof of bot ownership");
        return source.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static int Fusion(Dictionary<string, string> options)
    {
        var imported = CsvTradeReader.Read(Required(options, "input"));
        var config = new DetectorConfig
        {
            MinMatches = Integer(options, "min-matches", 6),
            AnalysisWindowMinutes = Integer(options, "window-minutes", 60),
            MaximumEventsPerGroup = Integer(options, "max-group-events", 5000)
        };
        var candidates = PeriodicDetector.Detect(imported, config);
        var report = EpisodeFusion.Group(imported, candidates, config,
            maxGapCycles: Integer(options, "max-gap-cycles", 12));
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out string? output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Conservative episode grouping report saved to {output}");
        }
        else Console.WriteLine(json);

        Console.Error.WriteLine(
            $"Candidate episodes={report.CandidateEpisodeCount}; " +
            $"linked groups={report.ConservativelyLinkedGroupCount}; " +
            "physical_bot_count=UNKNOWN");
        return imported.RejectedRowTotal > 0 ? 3 : 0;
    }

    private static int NullShuffle(Dictionary<string, string> options)
    {
        string input = Required(options, "input");
        var imported = CsvTradeReader.Read(input);
        var config = new DetectorConfig
        {
            MinMatches = Integer(options, "min-matches", 6),
            AnalysisWindowMinutes = Integer(options, "window-minutes", 60),
            MaximumEventsPerGroup = Integer(options, "max-group-events", 5000)
        };
        var report = SizeShuffleNull.Compare(imported, config,
            trials: Integer(options, "trials", 10),
            seed: Integer(options, "seed", 42),
            localWindowSeconds: Integer(options, "block-seconds", 60),
            nullMode: options.GetValueOrDefault("mode", "permute"));
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out var output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Uncalibrated negative-control report saved to {output}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine("WARNING: local size-shuffle is exploratory; tail frequency does not validate any individual robot.");
        return 0;
    }

    private static int Spectrum(Dictionary<string, string> options)
    {
        var imported = CsvTradeReader.Read(Required(options, "input"));
        var report = SpectralCandidates.Analyse(imported,
            binMs: Integer(options, "bin-ms", 500),
            topPeaks: Integer(options, "top", 8));
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out string? output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Spectral candidate report saved to {output}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine("FFT peaks are hypotheses only, not bot IDs or calibrated probabilities.");
        return 0;
    }

    private static int Walkforward(Dictionary<string, string> options)
    {
        string input = Required(options, "input");
        string cutoff = Required(options, "cutoff");
        if (!(cutoff.EndsWith("Z", StringComparison.OrdinalIgnoreCase) ||
              (cutoff.Length > 10 && cutoff[10..].Contains('+')) ||
              (cutoff.Length > 10 && cutoff[10..].Contains('-'))))
            throw new ArgumentException("Use --cutoff with explicit UTC offset or Z.");
        var time = DateTimeOffset.Parse(cutoff, CultureInfo.InvariantCulture,
            DateTimeStyles.AdjustToUniversal);
        var imported = CsvTradeReader.Read(input);
        var result = WalkForward.Evaluate(imported, time, new DetectorConfig
        {
            MinMatches = Integer(options, "min-matches", 4)
        });
        string json = JsonSerializer.Serialize(result, JsonOptions);
        if (options.TryGetValue("output", out string? output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Walk-forward report saved to {output}");
        }
        else Console.WriteLine(json);
        return 0;
    }

    private static int Benchmark(Dictionary<string, string> options)
    {
        int seeds = Integer(options, "seeds", 20);
        int noise = Integer(options, "noise-trades", 200);
        var report = SyntheticBenchmark.Run(seeds, new DetectorConfig(), noise);
        string json = JsonSerializer.Serialize(report, JsonOptions);
        if (options.TryGetValue("output", out var output))
        {
            EnsureNewFile(output);
            File.WriteAllText(output, json + Environment.NewLine);
            Console.WriteLine($"Synthetic benchmark saved to {output}");
        }
        else Console.WriteLine(json);
        Console.Error.WriteLine("WARNING: simulator metrics are not calibrated estimates for MOEX/SPB.");
        return 0;
    }

    private static int Quote(Dictionary<string, string> options)
    {
        string path = Required(options, "input");
        var lines = File.ReadAllLines(path);
        if (lines.Length < 3) throw new InvalidDataException("Expected CSV header and two quote observations.");
        var headers = lines[0].Split(',').Select(x => x.Trim()).ToArray();
        int Index(string name) => Array.FindIndex(headers, x => x.Equals(name, StringComparison.OrdinalIgnoreCase)) is var i && i >= 0
            ? i : throw new InvalidDataException("Missing column: " + name);
        int timeIdx = Index("exchange_time_utc");
        int uidIdx = Index("instrument_uid");
        int bidIdx = Index("bid_price");
        int askIdx = Index("ask_price");
        int bidLotsIdx = Index("bid_quantity_lots");
        int askLotsIdx = Index("ask_quantity_lots");
        int tickIdx = Index("tick_size");

        var observations = new List<BestQuote>();
        foreach (string line in lines.Skip(1).Where(x => !string.IsNullOrWhiteSpace(x)))
        {
            var v = line.Split(',');
            observations.Add(new BestQuote(
                DateTimeOffset.Parse(v[timeIdx], CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal),
                v[uidIdx],
                decimal.Parse(v[bidIdx], CultureInfo.InvariantCulture),
                decimal.Parse(v[askIdx], CultureInfo.InvariantCulture),
                decimal.Parse(v[tickIdx], CultureInfo.InvariantCulture),
                long.Parse(v[bidLotsIdx], CultureInfo.InvariantCulture),
                long.Parse(v[askLotsIdx], CultureInfo.InvariantCulture)
            ));
        }
        // A CSV on disk does not by itself prove continuous exchange quote coverage.
        var result = QuoteOscillation.Calculate(observations, coverageVerified: false);
        Console.WriteLine(JsonSerializer.Serialize(result, JsonOptions));
        return 0;
    }

    private static Dictionary<string, string> ParseOptions(string[] tokens)
    {
        var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < tokens.Length; i += 2)
        {
            if (!tokens[i].StartsWith("--", StringComparison.Ordinal) || i + 1 >= tokens.Length)
                throw new ArgumentException("Options must use --name value.");
            var key = tokens[i][2..];
            if (!result.TryAdd(key, tokens[i + 1]))
                throw new ArgumentException("Duplicate option: " + key);
        }
        return result;
    }
    private static string Required(Dictionary<string, string> args, string name) =>
        args.TryGetValue(name, out string? value) && !string.IsNullOrWhiteSpace(value)
            ? value : throw new ArgumentException("Missing --" + name);

    private static int Integer(Dictionary<string, string> args, string key, int fallback) =>
        args.TryGetValue(key, out var value)
            ? int.Parse(value, CultureInfo.InvariantCulture) : fallback;

    private static double Double(Dictionary<string, string> args, string key, double fallback) =>
        args.TryGetValue(key, out var value)
            ? double.Parse(value, CultureInfo.InvariantCulture) : fallback;

    private static void EnsureNewFile(string path)
    {
        if (File.Exists(path)) throw new IOException("Refusing to overwrite existing file: " + path);
        string? directory = Path.GetDirectoryName(Path.GetFullPath(path));
        if (directory is not null) Directory.CreateDirectory(directory);
    }

    private static void PrintHelp()
    {
        Console.WriteLine("Robot Detector 0.1 — research-only market trade pattern screener");
        Console.WriteLine("detect --input file.csv|zip [--output report.json] [--rejects errors.json] [--min-matches 6]");
        Console.WriteLine("       [--min-period-ms 200] [--max-period-ms 600000] [--min-coverage 0.55]");
        Console.WriteLine("       [--window-minutes 60] [--max-group-events 5000]");
        Console.WriteLine("fetch --date YYYY-MM-DD --instrument-id SBER_TQBR --output data/raw/file.csv|zip");
        Console.WriteLine("quote --input fixtures/synthetic_quote_oscillation.csv");
        Console.WriteLine("benchmark [--seeds 20] [--noise-trades 200] [--output synthetic_report.json]");
        Console.WriteLine("walkforward --input file.csv --cutoff YYYY-MM-DDTHH:MM:SSZ [--min-matches 4]");
        Console.WriteLine("spectrum --input file.csv [--bin-ms 500] [--top 8] [--output spectrum.json]");
        Console.WriteLine("null-shuffle --input file.csv [--trials 10] [--seed 42] [--block-seconds 60] [--mode permute|rotate]");
        Console.WriteLine("fusion --input file.csv [--max-gap-cycles 12] [--output grouped.json]");
        Console.WriteLine("rolling-forecast --input file.csv [--warmup-minutes 20] [--stride-minutes 15] [--max-cutoffs 24] [--max-training-age-cycles 2]");
        Console.WriteLine("diagnose-forecast --input file.csv [--min-matches 6] [--warmup-minutes 60] [--stride-minutes 30] [--max-cutoffs 12] [--max-training-age-cycles 2]");
        Console.WriteLine("variable-cadence --input file.csv [--min-matches 8] [--min-distinct-sizes 3] [--output candidates.json]");
        Console.WriteLine("variable-temporal-null --input file.csv [--mode uniform|rotate] [--trials 6] [--block-seconds 60]");
        Console.WriteLine("flow-footprint --input file.csv [--window-minutes 5] [--bin-seconds 1] [--output footprints.json]");
        Console.WriteLine("activity-episodes --input file.csv [--reference-windows 4] [--min-count-ratio 3] [--min-lot-ratio 3] [--min-abs-imbalance 0.6]");
        Console.WriteLine("clock-phase-audit --input file.csv [--first-ms 100] [--min-prints 100] [--trials 99] [--seed 20261119] [--output clock.json]");
        Console.WriteLine("timestamp-quality --input file.csv [--output timestamp-quality.json]");
        Console.WriteLine("cluster-compare --input file.csv [--min-matches 6] [--output clusters.json]");
        Console.WriteLine("dashboard --input file.csv|zip --html report.html [--json report.json] [--window-minutes 5] [--max-visible-windows 240]");
        Console.WriteLine("replay-audit --input file.csv|zip [--lateness-ms 500] [--max-pending 10000] [--window-minutes 5] [--receipt-order archive_row|exchange_time_ideal] [--output replay.json]");
        Console.WriteLine("compare-archives --inputs \"a.csv;b.csv\" --html comparison.html [--json comparison.json] [--window-minutes 5]");
        Console.WriteLine("benchmark-blind [--seeds 5] [--background-prints 120] [--output blind-benchmark.json]");
        Console.WriteLine("benchmark-clock-null [--trials 20] [--background-prints 120] [--cycles 12] [--period-ms 5000] [--clip-mode fixed|variable] [--output clock-null.json]");
        Console.WriteLine("benchmark-abides-blind --public abides.csv --truth private.json [--output report.json]");
        Console.WriteLine("No order placement, account access, owner identification or calibrated confidence.");
    }
}
