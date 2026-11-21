using System.Globalization;

namespace RobotDetector.Core;

/// <summary>
/// Public-only experimental volume response, useful for studying candidate
/// POV-like flow. It does NOT identify any order, algorithm, or participant.
/// All predictors for bin t are derived from completed bin t-1.
/// </summary>
public sealed class VolumeResponseConfig
{
    public int BinSeconds { get; init; } = 30;
    public int MinimumAdjacentPairs { get; init; } = 8;
    public int MaxPopulatedBinsPerGroup { get; init; } = 10000;

    public void Validate()
    {
        if (BinSeconds is < 1 or > 3600 ||
            MinimumAdjacentPairs is < 3 or > 10000 ||
            MaxPopulatedBinsPerGroup < MinimumAdjacentPairs + 1 ||
            MaxPopulatedBinsPerGroup > 200000)
            throw new ArgumentException("Invalid bounded public volume response settings.");
    }
}

public sealed record VolumeResponseSide(
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string TradingMode,
    string SessionId,
    string DataKind,
    string ReportedDirection,
    string FirstBinStartUtc,
    string LastBinStartUtc,
    int PublicPrintsForSide,
    long ObservedLotsForSide,
    int PopulatedClockBins,
    int EligibleAdjacentPairs,
    int UnobservedClockTransitions,
    double? SpearmanPreviousMarketLotsToCurrentSideLots,
    double? MedianCurrentSideLotsOverPreviousMarketLots,
    bool SufficientAdjacentPairs,
    bool OwnerIdentityKnown,
    bool SignificanceCalibrated,
    string Interpretation
);

public sealed record VolumeResponseObservation(
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string TradingMode,
    string SessionId,
    string DataKind,
    string PreviousBinStartUtc,
    string CurrentBinStartUtc,
    long PreviousTotalMarketLots,
    long CurrentReportedBuyLots,
    long CurrentReportedSellLots,
    long CurrentTotalMarketLots,
    int CurrentPublicPrints
);

public sealed record VolumeResponseReport(
    string SchemaVersion,
    string SourceSha256,
    int InputPublicPrints,
    int EvaluatedSourceGroups,
    int SkippedDenseGroups,
    int BinSeconds,
    bool PhysicalBotCountKnown,
    bool StatisticalSignificanceEstablished,
    bool SourceCoverageVerified,
    IReadOnlyList<VolumeResponseSide> SideProfiles,
    IReadOnlyList<VolumeResponseObservation> Observations,
    IReadOnlyList<string> Warnings
);

public static class VolumeResponseResearch
{
    private sealed class Bin
    {
        public int PublicPrints;
        public long TotalLots;
        public int BuyPrints;
        public int SellPrints;
        public long BuyLots;
        public long SellLots;
    }

    public static VolumeResponseReport Describe(
        TradeImportResult source, VolumeResponseConfig? config = null)
    {
        config ??= new VolumeResponseConfig();
        config.Validate();
        var profiles = new List<VolumeResponseSide>();
        var observations = new List<VolumeResponseObservation>();
        if (source.Trades.Select(x => x.EventId).Distinct(StringComparer.Ordinal).Count()
            != source.Trades.Count)
            throw new InvalidDataException("Duplicate public event IDs prevent independent print accounting.");
        var warnings = new List<string>
        {
            "DESCRIPTIVE_ONLY: volume association is not a detected VWAP/POV parent order or an identified physical trader.",
            "PAST_ONLY_EXPOSURE: predictors are from the prior completed bin; current-bin side volume is only an observed outcome.",
            "MARKET_WIDE_CONFOUND: background flow autocorrelation, session clocks and liquidity cycles may mimic participation.",
            "NO_FEED_COMPLETENESS: a missing populated bin is not assumed to have zero market volume.",
            "DIRECTION_SEMANTICS: provider reported BUY/SELL may not identify the aggressor or passive side.",
            "NO_MULTIPLE_TESTING_CALIBRATION: descriptive Spearman rho is not a p-value or real-market specificity.",
            "NO_ORDER_API: public prints only; no agent identifiers, account data, or trading operations."
        };
        if (source.RejectedRowTotal != 0)
            warnings.Add("REJECTED_ROWS: source parsing rejected records.");
        if (source.Trades.Any(x => x.ReportedDirection == "UNKNOWN"))
            warnings.Add("UNKNOWN_DIRECTION: unknown public prints contribute to total exposure but not reported-side outcomes.");
        if (!source.HasVerifiedFeedCoverage)
            warnings.Add("COVERAGE_UNVERIFIED: missing archive segments cannot be treated as quiet bins.");

        int groups = 0, skipped = 0;
        foreach (var group in source.Trades
            .GroupBy(t => (t.InstrumentUid, t.Ticker, t.TradeSource,
                           t.TradingMode, t.SessionId, t.DataKind))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal)
            .ThenBy(g => g.Key.DataKind, StringComparer.Ordinal))
        {
            var bins = new SortedDictionary<long, Bin>();
            foreach (var trade in group)
            {
                if (trade.QuantityLots <= 0)
                    throw new InvalidDataException("Non-positive public print quantity.");
                long ordinal = trade.ExchangeTimeUtc.ToUnixTimeSeconds() / config.BinSeconds;
                if (!bins.TryGetValue(ordinal, out var bin))
                {
                    bin = new Bin();
                    bins.Add(ordinal, bin);
                }
                checked
                {
                    bin.PublicPrints++;
                    bin.TotalLots += trade.QuantityLots;
                    if (trade.ReportedDirection == "BUY")
                    {
                        bin.BuyPrints++;
                        bin.BuyLots += trade.QuantityLots;
                    }
                    else if (trade.ReportedDirection == "SELL")
                    {
                        bin.SellPrints++;
                        bin.SellLots += trade.QuantityLots;
                    }
                }
            }
            if (bins.Count == 0) continue;
            groups++;
            if (bins.Count > config.MaxPopulatedBinsPerGroup)
            {
                skipped++;
                warnings.Add($"OVERSIZE_GROUP_NOT_EVALUATED: uid={group.Key.InstrumentUid}; " +
                    $"source={group.Key.TradeSource}; session={group.Key.SessionId}; " +
                    $"populatedBins={bins.Count}; max={config.MaxPopulatedBinsPerGroup}.");
                continue;
            }

            var series = bins.ToArray();
            int nonadjacent = 0;
            var pairs = new List<(Bin Previous, Bin Current)>();
            for (int i = 1; i < series.Length; i++)
            {
                if (series[i].Key - series[i - 1].Key == 1)
                {
                    var previous = series[i - 1].Value;
                    var current = series[i].Value;
                    pairs.Add((previous, current));
                    // The exposure is from the previous *completed* public
                    // bin; never join with future volume or private truth.
                    observations.Add(new VolumeResponseObservation(
                        group.Key.InstrumentUid, group.Key.Ticker,
                        group.Key.TradeSource, group.Key.TradingMode,
                        group.Key.SessionId, group.Key.DataKind,
                        BinStart(series[i - 1].Key, config.BinSeconds),
                        BinStart(series[i].Key, config.BinSeconds),
                        previous.TotalLots, current.BuyLots, current.SellLots,
                        current.TotalLots, current.PublicPrints));
                }
                else nonadjacent++;
            }

            string first = BinStart(series[0].Key, config.BinSeconds);
            string last = BinStart(series[^1].Key, config.BinSeconds);
            foreach (string direction in new[] { "BUY", "SELL" })
            {
                long lots = 0;
                int prints = 0;
                foreach (var bin in bins.Values)
                {
                    checked
                    {
                        lots += direction == "BUY" ? bin.BuyLots : bin.SellLots;
                        prints += direction == "BUY" ? bin.BuyPrints : bin.SellPrints;
                    }
                }
                var exposure = pairs.Select(p => (double)p.Previous.TotalLots).ToArray();
                var outcome = pairs.Select(p => (double)(
                    direction == "BUY" ? p.Current.BuyLots : p.Current.SellLots)).ToArray();
                bool enough = pairs.Count >= config.MinimumAdjacentPairs;
                double? rho = enough ? Spearman(exposure, outcome) : null;
                var ratios = pairs.Select(p => (double)(
                    direction == "BUY" ? p.Current.BuyLots : p.Current.SellLots) /
                    p.Previous.TotalLots).ToArray();
                profiles.Add(new VolumeResponseSide(
                    group.Key.InstrumentUid, group.Key.Ticker,
                    group.Key.TradeSource, group.Key.TradingMode, group.Key.SessionId,
                    group.Key.DataKind, direction, first, last, prints, lots,
                    series.Length, pairs.Count, nonadjacent, rho,
                    enough ? Median(ratios) : null,
                    enough, false, false,
                    "Public reported-side volume relative to the preceding completed market-volume bin; descriptive association only, not POV execution attribution."));
            }
        }
        return new VolumeResponseReport("0.1-public-lag-volume-response",
            source.FileSha256, source.Trades.Count, groups, skipped,
            config.BinSeconds, false, false, source.HasVerifiedFeedCoverage,
            profiles, observations, warnings);
    }

    private static string BinStart(long ordinal, int seconds) =>
        DateTimeOffset.FromUnixTimeSeconds(checked(ordinal * seconds))
            .ToUniversalTime().ToString("O", CultureInfo.InvariantCulture);

    private static double? Spearman(double[] x, double[] y)
    {
        if (x.Length != y.Length || x.Length < 3)
            return null;
        var xr = Ranks(x);
        var yr = Ranks(y);
        double mean = (x.Length + 1) / 2.0;
        double xx = 0, yy = 0, xy = 0;
        for (int i = 0; i < x.Length; i++)
        {
            double a = xr[i] - mean, b = yr[i] - mean;
            xx += a * a;
            yy += b * b;
            xy += a * b;
        }
        if (xx == 0 || yy == 0) return null;
        return Math.Clamp(xy / Math.Sqrt(xx * yy), -1, 1);
    }

    private static double[] Ranks(double[] values)
    {
        var order = Enumerable.Range(0, values.Length)
            .OrderBy(i => values[i]).ThenBy(i => i).ToArray();
        var result = new double[values.Length];
        for (int i = 0; i < order.Length;)
        {
            int j = i + 1;
            while (j < order.Length && values[order[i]] == values[order[j]]) j++;
            double midRank = ((i + 1) + j) / 2.0;
            for (int k = i; k < j; k++) result[order[k]] = midRank;
            i = j;
        }
        return result;
    }

    private static double? Median(double[] values)
    {
        if (values.Length == 0) return null;
        Array.Sort(values);
        int m = values.Length / 2;
        return values.Length % 2 == 1 ? values[m] : (values[m - 1] + values[m]) / 2.0;
    }
}
