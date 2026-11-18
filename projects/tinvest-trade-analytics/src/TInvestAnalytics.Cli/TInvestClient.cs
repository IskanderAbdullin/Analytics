using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;

namespace TInvestAnalytics;

/// <summary>
/// Read-only REST adapter, with strict allowlist of endpoints.
/// There is intentionally no order placement/cancellation or trading API.
/// </summary>
public sealed class TInvestClient : IDisposable
{
    private readonly HttpClient _http;
    private readonly TimeSpan _minGap = TimeSpan.FromMilliseconds(650);
    private DateTimeOffset _lastRequest = DateTimeOffset.MinValue;
    private readonly SemaphoreSlim _gate = new(1, 1);
    public string Endpoint { get; }

    public TInvestClient(string token, bool sandbox = false, HttpMessageHandler? handler = null)
    {
        if (string.IsNullOrWhiteSpace(token)) throw new ArgumentException("Read-only token is missing.");
        Endpoint = sandbox ? "https://sandbox-invest-public-api.tbank.ru/rest/tinkoff.public.invest.api.contract.v1."
            : "https://invest-public-api.tbank.ru/rest/tinkoff.public.invest.api.contract.v1.";
        _http = handler is null ? new HttpClient() : new HttpClient(handler);
        _http.Timeout = TimeSpan.FromSeconds(35);
        _http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        _http.DefaultRequestHeaders.UserAgent.ParseAdd("TInvestAnalytics/0.1-readonly");
    }

    private async Task<string> PostAsync(string allowedServiceMethod, object payload,
        CancellationToken ct)
    {
        // Whitelist is essential. A read-only application must not expose arbitrary API routes.
        if (allowedServiceMethod is not ("UsersService/GetAccounts"
            or "UsersService/GetUserTariff"
            or "OperationsService/GetOperationsByCursor"
            or "OperationsService/GetPortfolio"
            or "OperationsService/GetPositions"
            or "OperationsService/GetBrokerReport"))
            throw new InvalidOperationException("Endpoint denied by read-only allowlist.");

        var url = Endpoint + allowedServiceMethod;
        string data = JsonSerializer.Serialize(payload);
        await _gate.WaitAsync(ct).ConfigureAwait(false);
        try
        {
            for (int attempt = 0; attempt < 6; attempt++)
            {
                var wait = _minGap - (DateTimeOffset.UtcNow - _lastRequest);
                if (wait > TimeSpan.Zero) await Task.Delay(wait, ct).ConfigureAwait(false);
                using var req = new HttpRequestMessage(HttpMethod.Post, url)
                {
                    Content = new StringContent(data, Encoding.UTF8, "application/json")
                };
                _lastRequest = DateTimeOffset.UtcNow;
                using var response = await _http.SendAsync(req, ct).ConfigureAwait(false);
                var body = await response.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
                if (response.IsSuccessStatusCode) return body;
                if (response.StatusCode is HttpStatusCode.TooManyRequests or HttpStatusCode.BadGateway
                    or HttpStatusCode.ServiceUnavailable or HttpStatusCode.GatewayTimeout
                    or HttpStatusCode.RequestTimeout)
                {
                    if (attempt == 5) throw new HttpRequestException(
                        "T-Invest requests exhausted retry budget. HTTP " + (int)response.StatusCode);
                    // Delay is conservative; never echo the upstream body (might contain account data).
                    TimeSpan retry = response.Headers.RetryAfter?.Delta ??
                        TimeSpan.FromMilliseconds(Math.Min(8000, 500 * (1 << attempt)));
                    await Task.Delay(retry, ct).ConfigureAwait(false);
                    continue;
                }
                throw new HttpRequestException("T-Invest REST error HTTP " + (int)response.StatusCode +
                    ". Check token scopes/account, date format and API contract.");
            }
            throw new InvalidOperationException("Unreachable retry state.");
        }
        finally { _gate.Release(); }
    }

    public Task<string> GetAccountsAsync(CancellationToken ct = default) =>
        PostAsync("UsersService/GetAccounts", new { }, ct);
    public Task<string> GetTariffAsync(CancellationToken ct = default) =>
        PostAsync("UsersService/GetUserTariff", new { }, ct);
    public Task<string> GetPortfolioAsync(string accountId, CancellationToken ct = default) =>
        PostAsync("OperationsService/GetPortfolio", new { accountId, currency = "RUB" }, ct);
    public Task<string> GetPositionsAsync(string accountId, CancellationToken ct = default) =>
        PostAsync("OperationsService/GetPositions", new { accountId }, ct);


    public Task<string> GenerateBrokerReportAsync(string accountId,
        DateTimeOffset from, DateTimeOffset to, CancellationToken ct = default) =>
        PostAsync("OperationsService/GetBrokerReport", new {
            generateBrokerReportRequest = new {
                accountId,
                from = from.ToUniversalTime().ToString("O"),
                to = to.ToUniversalTime().ToString("O")
            }
        }, ct);

    public Task<string> GetBrokerReportPageAsync(string taskId,
        int page, CancellationToken ct = default) =>
        PostAsync("OperationsService/GetBrokerReport",
            new { getBrokerReportRequest = new { taskId, page } }, ct);

    public Task<string> GetOperationsPageAsync(string accountId, DateTimeOffset from,
        DateTimeOffset to, string? cursor, CancellationToken ct = default) =>
        PostAsync("OperationsService/GetOperationsByCursor",
            new
            {
                accountId,
                from = from.ToUniversalTime().ToString("O"),
                to = to.ToUniversalTime().ToString("O"),
                cursor = cursor ?? "",
                limit = 1000,
                withoutCommissions = false,
                withoutTrades = false,
                withoutOvernights = false
            }, ct);

    public static IReadOnlyList<BrokerAccount> ParseAccounts(string response)
    {
        using var doc = JsonDocument.Parse(response);
        if (!doc.RootElement.TryGetProperty("accounts", out var accounts) ||
            accounts.ValueKind != JsonValueKind.Array)
            throw new FormatException("Expected T-Invest accounts array.");
        return accounts.EnumerateArray()
            .Select(x => new BrokerAccount(JsonValue.Text(x, "id") ?? "",
                JsonValue.Text(x, "name") ?? "",
                JsonValue.Text(x, "type") ?? "",
                JsonValue.Text(x, "status") ?? ""))
            .Where(x => !string.IsNullOrEmpty(x.Id)).ToArray();
    }

    public static (bool HasNext, string? NextCursor) ParsePageCursor(string response)
    {
        using var doc = JsonDocument.Parse(response);
        var obj = doc.RootElement;
        if (!obj.TryGetProperty("items", out var items) || items.ValueKind != JsonValueKind.Array)
            throw new FormatException("API response has no items array.");
        return (JsonValue.BooleanOr(obj, "hasNext", false), JsonValue.Text(obj, "nextCursor"));
    }

    public void Dispose()
    {
        _gate.Dispose();
        _http.Dispose();
    }
}

public sealed record BrokerAccount(string Id, string Name, string Type, string Status);
