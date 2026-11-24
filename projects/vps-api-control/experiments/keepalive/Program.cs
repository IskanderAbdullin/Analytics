using System.Net.WebSockets;
using System.Text;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;

var builder = WebApplication.CreateBuilder();
builder.Logging.ClearProviders();
builder.WebHost.UseUrls("http://127.0.0.1:0");
await using var app = builder.Build();
app.UseWebSockets(new Microsoft.AspNetCore.Builder.WebSocketOptions { KeepAliveInterval = Timeout.InfiniteTimeSpan });
app.Map("/echo", async (HttpContext context) =>
{
    using var ws = await context.WebSockets.AcceptWebSocketAsync();
    byte[] buffer = new byte[128];
    try
    {
        while (ws.State == WebSocketState.Open)
        {
            var incoming = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), context.RequestAborted);
            if (incoming.MessageType == WebSocketMessageType.Close) break;
            await ws.SendAsync(new ArraySegment<byte>(buffer, 0, incoming.Count), incoming.MessageType,
                incoming.EndOfMessage, context.RequestAborted);
        }
    }
    catch (Exception e) when (e is WebSocketException or OperationCanceledException or IOException) {}
});
// Reject the upgrade with an intentionally synthetic HTTP conflict.
app.Map("/conflict", (HttpContext context) => { context.Response.StatusCode = 409; return Task.CompletedTask; });
app.Map("/requests", async (HttpContext context) =>
{
    using var ws = await context.WebSockets.AcceptWebSocketAsync();
    using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(20));
    // Deliberately deliver a second request before the first response.
    foreach (string id in new[] { "one", "two" })
        await ws.SendAsync(new ArraySegment<byte>(Encoding.UTF8.GetBytes(id)),
            WebSocketMessageType.Text, true, deadline.Token);
    var first = await ReadText(ws, deadline.Token);
    var second = await ReadText(ws, deadline.Token);
    if (first != "reply:one" || second != "reply:two")
        throw new InvalidOperationException("unexpected reply sequence");
    await ws.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "done", deadline.Token);
});
await app.StartAsync();
var url = new Uri(app.Urls.Single().Replace("http://", "ws://") + "/echo");
Console.WriteLine($"runtime={Environment.Version}");
bool blocked = await Run(url, false);
bool reading = await Run(url, true);
Console.WriteLine($"serial_no_read_echo={blocked}; concurrent_read_echo={reading}");
var baseUri = new Uri(url.GetLeftPart(UriPartial.Authority));
bool serial = await SerialPump(new Uri(baseUri, "/requests"));
bool conflict = await ConflictStatus(new Uri(baseUri, "/conflict"));
await app.StopAsync();
return !blocked && reading && serial && conflict ? 0 : 1;

static async Task<bool> Run(Uri uri, bool keepReading)
{
    using var ws = new ClientWebSocket();
    ws.Options.KeepAliveInterval = TimeSpan.FromMilliseconds(500);
    ws.Options.KeepAliveTimeout = TimeSpan.FromSeconds(1);
    using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(15));
    await ws.ConnectAsync(uri, deadline.Token);
    var bytes = Encoding.UTF8.GetBytes("echo");
    var buffer = new byte[128];
    try
    {
        Task<WebSocketReceiveResult>? receive = keepReading
            ? ws.ReceiveAsync(new ArraySegment<byte>(buffer), deadline.Token)
            : null;
        // Synthetic asynchronous work: no network I/O, shell or credentials.
        await Task.Delay(TimeSpan.FromSeconds(5), deadline.Token);
        await ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, deadline.Token);
        receive ??= ws.ReceiveAsync(new ArraySegment<byte>(buffer), deadline.Token);
        var result = await receive;
        bool echoed = result.MessageType == WebSocketMessageType.Text &&
            result.EndOfMessage && bytes.SequenceEqual(buffer.Take(result.Count));
        Console.WriteLine($"keep_reading={keepReading}; echo={echoed}; state={ws.State}");
        return echoed;
    }
    catch (Exception e) when (e is WebSocketException or OperationCanceledException or InvalidOperationException)
    {
        Console.WriteLine($"keep_reading={keepReading}; echo=false; exception={e.GetType().Name}; state={ws.State}");
        return false;
    }
}

static async Task<string> ReadText(WebSocket ws, CancellationToken token)
{
    var buffer = new byte[128];
    using var body = new MemoryStream();
    do
    {
        var r = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), token);
        if (r.MessageType == WebSocketMessageType.Close) return "<close>";
        if (r.MessageType != WebSocketMessageType.Text || body.Length + r.Count > 128)
            throw new InvalidDataException("bad synthetic frame");
        body.Write(buffer, 0, r.Count);
        if (r.EndOfMessage) return Encoding.UTF8.GetString(body.ToArray());
    } while (true);
}

static async Task<bool> SerialPump(Uri uri)
{
    using var ws = new ClientWebSocket();
    ws.Options.KeepAliveInterval = TimeSpan.FromMilliseconds(500);
    ws.Options.KeepAliveTimeout = TimeSpan.FromSeconds(1);
    using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(20));
    using var readStop = CancellationTokenSource.CreateLinkedTokenSource(deadline.Token);
    await ws.ConnectAsync(uri, deadline.Token);
    Task<string> next = ReadText(ws, readStop.Token);
    var handled = new List<string>();
    try
    {
        while (true)
        {
            string id = await next;
            if (id == "<close>") break;
            next = ReadText(ws, readStop.Token);
            // Second request may already be buffered, but never dispatched
            // before the current synthetic operation and its reply complete.
            // Keep the first operation short if the next frame completed;
            // in that case no receive is outstanding.
            await Task.Delay(next.IsCompleted ? 100 : 600, deadline.Token);
            handled.Add(id);
            await ws.SendAsync(new ArraySegment<byte>(Encoding.UTF8.GetBytes("reply:" + id)),
                WebSocketMessageType.Text, true, deadline.Token);
        }
    }
    finally
    {
        readStop.Cancel();
        try { await next; } catch (OperationCanceledException) {}
    }
    bool ok = handled.SequenceEqual(new[] { "one", "two" })
        && ws.CloseStatus == WebSocketCloseStatus.NormalClosure;
    Console.WriteLine($"serial_buffered_requests={string.Join(",",handled)}; normal_close={ws.CloseStatus}; pass={ok}");
    return ok;
}

static async Task<bool> ConflictStatus(Uri uri)
{
    using var ws = new ClientWebSocket();
    ws.Options.CollectHttpResponseDetails = true;
    using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(5));
    try { await ws.ConnectAsync(uri, deadline.Token); return false; }
    catch (WebSocketException)
    {
        bool ok = (int)ws.HttpStatusCode == 409;
        Console.WriteLine($"synthetic_upgrade_http={(int)ws.HttpStatusCode}; pass={ok}");
        return ok;
    }
}
