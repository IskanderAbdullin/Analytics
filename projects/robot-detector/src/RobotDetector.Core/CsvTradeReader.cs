using System.Globalization;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;

namespace RobotDetector.Core;

/// <summary>
/// Strict line-oriented reader for public T-Invest trade-history CSV and local fixtures.
/// Uses invariant decimal numbers and UTC timestamps. It deliberately does not interpret
/// DIRECTION as a passive-order or participant side.
/// </summary>
public static class CsvTradeReader
{
    private const int MaximumBadRowsKept = 1000;

    public static TradeImportResult Read(string path, int maximumRows = 1_000_000)
    {
        if (maximumRows < 1) throw new ArgumentOutOfRangeException(nameof(maximumRows));
        using var source = File.OpenRead(path);
        var fileSha256 = Convert.ToHexString(SHA256.HashData(source)).ToLowerInvariant();
        source.Position = 0;
        if (source.Length > 1_000_000_000)
            throw new InvalidDataException("Input exceeds 1 GB safety bound.");

        Stream data = source;
        ZipArchive? archive = null;
        try
        {
            if (path.EndsWith(".zip", StringComparison.OrdinalIgnoreCase))
            {
                archive = new ZipArchive(source, ZipArchiveMode.Read, leaveOpen: true);
                var entries = archive.Entries.Where(e => e.FullName.EndsWith(".csv", StringComparison.OrdinalIgnoreCase)).ToList();
                if (entries.Count != 1)
                    throw new InvalidDataException("Expected exactly one CSV entry in archive.");
                if (entries[0].Length > 1_000_000_000)
                    throw new InvalidDataException("Uncompressed CSV exceeds 1 GB bound.");
                data = entries[0].Open();
            }
            using var reader = new StreamReader(data, Encoding.UTF8, detectEncodingFromByteOrderMarks: true, leaveOpen: true);
            var header = reader.ReadLine() ?? throw new InvalidDataException("Missing CSV header.");
            header = header.TrimStart('\uFEFF');
            var separator = header.Contains(';') && !header.Contains(',') ? ';' : ',';
            var headers = SplitCsv(header, separator);
            var lookup = headers.Select((name, index) => (name: name.Trim().ToUpperInvariant(), index))
                .GroupBy(x => x.name).ToDictionary(x => x.Key, x => x.First().index, StringComparer.OrdinalIgnoreCase);

            foreach (var required in new[] { "TRADE_TS", "INSTRUMENT_UID", "DIRECTION", "PRICE", "QUANTITY", "TRADE_SOURCE" })
                if (!lookup.ContainsKey(required) && !(required == "TRADE_TS" && lookup.ContainsKey("EXCHANGE_TIME_UTC")) &&
                    !(required == "QUANTITY" && lookup.ContainsKey("QUANTITY_LOTS")) &&
                    !(required == "DIRECTION" && lookup.ContainsKey("REPORTED_DIRECTION")) &&
                    !(required == "PRICE" && lookup.ContainsKey("PRICE_DECIMAL")))
                    throw new InvalidDataException($"Missing mandatory trade column: {required}.");

            string Get(string[] fields, params string[] names)
            {
                foreach (var name in names)
                    if (lookup.TryGetValue(name, out int index) && index < fields.Length)
                        return fields[index].Trim();
                return "";
            }

            var trades = new List<MarketTrade>();
            var badRows = new List<BadRow>();
            long line = 1;
            int badCount = 0;
            while (reader.ReadLine() is { } raw)
            {
                line++;
                if (string.IsNullOrWhiteSpace(raw)) continue;
                if (trades.Count + badCount >= maximumRows)
                    throw new InvalidDataException($"Row limit ({maximumRows}) reached; filter input explicitly.");

                try
                {
                    var fields = SplitCsv(raw, separator);
                    if (fields.Length != headers.Length)
                        throw new FormatException("Unexpected number of CSV columns.");

                    string tsText = Get(fields, "TRADE_TS", "EXCHANGE_TIME_UTC");
                    if (!DateTimeOffset.TryParse(tsText, CultureInfo.InvariantCulture,
                            DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var ts) ||
                        !(tsText.EndsWith("Z", StringComparison.OrdinalIgnoreCase) || tsText.Contains('+') ||
                          (tsText.Length > 10 && tsText[10..].Contains('-'))))
                        throw new FormatException("Time must be an explicit UTC/offset timestamp.");

                    string uid = Get(fields, "INSTRUMENT_UID");
                    string side = Get(fields, "DIRECTION", "REPORTED_DIRECTION").ToUpperInvariant();
                    string sourceName = Get(fields, "TRADE_SOURCE").ToUpperInvariant();
                    if (uid.Length == 0) throw new FormatException("Missing instrument UID.");
                    if (side is not ("BUY" or "SELL" or "UNKNOWN"))
                        throw new FormatException("Unsupported direction; use BUY/SELL/UNKNOWN.");
                    if (sourceName is not ("EXCHANGE" or "DEALER" or "UNKNOWN"))
                        throw new FormatException("Unsupported trade source.");
                    if (!decimal.TryParse(Get(fields, "PRICE", "PRICE_DECIMAL"), NumberStyles.Number,
                            CultureInfo.InvariantCulture, out var price) || price <= 0)
                        throw new FormatException("Invalid positive decimal price.");
                    if (!long.TryParse(Get(fields, "QUANTITY", "QUANTITY_LOTS"), NumberStyles.None,
                            CultureInfo.InvariantCulture, out var lots) || lots <= 0)
                        throw new FormatException("Invalid positive integer lots.");
                    var eventId = Get(fields, "EVENT_ID");
                    if (eventId.Length == 0) eventId = $"{fileSha256[..16]}:{line}";
                    var ticker = Get(fields, "TICKER_CC", "TICKER");
                    var tradingMode = Get(fields, "TRADING_MODE");
                    if (tradingMode.Length == 0) tradingMode = "UNSPECIFIED";
                    var sessionId = Get(fields, "SESSION_ID");
                    if (sessionId.Length == 0) sessionId = ts.UtcDateTime.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
                    var dataKind = Get(fields, "FIXTURE_TYPE", "DATA_KIND");
                    if (dataKind.Length == 0) dataKind = "HISTORICAL_PUBLIC";
                    trades.Add(new MarketTrade(eventId, ts, uid, ticker, sourceName, side, price,
                        lots, tradingMode, sessionId, dataKind, line));
                }
                catch (Exception ex) when (ex is FormatException or ArgumentException or OverflowException)
                {
                    badCount++;
                    if (badRows.Count < MaximumBadRowsKept)
                        badRows.Add(new BadRow(line, ex.Message, raw[..Math.Min(180, raw.Length)]));
                }
            }

            trades.Sort((a, b) =>
            {
                int byTime = a.ExchangeTimeUtc.CompareTo(b.ExchangeTimeUtc);
                return byTime != 0 ? byTime : a.ArrivalSequence.CompareTo(b.ArrivalSequence);
            });

            // Archive completeness is not known from successful file parsing alone.
            return new TradeImportResult(trades, badRows, Path.GetFileName(path), fileSha256, false);
        }
        finally
        {
            archive?.Dispose();
        }
    }

    private static string[] SplitCsv(string line, char separator)
    {
        var fields = new List<string>();
        var value = new StringBuilder();
        bool quoted = false;
        for (int i = 0; i < line.Length; i++)
        {
            char c = line[i];
            if (c == '"')
            {
                if (quoted && i + 1 < line.Length && line[i + 1] == '"')
                {
                    value.Append('"');
                    i++;
                }
                else quoted = !quoted;
            }
            else if (c == separator && !quoted)
            {
                fields.Add(value.ToString());
                value.Clear();
            }
            else value.Append(c);
        }
        if (quoted) throw new FormatException("Unclosed CSV quote.");
        fields.Add(value.ToString());
        return fields.ToArray();
    }
}
