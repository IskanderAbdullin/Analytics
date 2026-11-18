using System.Globalization;
using System.Text.Json;

namespace TInvestAnalytics;

public sealed record BotEvent(
    string EventId, string Kind, DateTimeOffset ObservedUtc,
    string BotId, string BotVersion, string RunId, string AccountRef,
    string InstrumentUid, string? ClientOrderId, string? BrokerOrderId,
    string? Side, decimal? Quantity, decimal? LimitPrice, decimal? FillPrice,
    string? DecisionId, string? ConfigHash, string RawJson, string PayloadHash);

public static class BotEventParser
{
    private static readonly HashSet<string> Kinds = new(StringComparer.Ordinal)
    {
        "run_start","run_stop","heartbeat","market_observation","strategy_decision",
        "order_submit","order_ack","order_modify_requested","order_cancel_requested",
        "order_cancel_ack","partial_fill","full_fill","order_reject","order_expired",
        "position_update","risk_limit","error"
    };
    private static string Required(JsonElement node, string field)
    {
        var value = JsonValue.Text(node, field);
        if (string.IsNullOrWhiteSpace(value))
            throw new FormatException("Bot event missing required field: " + field);
        return value;
    }
    private static decimal? OptionalDecimal(JsonElement node, string field)
    {
        var value = JsonValue.Text(node, field);
        return value is null ? null : decimal.Parse(value, NumberStyles.Float,
            CultureInfo.InvariantCulture);
    }
    public static BotEvent Parse(string raw)
    {
        using var doc = JsonDocument.Parse(raw);
        var n = doc.RootElement;
        if (Required(n, "schema") != "bot-event/v1")
            throw new FormatException("Unsupported bot-event schema version.");
        string kind = Required(n, "kind");
        if (!Kinds.Contains(kind)) throw new FormatException("Unknown bot event kind: " + kind);
        var id = Required(n, "event_id");
        var at = JsonValue.Date(n, "observed_utc") ??
            throw new FormatException("Missing observed_utc in bot event.");
        string bot = Required(n, "bot_id");
        string version = Required(n, "bot_version");
        string run = Required(n, "run_id");
        string account = Required(n, "account_ref");
        string uid = Required(n, "instrument_uid");
        var clientOrder = JsonValue.Text(n, "client_order_id");
        var brokerOrder = JsonValue.Text(n, "broker_order_id");
        var side = JsonValue.Text(n, "side");
        decimal? qty = OptionalDecimal(n, "qty_units");
        decimal? limit = OptionalDecimal(n, "limit_price");
        decimal? fill = OptionalDecimal(n, "fill_price");
        if (qty is <= 0) throw new FormatException("Bot event quantity must be positive.");
        if (kind == "order_submit" &&
            (string.IsNullOrWhiteSpace(clientOrder) || side is not ("BUY" or "SELL") ||
            qty is null || limit is null))
            throw new FormatException("order_submit must contain client order ID, side, qty and limit.");
        if (kind is "partial_fill" or "full_fill" &&
            (side is not ("BUY" or "SELL") || qty is null || fill is null))
            throw new FormatException("fill event must contain side, qty delta and execution price.");
        return new BotEvent(id,kind,at,bot,version,run,account,uid,clientOrder,brokerOrder,
            side,qty,limit,fill,JsonValue.Text(n,"decision_id"),JsonValue.Text(n,"config_hash"),
            raw, OperationParser.Hash(raw));
    }
    public static IReadOnlyList<BotEvent> ParseJsonLines(string lines)
    {
        var list = new List<BotEvent>();
        int i = 0;
        foreach (var line in lines.Split('\n'))
        {
            i++;
            if (string.IsNullOrWhiteSpace(line)) continue;
            try { list.Add(Parse(line.Trim())); }
            catch (Exception ex) when (ex is JsonException or FormatException or OverflowException)
            { throw new FormatException("Invalid bot JSONL at line " + i + ": " + ex.Message, ex); }
        }
        return list;
    }
}

public sealed record BotPerformanceSummary(
    string BotId, DateTimeOffset FromUtc, DateTimeOffset ToUtc,
    int UniqueRuns, int SubmittedOrders, int CancelRequests, int PartialFillEvents,
    int FullFillEvents, int Rejects, int StrategyDecisions, int Errors,
    decimal ReportedRequestedUnits, decimal ReportedFillDeltaUnits,
    int RapidCancelRepostCandidates, string Quality, IReadOnlyList<string> Warnings);

public static class BotTelemetryAnalysis
{
    public static BotPerformanceSummary Analyze(string bot,
        IReadOnlyList<BotEvent> input, DateTimeOffset from, DateTimeOffset to)
    {
        var events = input.Where(x => x.BotId == bot && x.ObservedUtc >= from && x.ObservedUtc < to)
            .OrderBy(x => x.ObservedUtc).ThenBy(x => x.EventId, StringComparer.Ordinal).ToList();
        int Count(string kind) => events.Count(x => x.Kind == kind);
        int quickReposts = 0;
        foreach (var run in events.GroupBy(x => x.RunId))
        {
            BotEvent? lastCancel = null;
            foreach (var e in run)
            {
                if (e.Kind == "order_cancel_requested") lastCancel = e;
                else if (e.Kind == "order_submit" && lastCancel is not null &&
                         e.InstrumentUid == lastCancel.InstrumentUid &&
                         e.ObservedUtc - lastCancel.ObservedUtc <= TimeSpan.FromSeconds(2))
                {
                    quickReposts++;
                    lastCancel = null;
                }
            }
        }
        var warnings = new List<string>
        {
            "Robot telemetry has not been linked to broker executions or reconciled with account P&L.",
            "qty_units on fill events is assumed incremental; cumulative fill reports would overcount.",
            "Rapid cancel/repost is heuristic, not proof of a strategy defect.",
            "No execution quality estimate without contemporaneous quotes and time synchronization."
        };
        var requested = events.Where(x => x.Kind == "order_submit").Sum(x => x.Quantity ?? 0);
        var fills = events.Where(x => x.Kind is "partial_fill" or "full_fill").Sum(x => x.Quantity ?? 0);
        return new BotPerformanceSummary(bot,from,to,events.Select(x => x.RunId).Distinct().Count(),
            Count("order_submit"),Count("order_cancel_requested"),Count("partial_fill"),
            Count("full_fill"),Count("order_reject"),Count("strategy_decision"),Count("error"),
            requested,fills,quickReposts,"unreconciled",warnings);
    }
}

public sealed partial class EvidenceStore
{
    public void InitializeBotTelemetry()
    {
        using var c = Open();
        using var q = Command(c, null, """
            CREATE TABLE IF NOT EXISTS bot_events (
                event_id TEXT PRIMARY KEY,
                bot_id TEXT NOT NULL,
                bot_version TEXT NOT NULL,
                run_id TEXT NOT NULL,
                instrument_uid TEXT NOT NULL,
                observed_utc TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                raw_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_bot_events_bot_time
                ON bot_events(bot_id, observed_utc);
            CREATE INDEX IF NOT EXISTS ix_bot_events_run
                ON bot_events(run_id, observed_utc);
            """);
        q.ExecuteNonQuery();
    }
    public int ImportBotEvents(IReadOnlyList<BotEvent> events)
    {
        using var c = Open();
        using var tx = c.BeginTransaction();
        int inserted = 0;
        foreach (var ev in events)
        {
            using var check = Command(c, tx,
                "SELECT payload_sha256 FROM bot_events WHERE event_id=$id",
                ("$id", ev.EventId));
            var existing = check.ExecuteScalar() as string;
            if (existing is not null)
            {
                if (existing != ev.PayloadHash)
                    throw new InvalidDataException("Conflicting bot event ID (preserved original): " + ev.EventId);
                continue;
            }
            using var insert = Command(c, tx, """
                INSERT INTO bot_events
                (event_id,bot_id,bot_version,run_id,instrument_uid,observed_utc,kind,payload_sha256,raw_json)
                VALUES($id,$bot,$ver,$run,$uid,$time,$kind,$sha,$raw)
                """, ("$id", ev.EventId), ("$bot", ev.BotId), ("$ver", ev.BotVersion),
                ("$run", ev.RunId), ("$uid", ev.InstrumentUid),
                ("$time", ev.ObservedUtc.ToUniversalTime().ToString("O")),
                ("$kind", ev.Kind), ("$sha", ev.PayloadHash), ("$raw", ev.RawJson));
            inserted += insert.ExecuteNonQuery();
        }
        tx.Commit();
        return inserted;
    }
    public IReadOnlyList<BotEvent> LoadBotEvents(string bot, DateTimeOffset from, DateTimeOffset to)
    {
        using var c = Open();
        using var q = Command(c, null, """
            SELECT raw_json FROM bot_events
            WHERE bot_id=$bot AND observed_utc>=$f AND observed_utc<$t ORDER BY observed_utc,event_id
            """, ("$bot", bot), ("$f", from.ToUniversalTime().ToString("O")),
            ("$t", to.ToUniversalTime().ToString("O")));
        using var reader = q.ExecuteReader();
        var events = new List<BotEvent>();
        while (reader.Read()) events.Add(BotEventParser.Parse(reader.GetString(0)));
        return events;
    }
}
