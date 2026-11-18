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
            MaximumEventsPerGroup = Integer(options, "max-group-events", 5000)
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

        Console.Error.WriteLine($"Trades={report.SourceTradeCount}; rejected_sample={report.RejectedRowCount};" +
                                $" candidates={report.CandidatePatternCount}; physical_bot_count=UNKNOWN");
        return imported.RejectedRows.Count > 0 ? 3 : 0;
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
        Console.WriteLine("fetch --date YYYY-MM-DD --instrument-id SBER_TQBR --output data/raw/file.csv|zip");
        Console.WriteLine("quote --input fixtures/synthetic_quote_oscillation.csv");
        Console.WriteLine("benchmark [--seeds 20] [--noise-trades 200] [--output synthetic_report.json]");
        Console.WriteLine("walkforward --input file.csv --cutoff YYYY-MM-DDTHH:MM:SSZ [--min-matches 4]");
        Console.WriteLine("spectrum --input file.csv [--bin-ms 500] [--top 8] [--output spectrum.json]");
        Console.WriteLine("No order placement, account access, owner identification or calibrated confidence.");
    }
}
