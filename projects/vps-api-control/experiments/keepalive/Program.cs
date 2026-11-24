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
await app.StartAsync();
var url = new Uri(app.Urls.Single().Replace("http://", "ws://") + "/echo");
Console.WriteLine($"runtime={Environment.Version}");
bool blocked = await Run(url, false);
bool reading = await Run(url, true);
Console.WriteLine($"serial_no_read_echo={blocked}; concurrent_read_echo={reading}");
await app.StopAsync();
return !blocked && reading ? 0 : 1;

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
