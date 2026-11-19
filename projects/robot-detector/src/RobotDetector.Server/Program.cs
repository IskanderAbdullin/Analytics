using System.Globalization;
using System.Net;
using System.Text.Json;
using RobotDetector.Core;

namespace RobotDetector.Server;

/// <summary>
/// Local-only snapshot service. No account methods, API tokens, trading
/// endpoints, external assets or live broker subscriptions.
/// </summary>
internal static class Program
{
    private static readonly HashSet<string> AllowedOptions = new(StringComparer.OrdinalIgnoreCase)
    {
        "input", "port", "window-minutes", "max-rows", "max-visible-windows"
    };

    public static async Task<int> Main(string[] args)
    {
        if (args.Length == 0 || args is ["--help"] or ["-h"] or ["help"])
        {
            Console.WriteLine("Robot Detector localhost read-only snapshot server (.NET 10)");
            Console.WriteLine("Usage: dotnet run --project src/RobotDetector.Server -- --input file.csv|zip [--port 8765] [--window-minutes 5]");
            Console.WriteLine("Routes: GET /, GET /api/v1/health, GET /api/v1/summary. Always binds 127.0.0.1.");
            Console.WriteLine("No stream connection, trading API, scripts, account information or external network requests.");
            return 0;
        }

        Dictionary<string, string> settings;
        ResearchDashboardReport report;
        string html;
        string json;
        int port;
        try
        {
            settings = ReadOptions(args);
            string input = Required(settings, "input");
            port = Number(settings, "port", 8765);
            if (port is < 1024 or > 65535)
                throw new ArgumentException("Local port must be between 1024 and 65535.");

            int maxRows = Number(settings, "max-rows", 1_000_000);
            int windowMinutes = Number(settings, "window-minutes", 5);
            int maximumVisible = Number(settings, "max-visible-windows", 240);
            var tape = CsvTradeReader.Read(input, maxRows);
            report = ResearchDashboard.Build(tape, windowMinutes);
            html = ResearchDashboard.ToStandaloneHtml(report, maximumVisible);
            json = JsonSerializer.Serialize(report, new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase
            });
        }
        catch (Exception ex) when (ex is ArgumentException or IOException
            or FormatException or InvalidDataException)
        {
            Console.Error.WriteLine("ERROR: " + ex.Message);
            return 2;
        }

        var builder = WebApplication.CreateSlimBuilder(Array.Empty<string>());
        // No user-selectable network binding. Kestrel serves IPv4 loopback ONLY.
        builder.WebHost.ConfigureKestrel(o => o.Listen(IPAddress.Loopback, port));
        builder.Logging.ClearProviders();
        await using var app = builder.Build();

        app.Use(async (context, next) =>
        {
            IPAddress? remote = context.Connection.RemoteIpAddress;
            if (remote is null || !IPAddress.IsLoopback(remote))
            {
                context.Response.StatusCode = StatusCodes.Status403Forbidden;
                return;
            }
            // Reject DNS-rebinding via an attacker-controlled Host header.
            // The server intentionally exposes one fixed literal IPv4 address.
            if (!string.Equals(context.Request.Host.Host, "127.0.0.1",
                    StringComparison.Ordinal))
            {
                context.Response.StatusCode = StatusCodes.Status403Forbidden;
                return;
            }
            // Reject browser requests with a nonlocal Origin even for safe GET.
            // No CORS permission is granted to external websites.
            if (context.Request.Headers.TryGetValue("Origin", out var origins) &&
                origins.Any(origin => !string.Equals(origin,
                    $"http://127.0.0.1:{port}", StringComparison.Ordinal)))
            {
                context.Response.StatusCode = StatusCodes.Status403Forbidden;
                return;
            }
            // Do not provide write endpoints, even as empty no-op handlers.
            if (!HttpMethods.IsGet(context.Request.Method) &&
                !HttpMethods.IsHead(context.Request.Method))
            {
                context.Response.StatusCode = StatusCodes.Status405MethodNotAllowed;
                return;
            }
            context.Response.Headers["Cache-Control"] = "no-store";
            context.Response.Headers["Pragma"] = "no-cache";
            context.Response.Headers["X-Content-Type-Options"] = "nosniff";
            context.Response.Headers["X-Frame-Options"] = "DENY";
            context.Response.Headers["Referrer-Policy"] = "no-referrer";
            context.Response.Headers["Content-Security-Policy"] =
                "default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; form-action 'none'; base-uri 'none'";
            await next(context);
        });

        app.MapGet("/", () => Results.Content(html, "text/html; charset=utf-8"));
        app.MapGet("/api/v1/health", () => Results.Json(new
        {
            status = "offline_snapshot",
            mode = "read_only",
            sourceSha256 = report.SourceSha256,
            publicPrints = report.PublicPrints,
            sourceCoverageVerified = report.FeedCoverageVerified,
            actualBotCountKnown = false,
            tradingEnabled = false,
            liveMarketDataConnected = false
        }));
        app.MapGet("/api/v1/summary", () =>
            Results.Content(json, "application/json; charset=utf-8"));
        app.MapFallback(() => Results.NotFound(new { error = "unknown_read_only_route" }));

        Console.WriteLine($"Robot Detector (local read-only snapshot): http://127.0.0.1:{port}/");
        Console.WriteLine($"Source prints={report.PublicPrints}, source SHA={report.SourceSha256}.");
        Console.WriteLine("No network exposure beyond loopback; stop with Ctrl+C.");
        await app.RunAsync();
        return 0;
    }

    private static Dictionary<string, string> ReadOptions(string[] args)
    {
        var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < args.Length; i += 2)
        {
            if (!args[i].StartsWith("--", StringComparison.Ordinal) || i + 1 >= args.Length)
                throw new ArgumentException("Expected --option value pairs.");
            string key = args[i][2..];
            if (!AllowedOptions.Contains(key))
                throw new ArgumentException("Unsupported server option: " + key);
            if (!result.TryAdd(key, args[i + 1]))
                throw new ArgumentException("Duplicate option: " + key);
        }
        return result;
    }

    private static string Required(Dictionary<string, string> options, string key) =>
        options.TryGetValue(key, out var value) && !string.IsNullOrWhiteSpace(value)
            ? value : throw new ArgumentException("Missing --" + key);

    private static int Number(Dictionary<string, string> options, string key, int fallback) =>
        options.TryGetValue(key, out var text)
            ? int.Parse(text, CultureInfo.InvariantCulture) : fallback;
}
