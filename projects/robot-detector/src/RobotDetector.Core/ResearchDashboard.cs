using System.Globalization;
using System.Net;
using System.Text;

namespace RobotDetector.Core;

/// <summary>
/// Standalone, offline, read-only window-level market research report.
/// Uses observable anonymous public prints; no signal, account or owner claims.
/// </summary>
public sealed record ResearchDashboardGroup(
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string TradingMode,
    string SessionId,
    int PublicPrints,
    long ObservedLots,
    int PopulatedWindows,
    int ElevatedActivityWindows,
    int PrintsSharingTimestamp,
    double TimestampCollisionShare,
    double? MedianFanoFactor,
    bool FeedCoverageVerified
);

public sealed record ResearchDashboardWindow(
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string TradingMode,
    string SessionId,
    string WindowStartUtc,
    int PublicPrints,
    long ObservedLots,
    double? ReportedDirectionImbalance,
    double? PrintCountFanoFactor,
    double NearWholeSecondPrintShare,
    bool ElevatedActivityObserved
);

public sealed record ResearchDashboardReport(
    string SchemaVersion,
    string SourceSha256,
    string SourceFileName,
    string DataKind,
    int PublicPrints,
    int RejectedRows,
    long ObservedLots,
    int DistinctInstruments,
    int PopulatedWindows,
    int EvaluatedActivityWindows,
    int ElevatedActivityWindows,
    int PrintsSharingTimestamp,
    bool FeedCoverageVerified,
    bool ActualBotCountKnown,
    bool StatisticalSignificanceEstablished,
    IReadOnlyList<ResearchDashboardGroup> Groups,
    IReadOnlyList<ResearchDashboardWindow> Windows,
    IReadOnlyList<string> Warnings
);

public static class ResearchDashboard
{
    public static ResearchDashboardReport Build(TradeImportResult input, int windowMinutes = 5)
    {
        if (windowMinutes is < 1 or > 1440)
            throw new ArgumentOutOfRangeException(nameof(windowMinutes));
        var flow = FlowFootprint.Describe(input, new FlowFootprintConfig
        {
            WindowMinutes = windowMinutes,
            CountBinSeconds = 1
        });
        var activity = FlowActivityEpisodes.Find(flow);
        var quality = TimestampQualityAudit.Describe(input);

        if (flow.InputPrints != input.Trades.Count ||
            quality.SourcePrints != input.Trades.Count ||
            activity.InputPrints != input.Trades.Count)
            throw new InvalidDataException("Independent analytics have inconsistent print totals.");

        var byGroupQuality = quality.Groups.ToDictionary(g =>
            (g.InstrumentUid, g.TradeSource, g.TradingMode, g.SessionId));
        var elevatedKeys = activity.ActivityWindows.Select(a =>
                (a.InstrumentUid, a.TradeSource, a.TradingMode,
                    a.SessionId, a.WindowStartUtc))
            .ToHashSet();

        var groups = flow.Windows
            .GroupBy(w => (w.InstrumentUid, w.TradeSource, w.TradingMode, w.SessionId))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal)
            .Select(g =>
            {
                if (!byGroupQuality.TryGetValue(g.Key, out var timestamp))
                    throw new InvalidDataException("Missing timestamp-quality group.");
                var windows = g.ToArray();
                int count = windows.Sum(w => w.PublicPrintCount);
                if (timestamp.PublicPrintCount != count)
                    throw new InvalidDataException("Timestamp and flow group print counts differ.");
                var fanos = windows.Where(w => w.PrintCountFanoFactor.HasValue)
                    .Select(w => w.PrintCountFanoFactor!.Value)
                    .OrderBy(v => v).ToArray();
                double? median = fanos.Length == 0 ? null :
                    fanos.Length % 2 == 1 ? fanos[fanos.Length / 2] :
                    (fanos[fanos.Length / 2 - 1] + fanos[fanos.Length / 2]) / 2;
                return new ResearchDashboardGroup(
                    g.Key.InstrumentUid, windows[0].Ticker,
                    g.Key.TradeSource, g.Key.TradingMode, g.Key.SessionId,
                    count, windows.Sum(w => w.TotalLots), windows.Length,
                    windows.Count(w => elevatedKeys.Contains(
                        (w.InstrumentUid, w.TradeSource, w.TradingMode,
                         w.SessionId, w.WindowStartUtc))),
                    timestamp.PrintsInSameTimestampClusters,
                    timestamp.SameTimestampClusterPrintShare,
                    median, input.HasVerifiedFeedCoverage);
            }).ToArray();

        var windowsForDisplay = flow.Windows
            .OrderBy(w => w.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(w => w.TradeSource, StringComparer.Ordinal)
            .ThenBy(w => w.TradingMode, StringComparer.Ordinal)
            .ThenBy(w => w.SessionId, StringComparer.Ordinal)
            .ThenBy(w => w.WindowStartUtc, StringComparer.Ordinal)
            .Select(w => new ResearchDashboardWindow(
                w.InstrumentUid, w.Ticker, w.TradeSource, w.TradingMode,
                w.SessionId, w.WindowStartUtc, w.PublicPrintCount,
                w.TotalLots, w.ReportedDirectionImbalance, w.PrintCountFanoFactor,
                w.NearWholeSecondPrintShare,
                elevatedKeys.Contains((w.InstrumentUid, w.TradeSource,
                    w.TradingMode, w.SessionId, w.WindowStartUtc))))
            .ToArray();

        long lots = groups.Sum(g => g.ObservedLots);
        int sharedTimestamps = groups.Sum(g => g.PrintsSharingTimestamp);
        if (groups.Sum(g => g.PublicPrints) != input.Trades.Count ||
            windowsForDisplay.Sum(w => w.PublicPrints) != input.Trades.Count ||
            groups.Sum(g => g.ElevatedActivityWindows) != activity.ActivityWindowCount)
            throw new InvalidDataException("Research dashboard lost source event cardinality.");

        var kinds = input.Trades.Select(x => x.DataKind).Distinct(StringComparer.Ordinal).Take(2).ToArray();
        string kind = kinds.Length switch { 0 => "EMPTY", 1 => kinds[0], _ => "MIXED" };
        return new ResearchDashboardReport(
            "0.1-standalone-observable", input.FileSha256,
            Path.GetFileName(input.FileName), kind, input.Trades.Count,
            input.RejectedRowTotal, lots,
            groups.Select(x => x.InstrumentUid).Distinct(StringComparer.Ordinal).Count(),
            flow.WindowCount, activity.EvaluatedWindows, activity.ActivityWindowCount,
            sharedTimestamps,
            input.HasVerifiedFeedCoverage, false, false,
            groups, windowsForDisplay,
            new[]
            {
                "OBSERVABLE_DATA_ONLY: summary aggregates anonymous prints, not identified robots or parent orders.",
                "NO_TRADING_SIGNALS: historical cadence forecasting has not demonstrated independent predictive advantage.",
                "WINDOWS_NOT_MARKET_SESSION: inactive/missing 5-minute windows are NOT zero-print evidence.",
                "DIRECTION_PROVIDER_REPORTED: does not identify the aggressive/passive participant.",
                "TIMESTAMP_COLLISIONS_NOT_DUPLICATES: counts do not establish individual order identity.",
                input.HasVerifiedFeedCoverage
                    ? "COVERAGE_FLAG_CAME_FROM_INPUT: verify feed scope independently."
                    : "UNVERIFIED_COVERAGE: a successfully parsed archive does not prove a complete exchange feed.",
                "READ_ONLY_OFFLINE: this report makes no network, account or order API calls."
            });
    }

    public static string ToStandaloneHtml(ResearchDashboardReport report, int maximumVisibleWindows = 240)
    {
        if (maximumVisibleWindows is < 1 or > 5000)
            throw new ArgumentOutOfRangeException(nameof(maximumVisibleWindows));
        if (report.PublicPrints != report.Groups.Sum(g => g.PublicPrints) ||
            report.PublicPrints != report.Windows.Sum(w => w.PublicPrints) ||
            report.PopulatedWindows != report.Windows.Count ||
            report.ElevatedActivityWindows != report.Windows.Count(w => w.ElevatedActivityObserved))
            throw new InvalidDataException("Dashboard data integrity failed.");

        static string E(string? s) => WebUtility.HtmlEncode(s ?? "");
        static string N(long n) => n.ToString("N0", CultureInfo.InvariantCulture);
        static string P(double? v) => v.HasValue
            ? v.Value.ToString("0.###", CultureInfo.InvariantCulture) : "—";
        var sb = new StringBuilder(16384);
        sb.AppendLine("<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\">");
        sb.AppendLine("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">");
        sb.AppendLine("<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; form-action 'none'; base-uri 'none'\">");
        sb.AppendLine("<title>Robot Detector — наблюдаемые рыночные данные</title>");
        sb.AppendLine("<style>body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:#101827;color:#eef3f9;margin:0;line-height:1.5}main{max-width:1100px;margin:auto;padding:32px 20px}h1{font-size:1.65rem;margin-bottom:0}h2{font-size:1.2rem;margin-top:2.2rem}small,.muted{color:#a3b2c8}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin:20px 0}.metric{border:1px solid #34445b;background:#1a2639;border-radius:12px;padding:16px}.metric strong{font-size:1.55rem;display:block}.notice{border-left:3px solid #9eabbc;padding:12px 16px;background:#202c40;margin:18px 0}.scroll{overflow-x:auto;border:1px solid #34445b;border-radius:10px}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:9px 10px;border-bottom:1px solid #34445b;text-align:left;white-space:nowrap;font-size:.86rem}th{background:#1b2940;color:#d0dbe9}tbody tr:nth-child(even){background:#172237}.barbg{height:8px;background:#293955;border-radius:4px;width:100px}.bar{height:8px;background:#80b4ed;border-radius:4px}.activity{font-weight:600}.foot{margin-top:30px;font-size:.8rem;overflow-wrap:anywhere}@media print{body{background:white;color:#202020}.metric,.notice,th{background:#f2f4f7;color:#202020}.scroll{border:0}.barbg{background:#ddd}.bar{background:#444}}</style></head><body><main>");
        sb.AppendLine("<h1>Robot Detector · обзор рыночного потока</h1>");
        sb.Append("<p class=\"muted\">Источник: <strong>").Append(E(report.SourceFileName))
            .Append("</strong> · ").Append(E(report.DataKind)).Append("</p>\n");
        sb.AppendLine("<div class=\"notice\"><strong>Исследовательский отчёт, не торговый сигнал.</strong> Показаны только агрегированные обезличенные сделки. Количество реальных торговых роботов и владельцев <strong>неизвестно</strong>; уверенность обнаружений не откалибрована.</div>");
        sb.AppendLine("<section class=\"metrics\">");
        Metric("Сделок",N(report.PublicPrints));
        Metric("Лотов",N(report.ObservedLots));
        Metric("Инструментов",N(report.DistinctInstruments));
        Metric("5-минутных окон",N(report.PopulatedWindows));
        Metric("Всплесков активности",N(report.ElevatedActivityWindows));
        Metric("Сделок с совпадающим временем",N(report.PrintsSharingTimestamp));
        sb.AppendLine("</section>");
        sb.Append("<p class=\"muted\">Полнота ленты: ")
            .Append(report.FeedCoverageVerified ? "заявлена источником (область не проверена)" : "не подтверждена")
            .Append(". Отбракованных строк: ").Append(N(report.RejectedRows)).Append(".</p>\n");
        sb.AppendLine("<h2>Сравнение инструментов и источников</h2><div class=\"scroll\"><table><thead><tr><th>Тикер</th><th>UID</th><th>Источник</th><th>Режим</th><th>Сессия</th><th>Сделок</th><th>Лотов</th><th>Окон</th><th>Всплесков</th><th>Совпадающие timestamps</th><th>Медиана Fano</th></tr></thead><tbody>");
        foreach (var g in report.Groups)
            sb.Append("<tr><td>").Append(E(g.Ticker)).Append("</td><td>").Append(E(g.InstrumentUid))
                .Append("</td><td>").Append(E(g.TradeSource)).Append("</td><td>").Append(E(g.TradingMode))
                .Append("</td><td>").Append(E(g.SessionId)).Append("</td><td>").Append(N(g.PublicPrints))
                .Append("</td><td>").Append(N(g.ObservedLots)).Append("</td><td>").Append(N(g.PopulatedWindows))
                .Append("</td><td>").Append(N(g.ElevatedActivityWindows))
                .Append("</td><td>").Append(P(100 * g.TimestampCollisionShare)).Append("%</td><td>")
                .Append(P(g.MedianFanoFactor)).Append("</td></tr>\n");
        sb.AppendLine("</tbody></table></div>");
        sb.AppendLine("<h2>Почасовая структура · наблюдаемые окна</h2>");
        sb.Append("<p class=\"muted\">Показано не более ").Append(N(maximumVisibleWindows))
            .Append(" самых насыщенных окон по количеству сделок из ").Append(N(report.Windows.Count))
            .Append(". Все окна остаются в JSON-отчёте; отображение не влияет на расчёты.</p>\n");
        sb.AppendLine("<div class=\"scroll\"><table><thead><tr><th>Время UTC</th><th>Тикер</th><th>Источник</th><th>Сделок</th><th>Нагрузка</th><th>Лотов</th><th>Reported imbalance</th><th>Fano</th><th>Всплеск</th></tr></thead><tbody>");
        var ranked = report.Windows.OrderByDescending(w => w.PublicPrints)
            .ThenBy(w => w.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(w => w.WindowStartUtc, StringComparer.Ordinal)
            .Take(maximumVisibleWindows).ToArray();
        int maxPrints = ranked.Length == 0 ? 0 : ranked.Max(x => x.PublicPrints);
        foreach (var w in ranked)
        {
            double fraction = maxPrints == 0 ? 0 : Math.Clamp((double)w.PublicPrints / maxPrints * 100, 0, 100);
            sb.Append("<tr><td>").Append(E(w.WindowStartUtc)).Append("</td><td>").Append(E(w.Ticker))
                .Append("</td><td>").Append(E(w.TradeSource)).Append("</td><td>")
                .Append(N(w.PublicPrints)).Append("</td><td><div class=\"barbg\"><div class=\"bar\" style=\"width:")
                .Append(fraction.ToString("0.##", CultureInfo.InvariantCulture))
                .Append("%\"></div></div></td><td>").Append(N(w.ObservedLots))
                .Append("</td><td>").Append(P(w.ReportedDirectionImbalance))
                .Append("</td><td>").Append(P(w.PrintCountFanoFactor)).Append("</td><td>")
                .Append(w.ElevatedActivityObserved ? "<span class=\"activity\">Наблюдался</span>" : "—")
                .Append("</td></tr>\n");
        }
        sb.AppendLine("</tbody></table></div>");
        sb.AppendLine("<h2>Ограничения интерпретации</h2><ul>");
        foreach (string warning in report.Warnings)
            sb.Append("<li>").Append(E(warning)).Append("</li>\n");
        sb.Append("</ul><p class=\"foot\">SHA-256 источника: <code>").Append(E(report.SourceSha256))
            .Append("</code>. Отчёт полностью автономен: без скриптов, веб-запросов и исходных записей отдельных сделок.</p>");
        sb.AppendLine("</main></body></html>");
        return sb.ToString();

        void Metric(string label, string value) => sb.Append("<div class=\"metric\"><small>")
            .Append(E(label)).Append("</small><strong>").Append(E(value))
            .Append("</strong></div>\n");
    }
}
