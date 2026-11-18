using System.Globalization;
using Microsoft.Data.Sqlite;

namespace TInvestAnalytics;

public sealed record SyncCheckpoint(string WindowId, string? Cursor, bool Complete, long Pages, long Items);

/// <summary>Local-only SQLite evidence store. Raw pages and observations are append-only.</summary>
public sealed partial class EvidenceStore
{
    private readonly string _dbPath;
    public EvidenceStore(string dbPath)
    {
        _dbPath = Path.GetFullPath(dbPath);
        Directory.CreateDirectory(Path.GetDirectoryName(_dbPath)!);
    }

    private SqliteConnection Open()
    {
        var builder = new SqliteConnectionStringBuilder { DataSource = _dbPath };
        var c = new SqliteConnection(builder.ToString());
        c.Open();
        return c;
    }
    private static SqliteCommand Command(SqliteConnection c, SqliteTransaction? tx,
        string sql, params (string Key, object? Value)[] args)
    {
        var q = c.CreateCommand();
        q.Transaction = tx;
        q.CommandText = sql;
        foreach (var (key, value) in args) q.Parameters.AddWithValue(key, value ?? DBNull.Value);
        return q;
    }

    public void Initialize()
    {
        using var c = Open();
        using var q = Command(c, null, """
            PRAGMA journal_mode=WAL;
            PRAGMA busy_timeout=5000;
            CREATE TABLE IF NOT EXISTS sync_windows (
                window_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                from_utc TEXT NOT NULL,
                to_utc TEXT NOT NULL,
                cursor_next TEXT,
                complete INTEGER NOT NULL DEFAULT 0,
                pages INTEGER NOT NULL DEFAULT 0,
                items INTEGER NOT NULL DEFAULT 0,
                updated_utc TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS raw_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                window_id TEXT NOT NULL REFERENCES sync_windows(window_id),
                cursor_in TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                recorded_utc TEXT NOT NULL,
                UNIQUE(window_id, cursor_in, payload_sha256)
            );
            CREATE TABLE IF NOT EXISTS operation_revisions (
                account_id TEXT NOT NULL,
                external_id TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                semantic_fingerprint TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                recorded_utc TEXT NOT NULL,
                PRIMARY KEY(account_id, external_id, payload_sha256)
            );
            CREATE TABLE IF NOT EXISTS current_operations (
                account_id TEXT NOT NULL,
                external_id TEXT NOT NULL,
                semantic_fingerprint TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                observed_utc TEXT NOT NULL,
                PRIMARY KEY(account_id, external_id)
            );
            CREATE INDEX IF NOT EXISTS ix_current_semantic
                ON current_operations(account_id,semantic_fingerprint);
            CREATE INDEX IF NOT EXISTS ix_revision_semantic
                ON operation_revisions(account_id,semantic_fingerprint);
            CREATE INDEX IF NOT EXISTS ix_window_account ON sync_windows(account_id,from_utc,to_utc);
            """);
        q.ExecuteNonQuery();
        InitializePortfolio();
        InitializeBotTelemetry();
        InitializeBrokerReports();
    }

    public static string WindowId(string accountId, DateTimeOffset from, DateTimeOffset to)
    {
        return OperationParser.Hash(accountId + "|" + from.ToUniversalTime().ToString("O") +
            "|" + to.ToUniversalTime().ToString("O"));
    }
    public SyncCheckpoint GetCheckpoint(string accountId, DateTimeOffset from, DateTimeOffset to)
    {
        var id = WindowId(accountId, from, to);
        using var c = Open();
        using var q = Command(c, null, """
            SELECT cursor_next,complete,pages,items FROM sync_windows WHERE window_id=$w
            """, ("$w", id));
        using var reader = q.ExecuteReader();
        if (!reader.Read()) return new SyncCheckpoint(id, null, false, 0, 0);
        return new SyncCheckpoint(id, reader.IsDBNull(0) ? null : reader.GetString(0),
            reader.GetInt64(1) == 1, reader.GetInt64(2), reader.GetInt64(3));
    }


    /// <summary>Explicit re-read of a completed historical window; never deletes raw evidence.</summary>
    public void RestartWindow(string accountId, DateTimeOffset from, DateTimeOffset to)
    {
        var id = WindowId(accountId, from, to);
        using var c = Open();
        using var q = Command(c, null, """
            UPDATE sync_windows SET cursor_next=NULL,complete=0,pages=0,items=0,
                updated_utc=$now WHERE window_id=$w
            """, ("$now", DateTimeOffset.UtcNow.ToString("O")), ("$w", id));
        q.ExecuteNonQuery();
    }

    public int ImportPage(string accountId, DateTimeOffset from, DateTimeOffset to,
        string? cursorIn, string? cursorNext, bool hasNext, string pageJson)
    {
        if (from >= to) throw new ArgumentOutOfRangeException(nameof(from), "from must be before to");
        if (hasNext && string.IsNullOrWhiteSpace(cursorNext))
            throw new InvalidDataException("API page says hasNext but has no cursor; not marking as complete.");
        if (hasNext && cursorIn == cursorNext)
            throw new InvalidDataException("Cursor cycle detected.");
        using var parsed = System.Text.Json.JsonDocument.Parse(pageJson);
        var root = parsed.RootElement;
        if (!root.TryGetProperty("items", out var items) || items.ValueKind != System.Text.Json.JsonValueKind.Array)
            throw new FormatException("Expected T-Invest operations response with items array.");
        var ops = OperationParser.ParsePage(accountId, pageJson);
        string id = WindowId(accountId, from, to);
        string time = DateTimeOffset.UtcNow.ToString("O");
        string digest = OperationParser.Hash(pageJson);
        using var c = Open();
        using var tx = c.BeginTransaction();
        using (var insert = Command(c, tx, """
            INSERT INTO sync_windows(window_id,account_id,from_utc,to_utc,cursor_next,complete,pages,items,updated_utc)
            VALUES($w,$a,$f,$t,NULL,0,0,0,$now)
            ON CONFLICT(window_id) DO NOTHING
            """, ("$w", id), ("$a", accountId), ("$f", from.ToUniversalTime().ToString("O")),
            ("$t", to.ToUniversalTime().ToString("O")), ("$now", time))) insert.ExecuteNonQuery();
        int pageInsert;
        using (var insert = Command(c, tx, """
            INSERT OR IGNORE INTO raw_pages(window_id,cursor_in,payload_sha256,payload_json,recorded_utc)
            VALUES($w,$cursor,$sha,$payload,$now)
            """, ("$w", id), ("$cursor", cursorIn ?? ""), ("$sha", digest),
            ("$payload", pageJson), ("$now", time))) pageInsert = insert.ExecuteNonQuery();
        foreach (var op in ops)
        {
            string opHash = OperationParser.Hash(op.RawJson);
            using (var q = Command(c, tx, """
                INSERT OR IGNORE INTO operation_revisions
                (account_id,external_id,payload_sha256,semantic_fingerprint,raw_json,recorded_utc)
                VALUES($a,$oid,$sha,$fp,$raw,$now)
                """, ("$a", accountId), ("$oid", op.ExternalId), ("$sha", opHash),
                ("$fp", op.SemanticFingerprint), ("$raw", op.RawJson), ("$now", time)))
                q.ExecuteNonQuery();
            using (var q = Command(c, tx, """
                INSERT INTO current_operations(account_id,external_id,semantic_fingerprint,raw_json,observed_utc)
                VALUES($a,$oid,$fp,$raw,$now)
                ON CONFLICT(account_id,external_id) DO UPDATE SET
                    semantic_fingerprint=excluded.semantic_fingerprint,
                    raw_json=excluded.raw_json,observed_utc=excluded.observed_utc
                """, ("$a", accountId), ("$oid", op.ExternalId),
                ("$fp", op.SemanticFingerprint), ("$raw", op.RawJson), ("$now", time)))
                q.ExecuteNonQuery();
        }
        using (var q = Command(c, tx, """
            UPDATE sync_windows SET cursor_next=$cursor,complete=$complete,
                pages=pages+$page,items=items+$items,updated_utc=$now WHERE window_id=$w
            """, ("$cursor", hasNext ? cursorNext : null), ("$complete", hasNext ? 0 : 1),
            ("$page", pageInsert), ("$items", pageInsert == 0 ? 0 : ops.Count),
            ("$now", time), ("$w", id))) q.ExecuteNonQuery();
        tx.Commit();
        return ops.Count;
    }

    public IReadOnlyList<BrokerOperation> LoadOperations(string accountId, DateTimeOffset from, DateTimeOffset to)
    {
        using var c = Open();
        using var q = Command(c, null, """
            SELECT raw_json FROM current_operations WHERE account_id=$a
            """, ("$a", accountId));
        var result = new List<BrokerOperation>();
        using var reader = q.ExecuteReader();
        while (reader.Read())
        {
            using var doc = System.Text.Json.JsonDocument.Parse(reader.GetString(0));
            var op = OperationParser.Parse(accountId, doc.RootElement);
            if (op.DateUtc >= from && op.DateUtc < to) result.Add(op);
        }
        return result.OrderBy(x => x.DateUtc).ThenBy(x => x.ExternalId, StringComparer.Ordinal).ToList();
    }

    public IReadOnlyList<(string Fingerprint, int Count)> AmbiguousFingerprints(
        string accountId, DateTimeOffset from, DateTimeOffset to)
    {
        var all = LoadOperations(accountId, from, to);
        return all.GroupBy(x => x.SemanticFingerprint).Where(x => x.Count() > 1)
            .Select(x => (x.Key, x.Count())).ToList();
    }

    public (long Pages, long Revisions, long CurrentOperations, long CompleteWindows) Stats()
    {
        using var c = Open();
        using var q = Command(c, null, """
            SELECT
            (SELECT COUNT(*) FROM raw_pages),
            (SELECT COUNT(*) FROM operation_revisions),
            (SELECT COUNT(*) FROM current_operations),
            (SELECT COUNT(*) FROM sync_windows WHERE complete=1)
            """);
        using var reader = q.ExecuteReader();
        reader.Read();
        return (reader.GetInt64(0), reader.GetInt64(1), reader.GetInt64(2), reader.GetInt64(3));
    }
}
