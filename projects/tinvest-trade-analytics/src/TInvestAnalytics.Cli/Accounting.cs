using System.Globalization;
using System.Text.Json.Serialization;

namespace TInvestAnalytics;

public sealed record PnlComponent(string Name, string Currency, decimal Amount, string Scope,
    string Quality, int SourceOperations);
public sealed record PnlReport(
    string AccountRef, DateTimeOffset FromUtc, DateTimeOffset ToUtc,
    string Status, IReadOnlyList<PnlComponent> Components,
    IReadOnlyList<string> Warnings, int SourceOperationCount, int UnclassifiedCount,
    string Method = "security-fifo-plus-settled-cash-components/v1")
{
    public IReadOnlyDictionary<string, decimal> TotalsByCurrency =>
        Components.Where(x => x.Name is "SECURITY_REALIZED_GROSS" or "FUTURES_VM_SETTLED"
                   or "BROKER_FEES" or "MARGIN_FINANCING" or "INVESTMENT_INCOME")
            .GroupBy(x => x.Currency).ToDictionary(x => x.Key, x => x.Sum(p => p.Amount));
    // The totals deliberately EXCLUDE funding (possibly embedded in VM), taxes and mark-to-market.
    // They are NOT a complete account-equity P&L and must never be presented as such.
}

internal sealed class PositionLot
{
    public int Sign { get; }
    public decimal Quantity { get; set; }
    public decimal EntryPrice { get; }
    public PositionLot(int sign, decimal qty, decimal price)
    {
        Sign = sign;
        Quantity = qty;
        EntryPrice = price;
    }
}

public static class SecurityLotMatcher
{
    public static IReadOnlyList<PnlComponent> Match(IReadOnlyList<BrokerOperation> operations,
        IReadOnlyDictionary<string, string> instrumentTypes, List<string> warnings)
    {
        // Not cross-account: a security subledger is keyed by account+instrument+currency.
        var pools = new Dictionary<(string Account, string Instrument, string Currency), Queue<PositionLot>>();
        var pnl = new Dictionary<(string Instrument, string Currency), decimal>();
        var matched = new Dictionary<(string Instrument, string Currency), int>();
        foreach (var op in operations.OrderBy(x => x.DateUtc).ThenBy(x => x.ExternalId, StringComparer.Ordinal))
        {
            if (!op.IsTrade || !op.IsExecuted) continue;
            var key = op.InstrumentKey;
            if (!instrumentTypes.TryGetValue(key, out string? assetClass) ||
                assetClass is not ("stock" or "fund" or "bond" or "currency"))
            {
                warnings.Add("UNCLASSIFIED_TRADE: " + key + "; excluded from security FIFO.");
                continue;
            }
            if (op.Payment is null)
            {
                warnings.Add("MISSING_TRADE_CURRENCY: " + key);
                continue;
            }
            var currency = op.Payment.Value.Currency;
            var poolKey = (op.AccountId, key, currency);
            if (!pools.TryGetValue(poolKey, out var open))
            {
                open = new Queue<PositionLot>();
                pools[poolKey] = open;
            }
            var reportKey = (key, currency);
            foreach (var fill in op.Executions)
            {
                if (fill.Quantity <= 0 || fill.Price <= 0)
                {
                    warnings.Add("INVALID_FILL: " + key);
                    continue;
                }
                // For bonds, quotation might be percent of nominal. Such instruments require
                // per-instrument nominal/price conversion; don't assume 1 point = 1 currency unit.
                if (assetClass == "bond")
                {
                    warnings.Add("BOND_QUOTE_UNSUPPORTED: " + key + "; bond trades excluded.");
                    continue;
                }
                int side = op.IsBuy ? 1 : -1;
                decimal remaining = fill.Quantity;
                while (remaining > 0 && open.Count > 0 && open.Peek().Sign != side)
                {
                    var lot = open.Peek();
                    decimal qty = Math.Min(remaining, lot.Quantity);
                    decimal realized = lot.Sign == 1
                        ? (fill.Price - lot.EntryPrice) * qty
                        : (lot.EntryPrice - fill.Price) * qty;
                    pnl[reportKey] = pnl.GetValueOrDefault(reportKey) + realized;
                    matched[reportKey] = matched.GetValueOrDefault(reportKey) + 1;
                    lot.Quantity -= qty;
                    remaining -= qty;
                    if (lot.Quantity == 0) open.Dequeue();
                }
                if (remaining > 0) open.Enqueue(new PositionLot(side, remaining, fill.Price));
            }
            if (op.Executions.Count == 0)
                warnings.Add("NO_EXECUTIONS: " + key + "; cannot match FIFO.");
        }
        return pnl.Select(x => new PnlComponent("SECURITY_REALIZED_GROSS", x.Key.Currency,
            x.Value, x.Key.Instrument, "provisional", matched[x.Key])).ToList();
    }
}

public static class PnlCalculator
{
    // Any newly encountered type defaults to UNKNOWN; never infer cash profit from amount sign alone.
    private static readonly HashSet<string> Fees = new(StringComparer.Ordinal)
    {
        "OPERATION_TYPE_BROKER_FEE","OPERATION_TYPE_SERVICE_FEE",
        "OPERATION_TYPE_CASH_FEE","OPERATION_TYPE_OTHER_FEE",
        "OPERATION_TYPE_OUT_FEE","OPERATION_TYPE_OVER_COM",
        "OPERATION_TYPE_SUCCESS_FEE","OPERATION_TYPE_TRACK_MFEE",
        "OPERATION_TYPE_TRACK_PFEE","OPERATION_TYPE_ADVICE_FEE"
    };
    private static readonly HashSet<string> Financing = new(StringComparer.Ordinal)
    {
        "OPERATION_TYPE_MARGIN_FEE","OPERATION_TYPE_OVERNIGHT",
        "OPERATION_TYPE_OVER_PLACEMENT"
    };
    private static readonly HashSet<string> Income = new(StringComparer.Ordinal)
    {
        "OPERATION_TYPE_DIVIDEND","OPERATION_TYPE_COUPON",
        "OPERATION_TYPE_DIV_EXT","OPERATION_TYPE_OVER_INCOME"
    };
    private static readonly HashSet<string> Taxes = new(StringComparer.Ordinal)
    {
        "OPERATION_TYPE_TAX","OPERATION_TYPE_BOND_TAX",
        "OPERATION_TYPE_DIVIDEND_TAX","OPERATION_TYPE_BENEFIT_TAX",
        "OPERATION_TYPE_TAX_PROGRESSIVE","OPERATION_TYPE_BOND_TAX_PROGRESSIVE",
        "OPERATION_TYPE_DIVIDEND_TAX_PROGRESSIVE",
        "OPERATION_TYPE_BENEFIT_TAX_PROGRESSIVE",
        "OPERATION_TYPE_TAX_CORRECTION","OPERATION_TYPE_TAX_CORRECTION_PROGRESSIVE",
        "OPERATION_TYPE_TAX_CORRECTION_COUPON","OPERATION_TYPE_TAX_REPO",
        "OPERATION_TYPE_TAX_REPO_PROGRESSIVE"
    };
    private static readonly HashSet<string> ExternalFlows = new(StringComparer.Ordinal)
    {
        "OPERATION_TYPE_INPUT","OPERATION_TYPE_OUTPUT","OPERATION_TYPE_INPUT_SWIFT",
        "OPERATION_TYPE_OUTPUT_SWIFT","OPERATION_TYPE_INPUT_ACQUIRING",
        "OPERATION_TYPE_OUTPUT_ACQUIRING","OPERATION_TYPE_INP_MULTI",
        "OPERATION_TYPE_OUT_MULTI","OPERATION_TYPE_INPUT_SECURITIES",
        "OPERATION_TYPE_OUTPUT_SECURITIES","OPERATION_TYPE_TRANS_IIS_BS",
        "OPERATION_TYPE_TRANS_BS_BS"
    };
    private static readonly HashSet<string> IgnoredKnown = new(StringComparer.Ordinal)
    {
        "OPERATION_TYPE_BUY","OPERATION_TYPE_SELL","OPERATION_TYPE_BUY_CARD",
        "OPERATION_TYPE_SELL_CARD","OPERATION_TYPE_BUY_MARGIN",
        "OPERATION_TYPE_SELL_MARGIN","OPERATION_TYPE_UNSPECIFIED",
        "OPERATION_TYPE_FUTURE_EXPIRATION","OPERATION_TYPE_OPTION_EXPIRATION",
        "OPERATION_TYPE_BOND_REPAYMENT","OPERATION_TYPE_BOND_REPAYMENT_FULL",
        "OPERATION_TYPE_DELIVERY_BUY","OPERATION_TYPE_DELIVERY_SELL",
        "OPERATION_TYPE_PRIMARY_ORDER"
    };

    public static PnlReport Calculate(string accountId,
        IReadOnlyList<BrokerOperation> operations,
        IReadOnlyDictionary<string, string>? instrumentTypes,
        DateTimeOffset from, DateTimeOffset to)
    {
        var warnings = new List<string>();
        var known = instrumentTypes ?? new Dictionary<string, string>();
        var components = new List<PnlComponent>();
        var settled = operations.Where(x => x.IsExecuted).ToList();
        // Don't auto-deduplicate colliding fingerprints: two same-time trades might be distinct.
        var dup = settled.GroupBy(x => x.SemanticFingerprint).Where(g => g.Count() > 1).ToList();
        foreach (var d in dup)
            warnings.Add("POSSIBLE_DUPLICATE_SEMANTIC_EVENT: " + d.Key[..12] +
                " count=" + d.Count().ToString(CultureInfo.InvariantCulture));
        components.AddRange(SecurityLotMatcher.Match(settled, known, warnings));
        var aggregate = new Dictionary<(string Name, string Currency, string Scope), (decimal Amount, int Count)>();
        int unknown = 0;
        foreach (var op in operations)
        {
            if (!op.IsExecuted)
            {
                if (op.State != "OPERATION_STATE_CANCELED")
                    warnings.Add("UNSETTLED_OPERATION: " + op.Type);
                continue;
            }
            string? component = op.Type switch
            {
                "OPERATION_TYPE_ACCRUING_VARMARGIN" or "OPERATION_TYPE_WRITING_OFF_VARMARGIN"
                    => "FUTURES_VM_SETTLED",
                "OPERATION_TYPE_FUNDING" => "FUNDING_UNVERIFIED_NOT_INCLUDED",
                _ when Fees.Contains(op.Type) => "BROKER_FEES",
                _ when Financing.Contains(op.Type) => "MARGIN_FINANCING",
                _ when Income.Contains(op.Type) => "INVESTMENT_INCOME",
                _ when Taxes.Contains(op.Type) => "TAX_WITHHELD_SEPARATE",
                _ when ExternalFlows.Contains(op.Type) => "EXTERNAL_FLOW_NOT_PNL",
                _ when IgnoredKnown.Contains(op.Type) => null,
                _ => "UNSUPPORTED_OPERATION"
            };
            if (component is null) continue;
            if (component == "UNSUPPORTED_OPERATION")
            {
                unknown++;
                warnings.Add("UNSUPPORTED_OPERATION: " + op.Type);
                continue;
            }
            if (op.Payment is null)
            {
                warnings.Add("MISSING_PAYMENT: " + op.Type);
                continue;
            }
            var money = op.Payment.Value;
            var key = (component, money.Currency, op.InstrumentKey);
            var current = aggregate.GetValueOrDefault(key);
            aggregate[key] = (current.Amount + money.Amount, current.Count + 1);
            if (component == "FUNDING_UNVERIFIED_NOT_INCLUDED")
                warnings.Add("FUNDING_OVERLAP_UNVERIFIED: " + op.InstrumentKey);
        }
        foreach (var kv in aggregate)
            components.Add(new PnlComponent(kv.Key.Name, kv.Key.Currency, kv.Value.Amount,
                kv.Key.Scope, kv.Key.Name is "EXTERNAL_FLOW_NOT_PNL" ? "observed" : "provisional",
                kv.Value.Count));
        if (known.Count == 0 && settled.Any(x => x.IsTrade))
            warnings.Add("Instrument types not configured: no realized security P&L is asserted.");
        warnings.Add("This is a PARTIAL realized-and-settled report, not total equity P&L; " +
            "no current open-position valuation or independent broker reconciliation.");
        return new PnlReport(Mask(accountId), from, to, "partial",
            components.OrderBy(x => x.Currency).ThenBy(x => x.Name).ThenBy(x => x.Scope).ToList(),
            warnings.Distinct().ToList(), operations.Count, unknown);
    }

    public static string Mask(string? account)
    {
        if (string.IsNullOrEmpty(account)) return "(none)";
        return account.Length <= 4 ? "****" : "***" + account[^4..];
    }
}
