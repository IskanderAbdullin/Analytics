using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace TInvestAnalytics;

public readonly record struct Money(decimal Amount, string Currency)
{
    public Money Add(Money other)
    {
        if (!Currency.Equals(other.Currency, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Cannot add amounts in different currencies.");
        return new Money(Amount + other.Amount, Currency);
    }
    public static Money FromJson(JsonElement item)
    {
        if (item.ValueKind != JsonValueKind.Object)
            throw new FormatException("Money must be an object containing currency/units/nano.");
        var currency = JsonValue.Text(item, "currency")?.ToUpperInvariant();
        if (string.IsNullOrWhiteSpace(currency))
            throw new FormatException("Money currency is missing.");
        decimal units = JsonValue.DecimalOr(item, "units", 0);
        decimal nano = JsonValue.DecimalOr(item, "nano", 0);
        if (nano is <= -1_000_000_000m or >= 1_000_000_000m)
            throw new FormatException("Money nano must be within (-1e9, 1e9).");
        // API signed units+nano: both components have their own signs.
        return new Money(units + nano / 1_000_000_000m, currency);
    }
    public override string ToString() => Amount.ToString("0.#########", CultureInfo.InvariantCulture) + " " + Currency;
}

public static class JsonValue
{
    public static JsonElement? Field(JsonElement node, string property)
    {
        if (node.ValueKind != JsonValueKind.Object) return null;
        if (node.TryGetProperty(property, out var v)) return v;
        return null;
    }
    public static string? Text(JsonElement node, string property)
    {
        var value = Field(node, property);
        if (value is null || value.Value.ValueKind == JsonValueKind.Null) return null;
        return value.Value.ValueKind switch
        {
            JsonValueKind.String => value.Value.GetString(),
            JsonValueKind.Number => value.Value.GetRawText(),
            _ => null
        };
    }
    public static decimal DecimalOr(JsonElement node, string property, decimal fallback)
    {
        string? val = Text(node, property);
        return val is null ? fallback : decimal.Parse(val, NumberStyles.Float, CultureInfo.InvariantCulture);
    }
    public static bool BooleanOr(JsonElement node, string property, bool fallback)
    {
        var value = Field(node, property);
        return value is { ValueKind: JsonValueKind.True } ? true :
               value is { ValueKind: JsonValueKind.False } ? false : fallback;
    }
    public static DateTimeOffset? Date(JsonElement node, string property)
    {
        var s = Text(node, property);
        return s is null ? null : DateTimeOffset.Parse(s, CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal);
    }
}

public sealed record Execution(string TradeId, DateTimeOffset TimeUtc, decimal Quantity, decimal Price);
public sealed record BrokerOperation(
    string ExternalId, string AccountId, string Type, string State,
    DateTimeOffset DateUtc, string InstrumentUid, string Figi, Money? Payment,
    decimal Quantity, decimal? UnitPrice, IReadOnlyList<Execution> Executions,
    string RawJson, string SemanticFingerprint)
{
    public bool IsExecuted => State is "OPERATION_STATE_EXECUTED" or "EXECUTED" or "";
    public bool IsBuy => Type is "OPERATION_TYPE_BUY" or "OPERATION_TYPE_BUY_CARD" or "OPERATION_TYPE_BUY_MARGIN";
    public bool IsSell => Type is "OPERATION_TYPE_SELL" or "OPERATION_TYPE_SELL_MARGIN" or "OPERATION_TYPE_SELL_CARD";
    public bool IsTrade => IsBuy || IsSell;
    public string InstrumentKey => !string.IsNullOrWhiteSpace(InstrumentUid) ? InstrumentUid :
        !string.IsNullOrWhiteSpace(Figi) ? "figi:" + Figi : "UNKNOWN_INSTRUMENT";
    public string? Currency => Payment?.Currency;
}

public static class OperationParser
{
    public static BrokerOperation Parse(string accountId, JsonElement operation)
    {
        string raw = operation.GetRawText();
        var id = JsonValue.Text(operation, "id") ?? JsonValue.Text(operation, "operationId") ??
                 "NO_ID_" + Hash(raw);
        var kind = JsonValue.Text(operation, "type") ?? JsonValue.Text(operation, "operationType") ?? "UNKNOWN";
        var status = JsonValue.Text(operation, "state") ?? "UNKNOWN";
        var dt = JsonValue.Date(operation, "date") ?? throw new FormatException("Operation date is missing.");
        var uid = JsonValue.Text(operation, "instrumentUid") ?? "";
        var figi = JsonValue.Text(operation, "figi") ?? "";
        Money? payment = null;
        var value = JsonValue.Field(operation, "payment");
        if (value is { ValueKind: JsonValueKind.Object }) payment = Money.FromJson(value.Value);
        decimal qty = JsonValue.DecimalOr(operation, "quantity", 0);
        decimal? price = null;
        var p = JsonValue.Field(operation, "price");
        if (p is { ValueKind: JsonValueKind.Object })
        {
            // Quotation also has "units"/"nano"; currency may be absent.
            price = JsonValue.DecimalOr(p.Value, "units", 0) +
                    JsonValue.DecimalOr(p.Value, "nano", 0) / 1_000_000_000m;
        }
        var executions = new List<Execution>();
        var trades = JsonValue.Field(operation, "trades");
        if (trades is { ValueKind: JsonValueKind.Array })
        {
            foreach (var trade in trades.Value.EnumerateArray())
            {
                var tradeId = JsonValue.Text(trade, "tradeId") ?? "";
                var tradeDt = JsonValue.Date(trade, "dateTime") ?? dt;
                var tradeQty = JsonValue.DecimalOr(trade, "quantity", 0);
                var tradePriceElement = JsonValue.Field(trade, "price");
                decimal tradePrice = price ?? 0;
                if (tradePriceElement is { ValueKind: JsonValueKind.Object })
                    tradePrice = JsonValue.DecimalOr(tradePriceElement.Value, "units", 0) +
                                 JsonValue.DecimalOr(tradePriceElement.Value, "nano", 0) / 1_000_000_000m;
                if (tradeQty > 0) executions.Add(new Execution(tradeId, tradeDt, tradeQty, tradePrice));
            }
        }
        // A fallback aggregate is lower-confidence; don't imply an exact exchange fill.
        if (executions.Count == 0 && qty > 0 && price is not null)
            executions.Add(new Execution("", dt, qty, price.Value));

        // Fingerprint excludes operation ID; possible collisions MUST be signalled, not silently merged.
        string fpBody = string.Join("|", accountId, kind, status, dt.ToUniversalTime().ToString("O"),
            uid, figi, payment?.ToString() ?? "", qty.ToString(CultureInfo.InvariantCulture),
            price?.ToString(CultureInfo.InvariantCulture) ?? "",
            string.Join(";", executions.Select(x => x.TradeId + ":" + x.TimeUtc.ToUniversalTime().ToString("O") +
            ":" + x.Price.ToString(CultureInfo.InvariantCulture) + ":" +
            x.Quantity.ToString(CultureInfo.InvariantCulture))));
        return new BrokerOperation(id, accountId, kind, status, dt, uid, figi, payment, qty,
            price, executions, raw, Hash(fpBody));
    }
    public static string Hash(string value) =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value))).ToLowerInvariant();

    public static IReadOnlyList<BrokerOperation> ParsePage(string accountId, string pageJson)
    {
        using var doc = JsonDocument.Parse(pageJson);
        if (!doc.RootElement.TryGetProperty("items", out var array) || array.ValueKind != JsonValueKind.Array)
            throw new FormatException("T-Invest response is missing an items array.");
        return array.EnumerateArray().Select(x => Parse(accountId, x)).ToList();
    }
}
