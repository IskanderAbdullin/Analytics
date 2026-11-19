using System.Globalization;

namespace RobotDetector.Core;

/// <summary>
/// Read-only, observable market-activity windows compared strictly against
/// prior populated, contiguous clock windows of the same source/session.
/// This is NOT a bot counter, order-identification model, or trading signal.
/// </summary>
public sealed class FlowActivityConfig
{
    public int ReferenceWindows { get; init; } = 4;
    public int MinimumPrintCount { get; init; } = 10;
    public double MinimumCountRatio { get; init; } = 3;
    public double MinimumLotRatio { get; init; } = 3;
    public double MinimumAbsoluteReportedImbalance { get; init; } = 0.6;

    public void Validate()
    {
        if (ReferenceWindows is < 2 or > 100 ||
            MinimumPrintCount < 1 ||
            MinimumCountRatio <= 1 || MinimumLotRatio <= 1 ||
            MinimumAbsoluteReportedImbalance is < 0 or > 1)
            throw new ArgumentException("Invalid observable activity episode settings.");
    }
}

public sealed record ObservedHighActivityWindow(
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string TradingMode,
    string SessionId,
    string WindowStartUtc,
    int PublicPrintCount,
    long TotalLots,
    double ReportedDirectionImbalance,
    double BaselineMedianPrintCount,
    double BaselineMedianLots,
    double PrintCountRatio,
    double TotalLotsRatio,
    string Label,
    string State,
    bool ActorIdentityKnown
);

public sealed record FlowActivityEpisodeReport(
    string SchemaVersion,
    string SourceSha256,
    int InputPrints,
    int InputPopulatedWindows,
    int EvaluatedWindows,
    int UnscorableWarmupOrGapWindows,
    int ActivityWindowCount,
    bool ActualBotCountKnown,
    bool SignificanceCalibrated,
    IReadOnlyList<ObservedHighActivityWindow> ActivityWindows,
    IReadOnlyList<string> Warnings
);

public static class FlowActivityEpisodes
{
    public static FlowActivityEpisodeReport Find(
        TradeFlowFootprintReport summary, FlowActivityConfig? config = null)
    {
        config ??= new FlowActivityConfig();
        config.Validate();
        if (summary.WindowCount != summary.Windows.Count)
            throw new InvalidDataException("Public window summary count differs from actual windows.");
        if (summary.InputPrints != summary.Windows.Sum(x => x.PublicPrintCount))
            throw new InvalidDataException("Public footprint lost or duplicated print counts.");
        var selected = new List<ObservedHighActivityWindow>();
        int evaluated = 0, warmup = 0;
        long windowTicks = checked((long)summary.WindowMinutes * TimeSpan.TicksPerMinute);
        if (summary.WindowMinutes is < 1 or > 1440)
            throw new InvalidDataException("Invalid source footprint window width.");

        var groups = summary.Windows.GroupBy(w =>
                (w.InstrumentUid, w.TradeSource, w.TradingMode, w.SessionId))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal);

        foreach (var group in groups)
        {
            var prior = new Queue<TradeFlowWindow>(config.ReferenceWindows);
            DateTimeOffset? previousStart = null;
            foreach (var w in group.OrderBy(w => w.WindowStartUtc, StringComparer.Ordinal))
            {
                var start = DateTimeOffset.Parse(w.WindowStartUtc,
                    CultureInfo.InvariantCulture, DateTimeStyles.AdjustToUniversal);
                if (previousStart.HasValue)
                {
                    long actualGap = (start - previousStart.Value).Ticks;
                    if (actualGap != windowTicks)
                        prior.Clear(); // A missing clock window is not a quiet zero-print window.
                }
                previousStart = start;

                if (prior.Count == config.ReferenceWindows)
                {
                    evaluated++;
                    double typicalPrints = Median(prior.Select(x => (double)x.PublicPrintCount));
                    double typicalLots = Median(prior.Select(x => (double)x.TotalLots));
                    double countRatio = typicalPrints > 0
                        ? w.PublicPrintCount / typicalPrints : 0;
                    double lotRatio = typicalLots > 0
                        ? w.TotalLots / typicalLots : 0;

                    if (w.PublicPrintCount >= config.MinimumPrintCount &&
                        countRatio >= config.MinimumCountRatio &&
                        lotRatio >= config.MinimumLotRatio &&
                        w.ReportedDirectionImbalance.HasValue &&
                        Math.Abs(w.ReportedDirectionImbalance.Value) >=
                            config.MinimumAbsoluteReportedImbalance)
                    {
                        string label = w.ReportedDirectionImbalance.Value > 0
                            ? "reported_buy_dominant_high_activity"
                            : "reported_sell_dominant_high_activity";
                        selected.Add(new ObservedHighActivityWindow(
                            w.InstrumentUid, w.Ticker, w.TradeSource, w.TradingMode,
                            w.SessionId, w.WindowStartUtc, w.PublicPrintCount,
                            w.TotalLots, w.ReportedDirectionImbalance.Value,
                            typicalPrints, typicalLots, countRatio, lotRatio,
                            label, "unvalidated_observed_activity", false));
                    }
                }
                else warmup++;

                prior.Enqueue(w);
                if (prior.Count > config.ReferenceWindows) prior.Dequeue();
            }
        }

        return new FlowActivityEpisodeReport(
            "0.1-observable-activity", summary.SourceSha256, summary.InputPrints,
            summary.WindowCount, evaluated, warmup, selected.Count,
            false, false, selected,
            new[]
            {
                "ACTIVITY_NOT_BOT: this labels aggregated anonymous print windows, not actual programs or owner IDs.",
                "HISTORICAL_BASELINE_ONLY: current window is compared only with previous contiguous windows of the same source/session/mode.",
                "MISSING_WINDOW_RESETS_BASELINE: absence of a public window is not proof of market inactivity.",
                "DIRECTION_IS_PROVIDER_REPORTED: buy/sell imbalance does not prove passive or aggressor side.",
                "UNCALIBRATED_THRESHOLDS: count/lot ratios and imbalance are research heuristics, not significance or profitability.",
                "BURST_CONFONDER: auctions, news, market-wide synchronized trading and feed anomalies can all trigger the same label.",
                "RELEASE_GATE_CLOSED: must validate on independent dates/instruments with better null models before emitting live alerts."
            });
    }

    private static double Median(IEnumerable<double> xs)
    {
        double[] v = xs.OrderBy(x => x).ToArray();
        if (v.Length == 0) throw new InvalidOperationException("Empty reference windows.");
        return v.Length % 2 == 1 ? v[v.Length / 2] :
            (v[v.Length / 2 - 1] + v[v.Length / 2]) / 2;
    }
}
