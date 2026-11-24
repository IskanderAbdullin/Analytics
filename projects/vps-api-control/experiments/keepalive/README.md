# Synthetic .NET keepalive experiment

Tests the documented requirement for a continuously outstanding read when
ClientWebSocket PING/PONG timeout is enabled. Independent public loopback
experiment; does not copy private application source, call a provider,
read credentials, connect to a real server, or deploy anything.

Expected: idle synthetic work with no outstanding read aborts the
connection; an otherwise identical case with an outstanding read can
echo a text frame. Scaled timing (500 ms interval, 1 s timeout, 5 s work)
makes the result observable quickly. This is a mechanism test, not proof
of the real production disconnect cause or a production agent build.
See https://learn.microsoft.com/dotnet/fundamentals/networking/websockets .
