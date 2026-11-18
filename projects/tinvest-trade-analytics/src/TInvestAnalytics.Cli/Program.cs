using System.Globalization;
using System.Text.Json;

namespace TInvestAnalytics;

public static class Program
{
    public static async Task<int> Main(string[] args)
    {
        try
        {
            if (args.Length == 0 || args[0] is "help" or "--help" or "-h")
            {
                Help();
                return 0;
            }
            string db = Arg(args, "--db") ?? Environment.GetEnvironmentVariable("TIA_DB") ??
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "TInvestAnalytics", "analytics.db");
            var store = new EvidenceStore(db);
            store.Initialize();
            string command = args[0].ToLowerInvariant();
            switch (command)
            {
                case "doctor":
                    var s = store.Stats();
                    Console.WriteLine(JsonSerializer.Serialize(new
                    {
                        app = "TInvestAnalytics", mode = "read-only",
                        db_file = Path.GetFileName(db),
                        token_configured = !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("TINVEST_TOKEN")),
                        pages = s.Pages, revisions = s.Revisions, current_operations = s.CurrentOperations,
                        complete_windows = s.CompleteWindows,
                        warning = "No portfolio valuation or independent reconciliation yet."
                    }, JsonOptions()));
                    break;
                case "accounts":
                    using (var client = Client(args))
                    {
                        var accounts = TInvestClient.ParseAccounts(await client.GetAccountsAsync());
                        foreach (var (a, idx) in accounts.Select((a, i) => (a, i)))
                            Console.WriteLine($"[{idx}] {PnlCalculator.Mask(a.Id)} {a.Name} {a.Type} {a.Status}");
                        Console.WriteLine("For sync use --account-index 0 (or explicit --account ID).");
                    }
                    break;
                case "sync":
                    await Sync(args, store);
                    break;
                case "import-json":
                    ImportJson(args, store);
                    break;
                case "report":
                    Report(args, store);
                    break;
                case "daily-report":
                    DailyReport(args, store);
                    break;
                case "snapshot":
                    await CaptureSnapshot(args, store);
                    break;
                case "snapshots":
                    ShowSnapshots(args, store);
                    break;
                case "equity-pnl":
                    EquityPnl(args, store);
                    break;
                case "stats":
                    var st = store.Stats();
                    Console.WriteLine($"Raw pages: {st.Pages}, revisions: {st.Revisions}, " +
                        $"current operations: {st.CurrentOperations}, complete windows: {st.CompleteWindows}");
                    break;
                default:
                    throw new ArgumentException("Unknown command: " + command);
            }
            return 0;
        }
        catch (Exception ex)
        {
            // Never echo credentials, full REST response, raw operation JSON or a stack trace.
            Console.Error.WriteLine(ex.GetType().Name + ": " + SafeMessage(ex.Message));
            return 1;
        }
    }

    private static TInvestClient Client(string[] args)
    {
        var token = Environment.GetEnvironmentVariable("TINVEST_TOKEN");
        if (string.IsNullOrWhiteSpace(token))
            throw new InvalidOperationException("Set TINVEST_TOKEN as a read-only API token first.");
        return new TInvestClient(token, Flag(args, "--sandbox"));
    }
    private static string SafeMessage(string input)
    {
        // No API bodies in any exceptions thrown by this code. Extra safeguard for environment token.
        var token = Environment.GetEnvironmentVariable("TINVEST_TOKEN");
        if (!string.IsNullOrEmpty(token)) input = input.Replace(token, "[REDACTED]", StringComparison.Ordinal);
        return input.Length > 250 ? input[..250] + "…" : input;
    }
    private static string? Arg(string[] a, string name)
    {
        for (int i = 0; i < a.Length; i++)
        {
            if (a[i].StartsWith(name + "=", StringComparison.Ordinal))
                return a[i][(name.Length + 1)..];
            if (a[i] == name)
                return i + 1 < a.Length && !a[i + 1].StartsWith("--", StringComparison.Ordinal)
                    ? a[i + 1] : throw new ArgumentException("Value required: " + name);
        }
        return null;
    }
    private static string Require(string[] a, string name) =>
        Arg(a, name) ?? throw new ArgumentException("Missing required option: " + name);
    private static bool Flag(string[] a, string name) => a.Contains(name, StringComparer.Ordinal);
    private static DateTimeOffset Time(string value) => DateTimeOffset.Parse(
        value, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal);

    private static (DateTimeOffset From, DateTimeOffset To) Period(string[] args)
    {
        var from = Time(Require(args, "--from"));
        var to = Time(Require(args, "--to"));
        if (from >= to) throw new ArgumentException("Expected --from earlier than --to.");
        return (from, to);
    }
    private static async Task Sync(string[] args, EvidenceStore store)
    {
        var (from, to) = Period(args);
        using var client = Client(args);
        string? accountId = Arg(args, "--account");
        if (accountId is null)
        {
            int idx = int.Parse(Require(args, "--account-index"), CultureInfo.InvariantCulture);
            var accounts = TInvestClient.ParseAccounts(await client.GetAccountsAsync());
            if (idx < 0 || idx >= accounts.Count)
                throw new ArgumentOutOfRangeException(nameof(idx), "Account index is out of range.");
            accountId = accounts[idx].Id;
        }
        if (Flag(args, "--refresh")) store.RestartWindow(accountId, from, to);
        var checkpoint = store.GetCheckpoint(accountId, from, to);
        if (checkpoint.Complete)
        {
            Console.WriteLine("Window previously completed. Use --refresh to compare revisions.");
            return;
        }
        string? cursor = checkpoint.Cursor;
        int pagesThisRun = 0;
        while (pagesThisRun < 100000)
        {
            string json = await client.GetOperationsPageAsync(accountId, from, to, cursor);
            var next = TInvestClient.ParsePageCursor(json);
            int inserted = store.ImportPage(accountId, from, to, cursor,
                next.NextCursor, next.HasNext, json);
            pagesThisRun++;
            Console.WriteLine($"Page {checkpoint.Pages + pagesThisRun}: " +
                $"{inserted} operations; {(next.HasNext ? "more" : "complete")}.");
            if (!next.HasNext)
            {
                Console.WriteLine("Raw history window complete. Financial verification NOT YET performed.");
                return;
            }
            if (cursor == next.NextCursor || string.IsNullOrWhiteSpace(next.NextCursor))
                throw new InvalidDataException("Cursor failed to advance; window left incomplete.");
            cursor = next.NextCursor;
        }
        throw new InvalidDataException("Excessive pagination; window remains incomplete.");
    }

    private static async Task CaptureSnapshot(string[] args, EvidenceStore store)
    {
        using var client = Client(args);
        string? account = Arg(args, "--account");
        if (account is null)
        {
            int idx = int.Parse(Require(args, "--account-index"), CultureInfo.InvariantCulture);
            var accounts = TInvestClient.ParseAccounts(await client.GetAccountsAsync());
            if (idx < 0 || idx >= accounts.Count)
                throw new ArgumentOutOfRangeException(nameof(idx), "Account index out of range.");
            account = accounts[idx].Id;
        }
        string portfolio = await client.GetPortfolioAsync(account);
        string positions = await client.GetPositionsAsync(account);
        var observed = DateTimeOffset.UtcNow;
        var snapshot = store.SavePortfolio(account, observed, portfolio, positions);
        Console.WriteLine($"Snapshot #{snapshot.Id} of {PnlCalculator.Mask(account)}: " +
            $"equity={snapshot.Equity}, observed={observed:O}. Quality: provisional.");
    }
    private static void ShowSnapshots(string[] args, EvidenceStore store)
    {
        var account = Require(args, "--account");
        foreach (var x in store.GetSnapshots(account))
            Console.WriteLine($"#{x.Id} {x.ObservedAtUtc:O} {x.Equity} hash={x.PortfolioSha256[..12]}");
    }
    private static void EquityPnl(string[] args, EvidenceStore store)
    {
        var account = Require(args, "--account");
        var snapshots = store.GetSnapshots(account);
        long firstId = long.Parse(Require(args, "--start-id"), CultureInfo.InvariantCulture);
        long lastId = long.Parse(Require(args, "--end-id"), CultureInfo.InvariantCulture);
        var first = snapshots.Single(x => x.Id == firstId);
        var last = snapshots.Single(x => x.Id == lastId);
        bool covered = store.HasCompleteOperationsWindow(account, first.ObservedAtUtc, last.ObservedAtUtc);
        var ops = store.LoadOperations(account, first.ObservedAtUtc, last.ObservedAtUtc);
        var report = PortfolioMath.Calculate(first, last, ops, covered);
        Console.WriteLine(JsonSerializer.Serialize(report, JsonOptions()));
    }
    private static void ImportJson(string[] args, EvidenceStore store)
    {
        var (from, to) = Period(args);
        var account = Require(args, "--account");
        var file = Require(args, "--file");
        string json = File.ReadAllText(file);
        var next = TInvestClient.ParsePageCursor(json);
        if (next.HasNext)
            throw new InvalidDataException("Offline import only supports a complete one-page response; " +
                "multi-page histories require live cursor synchronization.");
        int n = store.ImportPage(account, from, to, null, null, false, json);
        Console.WriteLine($"Imported {n} raw observations. No broker authenticity verification.");
    }

    private static void DailyReport(string[] args, EvidenceStore store)
    {
        var (from, to) = Period(args);
        var account = Require(args, "--account");
        var classes = new Dictionary<string, string>(StringComparer.Ordinal);
        var classFile = Arg(args, "--asset-map");
        if (classFile is not null)
            foreach (var (uid, value) in JsonSerializer.Deserialize<Dictionary<string, string>>(
                File.ReadAllText(classFile)) ?? new Dictionary<string, string>())
                classes[uid] = value.ToLowerInvariant();
        var excluded = new HashSet<DateOnly>();
        var rawExclusion = Arg(args, "--exclude-days");
        if (rawExclusion is not null)
            foreach (var day in rawExclusion.Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries))
                excluded.Add(DateOnly.ParseExact(day, "yyyy-MM-dd", CultureInfo.InvariantCulture));
        var ops = store.LoadOperations(account, DateTimeOffset.MinValue, to);
        var report = DailyReporting.Calculate(account, ops, classes, from, to, excluded);
        Console.WriteLine(JsonSerializer.Serialize(report, JsonOptions()));
    }

    private static void Report(string[] args, EvidenceStore store)
    {
        var (from, to) = Period(args);
        var account = Require(args, "--account");
        IReadOnlyDictionary<string, string> classMap = new Dictionary<string, string>();
        var mapFile = Arg(args, "--asset-map");
        if (mapFile is not null)
        {
            var map = JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(mapFile)) ??
                throw new FormatException("Empty asset type map.");
            classMap = map.ToDictionary(x => x.Key, x => x.Value.ToLowerInvariant(), StringComparer.Ordinal);
        }
        // FIFO needs inventory established before the selected period; load all available history.
        var operations = store.LoadOperations(account, DateTimeOffset.MinValue, to);
        var output = PnlCalculator.Calculate(account, operations, classMap, from, to);
        Console.WriteLine(JsonSerializer.Serialize(output, JsonOptions()));
    }
    private static JsonSerializerOptions JsonOptions() => new()
    {
        WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    private static void Help()
    {
        Console.WriteLine("""
            TInvestAnalytics v0.1 — read-only prototype, not tax/accounting advice
            Commands:
              doctor [--db PATH]
              accounts [--sandbox]
              sync --account-index 0 --from 2026-11-01 --to 2026-11-18 [--db PATH] [--sandbox]
              sync --account ID --from ... --to ... [--db PATH] [--refresh]
              import-json --account TEST --file sample.json --from ... --to ...
              report --account ID --from ... --to ... [--asset-map class-map.json] [--db PATH]
              daily-report --account ID --from ... --to ... [--exclude-days 2026-11-14] [--asset-map class-map.json]
              snapshot --account-index 0 [--db PATH] [--sandbox]
              snapshots --account ID [--db PATH]
              equity-pnl --account ID --start-id N --end-id N [--db PATH]
              stats [--db PATH]

            Authentication: set TINVEST_TOKEN as a read-only token in the process environment.
            A report is PARTIAL; futures current mark and broker reconciliation not implemented.
            Never store token, account statements or private databases in Git.
            """);
    }
}
