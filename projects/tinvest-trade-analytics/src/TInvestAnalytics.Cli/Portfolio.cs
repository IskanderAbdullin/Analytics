using System.Globalization;
using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace TInvestAnalytics;

/// <summary>
/// Broker portfolio snapshots are observed valuations, not independent trade-ledger reconciliation.
/// As-of is the time at which this client received the response, not guaranteed exchange mark time.
/// </summary>
public sealed record PortfolioSnapshot(long Id, string AccountId, DateTimeOffset ObservedAtUtc,
    Money Equity, string PortfolioSha256, string PositionsSha256);

public sealed record EquityChangeReport(
    string AccountRef, long StartSnapshotId, long EndSnapshotId,
    DateTimeOffset FromObservedUtc, DateTimeOffset ToObservedUtc, string Currency,
    decimal InitialEquity, decimal FinalEquity, decimal NetExternalFlows,
    decimal AbsoluteEquityPnl, string Quality, IReadOnlyList<string> Warnings,
    string Policy = "snapshot-equity-less-external-flows/v1");

public static class PortfolioMath
{
    private static readonly HashSet<string> CashFlows = new(StringComparer.Ordinal)
    {
        "OPERATION_TYPE_INPUT","OPERATION_TYPE_OUTPUT","OPERATION_TYPE_INPUT_SWIFT",
        "OPERATION_TYPE_OUTPUT_SWIFT","OPERATION_TYPE_INPUT_ACQUIRING",
        "OPERATION_TYPE_OUTPUT_ACQUIRING","OPERATION_TYPE_INP_MULTI",
        "OPERATION_TYPE_OUT_MULTI"
    };
    private static readonly HashSet<string> SecurityTransfer = new(StringComparer.Ordinal)
    {
        "OPERATION_TYPE_INPUT_SECURITIES","OPERATION_TYPE_OUTPUT_SECURITIES",
        "OPERATION_TYPE_TRANS_IIS_BS","OPERATION_TYPE_TRANS_BS_BS"
    };
    public static EquityChangeReport Calculate(PortfolioSnapshot begin, PortfolioSnapshot end,
        IReadOnlyList<BrokerOperation> operations, bool completeOperationCoverage)
    {
        if (begin.AccountId != end.AccountId)
            throw new InvalidOperationException("Cannot compare snapshots from different accounts.");
        if (begin.ObservedAtUtc >= end.ObservedAtUtc)
            throw new ArgumentException("Start snapshot must be earlier.");
        if (begin.Equity.Currency != end.Equity.Currency)
            throw new InvalidOperationException("Snapshots must have the same valuation currency.");
        var warnings = new List<string>();
        if (!completeOperationCoverage)
            warnings.Add("INCOMPLETE_CASHFLOW_COVERAGE: operations history does not fully cover snapshot interval.");
        decimal external = 0;
        foreach (var op in operations)
        {
            if (op.DateUtc <= begin.ObservedAtUtc || op.DateUtc > end.ObservedAtUtc) continue;
            if (!op.IsExecuted) continue;
            if (SecurityTransfer.Contains(op.Type))
            {
                warnings.Add("SECURITIES_TRANSFER_UNVALUED: " + op.Type);
                continue;
            }
            if (!CashFlows.Contains(op.Type)) continue;
            if (op.Payment is null)
            {
                warnings.Add("EXTERNAL_FLOW_MISSING_PAYMENT: " + op.Type);
                continue;
            }
            if (op.Payment.Value.Currency != begin.Equity.Currency)
            {
                warnings.Add("EXTERNAL_FLOW_FX_UNAVAILABLE: " + op.Payment.Value.Currency);
                continue;
            }
            external += op.Payment.Value.Amount;
        }
        decimal pnl = end.Equity.Amount - begin.Equity.Amount - external;
        // Never "verified": snapshots are observed at different times and live portfolio
        // marks may lag. Independent broker report and historical FX are still required.
        var quality = completeOperationCoverage && warnings.Count == 0 ? "provisional" : "partial";
        warnings.Add("Portfolio as-of exchange marks and settled positions not independently verified.");
        return new EquityChangeReport(PnlCalculator.Mask(begin.AccountId), begin.Id, end.Id,
            begin.ObservedAtUtc, end.ObservedAtUtc, begin.Equity.Currency,
            begin.Equity.Amount, end.Equity.Amount, external, pnl, quality, warnings);
    }
    public static Money ReadPortfolioEquity(string portfolioResponse)
    {
        using var doc = JsonDocument.Parse(portfolioResponse);
        if (!doc.RootElement.TryGetProperty("totalAmountPortfolio", out var item))
            throw new FormatException("GetPortfolio response is missing totalAmountPortfolio.");
        return Money.FromJson(item);
    }
}

public sealed partial class EvidenceStore
{
    public void InitializePortfolio()
    {
        using var c = Open();
        using var cmd = Command(c, null, """
            CREATE TABLE IF NOT EXISTS portfolio_observations (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                observed_utc TEXT NOT NULL,
                currency TEXT NOT NULL,
                equity_decimal TEXT NOT NULL,
                portfolio_sha256 TEXT NOT NULL,
                positions_sha256 TEXT NOT NULL,
                raw_portfolio TEXT NOT NULL,
                raw_positions TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_snapshots_account_date
                ON portfolio_observations(account_id, observed_utc);
            """);
        cmd.ExecuteNonQuery();
    }

    public PortfolioSnapshot SavePortfolio(string accountId, DateTimeOffset observedAt,
        string rawPortfolio, string rawPositions)
    {
        var equity = PortfolioMath.ReadPortfolioEquity(rawPortfolio);
        using var positionsDoc = JsonDocument.Parse(rawPositions);
        if (positionsDoc.RootElement.ValueKind != JsonValueKind.Object)
            throw new FormatException("GetPositions response expected JSON object.");
        string pHash = OperationParser.Hash(rawPortfolio);
        string xHash = OperationParser.Hash(rawPositions);
        using var c = Open();
        using var tx = c.BeginTransaction();
        long id;
        using (var q = Command(c, tx, """
            INSERT INTO portfolio_observations
            (account_id,observed_utc,currency,equity_decimal,portfolio_sha256,positions_sha256,
             raw_portfolio,raw_positions)
            VALUES($a,$time,$ccy,$equity,$p,$x,$rawp,$rawx)
            """, ("$a", accountId), ("$time", observedAt.ToUniversalTime().ToString("O")),
            ("$ccy", equity.Currency), ("$equity", equity.Amount.ToString(CultureInfo.InvariantCulture)),
            ("$p", pHash), ("$x", xHash), ("$rawp", rawPortfolio), ("$rawx", rawPositions)))
        {
            q.ExecuteNonQuery();
            using var idCommand = Command(c, tx, "SELECT last_insert_rowid();");
            id = Convert.ToInt64(idCommand.ExecuteScalar(), CultureInfo.InvariantCulture);
        }
        tx.Commit();
        return new PortfolioSnapshot(id, accountId, observedAt, equity, pHash, xHash);
    }

    public IReadOnlyList<PortfolioSnapshot> GetSnapshots(string accountId)
    {
        using var c = Open();
        using var q = Command(c, null, """
            SELECT snapshot_id,observed_utc,currency,equity_decimal,portfolio_sha256,positions_sha256
            FROM portfolio_observations WHERE account_id=$a ORDER BY observed_utc, snapshot_id
            """, ("$a", accountId));
        using var reader = q.ExecuteReader();
        var list = new List<PortfolioSnapshot>();
        while (reader.Read())
            list.Add(new PortfolioSnapshot(reader.GetInt64(0), accountId,
                DateTimeOffset.Parse(reader.GetString(1), CultureInfo.InvariantCulture),
                new Money(decimal.Parse(reader.GetString(3), CultureInfo.InvariantCulture), reader.GetString(2)),
                reader.GetString(4), reader.GetString(5)));
        return list;
    }

    public bool HasCompleteOperationsWindow(string account, DateTimeOffset from, DateTimeOffset to)
    {
        // First implementation only proves coverage if a single complete query window
        // contains the whole interval. Disjoint windows are never assumed to be complete.
        using var c = Open();
        using var q = Command(c, null, """
            SELECT count(*) FROM sync_windows WHERE account_id=$a AND complete=1
              AND from_utc<=$f AND to_utc>=$t
            """, ("$a", account), ("$f", from.ToUniversalTime().ToString("O")),
            ("$t", to.ToUniversalTime().ToString("O")));
        return Convert.ToInt64(q.ExecuteScalar(), CultureInfo.InvariantCulture) > 0;
    }
}
