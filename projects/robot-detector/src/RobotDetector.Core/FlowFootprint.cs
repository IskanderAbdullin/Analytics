using System.Globalization;

namespace RobotDetector.Core;

/// <summary>
/// Purely descriptive, dependency-free clock-window features computed from
/// anonymous public trade prints. Neither a bot counter nor trading advice.
/// </summary>
public sealed class FlowFootprintConfig
{
    public int WindowMinutes { get; init; } = 5;
    public int CountBinSeconds { get; init; } = 1;
    public int ClockPhaseThresholdMilliseconds { get; init; } = 100;

    public void Validate()
    {
        if (WindowMinutes is < 1 or > 1440 || CountBinSeconds is < 1 or > 3600 ||
            ClockPhaseThresholdMilliseconds is < 1 or > 500)
            throw new ArgumentException("Invalid trade-flow footprint window or phase parameters.");
    }
}

public sealed record TradeFlowWindow(
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string TradingMode,
    string SessionId,
    string WindowStartUtc,
    string FirstObservedUtc,
    string LastObservedUtc,
    int PublicPrintCount,
    long TotalLots,
    long BuyReportedLots,
    long SellReportedLots,
    long UnknownDirectionLots,
    double? ReportedDirectionImbalance,
    int LongestBuyReportedRun,
    int LongestSellReportedRun,
    double? LagOneReportedSignAgreement,
    double? MedianInterarrivalMs,
    double? InterarrivalCoefficientOfVariation,
    double? PrintCountFanoFactor,
    int IncludedClockBins,
    int NearWholeSecondPrints,
    double NearWholeSecondPrintShare,
    bool HasVerifiedFeedCoverage,
    string Interpretation
);

public sealed record TradeFlowFootprintReport(
    string SchemaVersion,
    string SourceSha256,
    int InputPrints,
    int WindowCount,
    bool ActualBotCountKnown,
    bool StatisticalSignificanceEstablished,
    IReadOnlyList<TradeFlowWindow> Windows,
    IReadOnlyList<string> Warnings,
    int WindowMinutes = 5
);

public static class FlowFootprint
{
    public static TradeFlowFootprintReport Describe(
        TradeImportResult input, FlowFootprintConfig? config = null)
    {
        config ??= new FlowFootprintConfig();
        config.Validate();
        long windowMs = config.WindowMinutes * 60_000L;
        var windows = input.Trades
            .GroupBy(t => (t.InstrumentUid, t.TradeSource,
                t.TradingMode, t.SessionId,
                Window: t.ExchangeTimeUtc.ToUnixTimeMilliseconds() / windowMs))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal)
            .ThenBy(g => g.Key.Window)
            .Select(g => DescribeWindow(g.ToList(), g.Key.Window, windowMs, config,
                input.HasVerifiedFeedCoverage))
            .ToArray();

        return new TradeFlowFootprintReport(
            "0.1-observable-flow", input.FileSha256, input.Trades.Count,
            windows.Length, false, false, windows,
            new[]
            {
                "NOT_BOT_IDENTIFICATION: each window aggregates multiple anonymous market participants.",
                "DIRECTION_IS_PROVIDER_REPORTED: imbalance and sign runs are not verified aggressor or passive order identity.",
                "CLOCK_CONCENTRATION_IS_NOT_BOT: broad market-wide timing can create artificial-looking periodicity.",
                "FANO_IS_DESCRIPTIVE: print clustering varies with bin width, market regime and feed gaps.",
                input.HasVerifiedFeedCoverage
                    ? "COVERAGE_FLAG_FROM_SOURCE: verify scope of claimed feed completeness independently."
                    : "UNVERIFIED_FEED_COVERAGE: missing prints and exchange halts cannot be distinguished from inactive windows.",
                "READ_ONLY: no trading APIs, orders, account data or owner IDs."
            }, config.WindowMinutes);
    }

    private static TradeFlowWindow DescribeWindow(
        List<MarketTrade> rows, long windowOrdinal, long windowMs,
        FlowFootprintConfig config, bool verifiedCoverage)
    {
        rows.Sort((a, b) =>
        {
            int cmp = a.ExchangeTimeUtc.CompareTo(b.ExchangeTimeUtc);
            return cmp != 0 ? cmp : a.ArrivalSequence.CompareTo(b.ArrivalSequence);
        });
        var first = rows[0];
        var last = rows[^1];
        long total = 0, buy = 0, sell = 0, unknown = 0;
        int nearClock = 0, currentBuyRun = 0, currentSellRun = 0;
        int maxBuyRun = 0, maxSellRun = 0;
        int previousSign = 0, signPairs = 0, signMatches = 0;

        var gaps = new double[Math.Max(0, rows.Count - 1)];
        long binMillis = config.CountBinSeconds * 1000L;
        long firstBin = first.ExchangeTimeUtc.ToUnixTimeMilliseconds() / binMillis;
        long lastBin = last.ExchangeTimeUtc.ToUnixTimeMilliseconds() / binMillis;
        var countsPerBin = new Dictionary<long, int>();

        for (int i = 0; i < rows.Count; i++)
        {
            var t = rows[i];
            long q = t.QuantityLots;
            if (q <= 0) throw new InvalidDataException("Nonpositive public print quantity.");
            total = checked(total + q);
            int sign = t.ReportedDirection switch { "BUY" => 1, "SELL" => -1, _ => 0 };
            if (sign == 1)
            {
                buy = checked(buy + q);
                maxBuyRun = Math.Max(maxBuyRun, ++currentBuyRun);
                currentSellRun = 0;
            }
            else if (sign == -1)
            {
                sell = checked(sell + q);
                maxSellRun = Math.Max(maxSellRun, ++currentSellRun);
                currentBuyRun = 0;
            }
            else
            {
                unknown = checked(unknown + q);
                currentBuyRun = currentSellRun = 0;
            }

            if (previousSign != 0 && sign != 0)
            {
                signPairs++;
                if (previousSign == sign) signMatches++;
            }
            previousSign = sign;
            long timestampMs = t.ExchangeTimeUtc.ToUnixTimeMilliseconds();
            if ((timestampMs % 1000 + 1000) % 1000 < config.ClockPhaseThresholdMilliseconds)
                nearClock++;
            long bin = timestampMs / binMillis;
            countsPerBin[bin] = countsPerBin.GetValueOrDefault(bin) + 1;

            if (i > 0)
                gaps[i - 1] = (t.ExchangeTimeUtc - rows[i - 1].ExchangeTimeUtc).TotalMilliseconds;
        }

        double? imbalance = buy + sell == 0 ? null : (double)(buy - sell) / (buy + sell);
        double? agreement = signPairs == 0 ? null : (double)signMatches / signPairs;
        double? medianMs = null, gapCv = null;
        if (gaps.Length > 0)
        {
            Array.Sort(gaps);
            medianMs = gaps.Length % 2 == 1 ? gaps[gaps.Length / 2]
                : (gaps[gaps.Length / 2 - 1] + gaps[gaps.Length / 2]) / 2;
            double meanGap = gaps.Average();
            if (meanGap > 0)
            {
                double variance = gaps.Average(x => (x - meanGap) * (x - meanGap));
                gapCv = Math.Sqrt(variance) / meanGap;
            }
        }

        // Include unoccupied bins between the *first* and *last* observed
        // public prints, NOT an invented complete exchange trading session.
        // sum(x^2)/N - N/B == population variance(x) / mean(x).
        long numBins = lastBin - firstBin + 1;
        double fano = 0;
        if (numBins > 1)
        {
            double sumSquares = countsPerBin.Values.Sum(n => (double)n * n);
            fano = Math.Max(0, sumSquares / rows.Count - (double)rows.Count / numBins);
        }
        string windowStart = DateTimeOffset.FromUnixTimeMilliseconds(
            checked(windowOrdinal * windowMs)).ToUniversalTime().ToString("O",
            CultureInfo.InvariantCulture);

        return new TradeFlowWindow(
            first.InstrumentUid, first.Ticker, first.TradeSource,
            first.TradingMode, first.SessionId, windowStart,
            first.ExchangeTimeUtc.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
            last.ExchangeTimeUtc.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
            rows.Count, total, buy, sell, unknown,
            imbalance, maxBuyRun, maxSellRun, agreement,
            medianMs, gapCv, numBins > 1 ? fano : null, checked((int)Math.Min(numBins, int.MaxValue)),
            nearClock, (double)nearClock / rows.Count,
            verifiedCoverage,
            "Observable public print flow only; cannot identify an individual trading robot.");
    }
}
