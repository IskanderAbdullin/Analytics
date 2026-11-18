using System.Globalization;
using System.Text.Json;

namespace TInvestAnalytics;

public sealed record BrokerReportTask(string TaskId, string AccountId,
    DateTimeOffset FromUtc, DateTimeOffset ToUtc, DateTimeOffset RequestedUtc);
public sealed record BrokerReportPage(int Page, int PagesCount, int ItemsCount,
    int ReturnedRows, string RawJson, string Sha256);

public sealed record BrokerReportSummary(
    string TaskId, string AccountRef, DateTimeOffset FromUtc, DateTimeOffset ToUtc,
    int PagesStored, int DeclaredItems, int ActualRows,
    IReadOnlyDictionary<string, decimal> ExplicitCommissionsByCurrency,
    string Status, IReadOnlyList<string> Warnings);

public static class BrokerReportParsing
{
    public static string ReadTaskId(string raw)
    {
        using var d = JsonDocument.Parse(raw);
        if (!d.RootElement.TryGetProperty("generateBrokerReportResponse", out var generated))
            throw new FormatException("GetBrokerReport did not return generateBrokerReportResponse.");
        return JsonValue.Text(generated, "taskId") ??
            throw new FormatException("Broker report request did not return a taskId.");
    }
    public static BrokerReportPage ReadPage(int expectedPage, string raw)
    {
        using var d = JsonDocument.Parse(raw);
        if (!d.RootElement.TryGetProperty("getBrokerReportResponse", out var result))
            throw new FormatException("GetBrokerReport returned no getBrokerReportResponse (possibly pending).");
        if (!result.TryGetProperty("brokerReport", out var rows) || rows.ValueKind != JsonValueKind.Array)
            throw new FormatException("Broker report has no brokerReport array.");
        int pages = (int)JsonValue.DecimalOr(result, "pagesCount", 0);
        int count = (int)JsonValue.DecimalOr(result, "itemsCount", 0);
        int responsePage = (int)JsonValue.DecimalOr(result, "page", expectedPage);
        // Different API revisions may use a 0- or 1-based page convention; don't silently
        // complete a task based on pagesCount alone.
        if (pages < 0 || count < 0) throw new FormatException("Invalid broker report paging metadata.");
        return new BrokerReportPage(responsePage, pages, count, rows.GetArrayLength(),
            raw, OperationParser.Hash(raw));
    }
    public static IReadOnlyList<(string Currency, decimal Fee)> ExtractCommissions(string pageJson)
    {
        using var d = JsonDocument.Parse(pageJson);
        var rows = d.RootElement.GetProperty("getBrokerReportResponse").GetProperty("brokerReport");
        var result = new List<(string, decimal)>();
        foreach (var row in rows.EnumerateArray())
            foreach (string field in new[] { "brokerCommission", "exchangeCommission", "exchangeClearingCommission" })
            {
                var value = JsonValue.Field(row, field);
                if (value is { ValueKind: JsonValueKind.Object })
                {
                    var money = Money.FromJson(value.Value);
                    // Broker report commissions may be positive costs while operation payments negative.
                    result.Add((money.Currency, Math.Abs(money.Amount)));
                }
            }
        return result;
    }
}

public sealed partial class EvidenceStore
{
    public void InitializeBrokerReports()
    {
        using var c = Open();
        using var q = Command(c, null, """
            CREATE TABLE IF NOT EXISTS broker_report_tasks (
                task_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                from_utc TEXT NOT NULL,
                to_utc TEXT NOT NULL,
                requested_utc TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS broker_report_pages (
                row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL REFERENCES broker_report_tasks(task_id),
                page_index INTEGER NOT NULL,
                payload_sha256 TEXT NOT NULL,
                declared_items INTEGER NOT NULL,
                declared_pages INTEGER NOT NULL,
                raw_json TEXT NOT NULL,
                stored_utc TEXT NOT NULL,
                UNIQUE(task_id,page_index,payload_sha256)
            );
            CREATE INDEX IF NOT EXISTS ix_broker_report_pages_task_page
                ON broker_report_pages(task_id,page_index);
            """);
        q.ExecuteNonQuery();
    }
    public void SaveBrokerReportTask(BrokerReportTask task)
    {
        using var c = Open();
        using var q = Command(c, null, """
            INSERT OR IGNORE INTO broker_report_tasks(task_id,account_id,from_utc,to_utc,requested_utc)
            VALUES($task,$acc,$from,$to,$at)
            """, ("$task", task.TaskId), ("$acc", task.AccountId),
            ("$from", task.FromUtc.ToUniversalTime().ToString("O")),
            ("$to", task.ToUtc.ToUniversalTime().ToString("O")),
            ("$at", task.RequestedUtc.ToUniversalTime().ToString("O")));
        q.ExecuteNonQuery();
    }
    public BrokerReportTask GetBrokerReportTask(string id)
    {
        using var c = Open();
        using var q = Command(c, null, """
            SELECT account_id,from_utc,to_utc,requested_utc
            FROM broker_report_tasks WHERE task_id=$task
            """, ("$task", id));
        using var rd = q.ExecuteReader();
        if (!rd.Read()) throw new KeyNotFoundException("Unknown broker report task ID.");
        DateTimeOffset Parse(int n) => DateTimeOffset.Parse(rd.GetString(n), CultureInfo.InvariantCulture);
        return new BrokerReportTask(id,rd.GetString(0),Parse(1),Parse(2),Parse(3));
    }
    public void SaveBrokerReportPage(string taskId, BrokerReportPage page)
    {
        using var c = Open();
        using var q = Command(c, null, """
            INSERT OR IGNORE INTO broker_report_pages
            (task_id,page_index,payload_sha256,declared_items,declared_pages,raw_json,stored_utc)
            VALUES($task,$page,$hash,$items,$pages,$raw,$now)
            """, ("$task", taskId), ("$page", page.Page), ("$hash", page.Sha256),
            ("$items", page.ItemsCount), ("$pages", page.PagesCount),
            ("$raw", page.RawJson), ("$now", DateTimeOffset.UtcNow.ToString("O")));
        q.ExecuteNonQuery();
    }
    public BrokerReportSummary BrokerReportSummary(string id)
    {
        var task = GetBrokerReportTask(id);
        using var c = Open();
        // One latest page revision for each page index, preserving all older raw page revisions.
        using var q = Command(c, null, """
            SELECT bp.raw_json,bp.declared_items,bp.declared_pages FROM broker_report_pages bp
            WHERE bp.task_id=$task AND bp.row_id=(
                SELECT MAX(x.row_id) FROM broker_report_pages x
                WHERE x.task_id=bp.task_id AND x.page_index=bp.page_index)
            ORDER BY bp.page_index
            """, ("$task", id));
        using var rd = q.ExecuteReader();
        var warnings = new List<string>();
        var totals = new Dictionary<string, decimal>(StringComparer.Ordinal);
        int pages = 0, count = 0, expected = 0, declaredPages = 0;
        while (rd.Read())
        {
            string json = rd.GetString(0);
            expected = Math.Max(expected, rd.GetInt32(1));
            declaredPages = Math.Max(declaredPages, rd.GetInt32(2));
            pages++;
            using var doc = JsonDocument.Parse(json);
            count += doc.RootElement.GetProperty("getBrokerReportResponse")
                .GetProperty("brokerReport").GetArrayLength();
            foreach (var (ccy, value) in BrokerReportParsing.ExtractCommissions(json))
                totals[ccy] = totals.GetValueOrDefault(ccy) + value;
        }
        if (pages == 0) warnings.Add("NO_BROKER_REPORT_PAGES_STORED");
        if (expected == 0) warnings.Add("DECLARED_ITEMS_UNKNOWN_OR_ZERO");
        if (expected > 0 && count != expected)
            warnings.Add($"BROKER_REPORT_ROW_COUNT_MISMATCH: loaded={count}, expected={expected}");
        if (declaredPages != 0 && pages < declaredPages)
            warnings.Add("PAGE_COUNT_INCOMPLETE");
        warnings.Add("Fees are summed from report rows; broker operation fees are not yet independently reconciled.");
        return new BrokerReportSummary(id, PnlCalculator.Mask(task.AccountId), task.FromUtc,
            task.ToUtc, pages, expected, count, totals,
            pages > 0 && expected > 0 && count == expected && warnings.Count == 1
                ? "raw_complete_unreconciled" : "partial", warnings);
    }
}
