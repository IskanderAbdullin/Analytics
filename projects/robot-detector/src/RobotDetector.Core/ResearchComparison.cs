using System.Globalization;
using System.Net;
using System.Text;

namespace RobotDetector.Core;

/// <summary>
/// Multi-file comparative view of anonymous, observational source statistics.
/// Never joins/deduplicates raw trade identities across archives and does not
/// infer independent algorithms or causality from differences in activity.
/// </summary>
public sealed record ResearchComparisonRow(
    string SourceFileName,
    string SourceSha256,
    string DataKind,
    string InstrumentNames,
    string SourceModes,
    int DistinctInstruments,
    int SourceGroups,
    int PublicPrints,
    long ObservedLots,
    int PopulatedWindows,
    int ElevatedActivityWindows,
    double? ActivityShare,
    double? TimestampCollisionShare,
    double? NearWholeSecondPrintShare,
    double? MedianWindowFano,
    bool FeedCoverageVerified
);

public sealed record ResearchComparisonReport(
    string SchemaVersion,
    int InputArchiveCount,
    int WindowMinutes,
    int TotalPublicPrints,
    long TotalObservedLots,
    bool ComparableDataKinds,
    bool SourceCoverageVerified,
    bool ActualBotCountKnown,
    bool StatisticalSignificanceEstablished,
    IReadOnlyList<ResearchComparisonRow> Archives,
    IReadOnlyList<string> Warnings
);

public static class ResearchComparison
{
    public static ResearchComparisonReport Compare(
        IReadOnlyList<ResearchDashboardReport> reports)
    {
        if (reports.Count is < 2 or > 20)
            throw new ArgumentException("Compare between 2 and 20 independently parsed source archives.");

        int width = reports[0].WindowMinutes;
        if (reports.Any(r => r.WindowMinutes != width || width is < 1 or > 1440))
            throw new ArgumentException("All reports must share the same UTC window width.");
        if (reports.Select(r => r.SourceSha256)
                .Distinct(StringComparer.OrdinalIgnoreCase).Count() != reports.Count)
            throw new InvalidDataException("Identical source SHA appears twice; refusing to present it as independent archives.");

        var rows = new List<ResearchComparisonRow>(reports.Count);
        foreach (var report in reports)
        {
            if (report.PublicPrints != report.Groups.Sum(g => g.PublicPrints) ||
                report.PublicPrints != report.Windows.Sum(w => w.PublicPrints) ||
                report.ObservedLots != report.Groups.Sum(g => g.ObservedLots) ||
                report.ObservedLots != report.Windows.Sum(w => w.ObservedLots) ||
                report.PopulatedWindows != report.Windows.Count ||
                report.ElevatedActivityWindows != report.Windows.Count(w => w.ElevatedActivityObserved) ||
                report.ActualBotCountKnown || report.StatisticalSignificanceEstablished)
                throw new InvalidDataException("Inconsistent or unverified source dashboard report.");

            var fano = report.Windows.Where(w => w.PrintCountFanoFactor.HasValue)
                .Select(w => w.PrintCountFanoFactor!.Value)
                .OrderBy(v => v).ToArray();
            double? medianFano = fano.Length == 0 ? null :
                fano.Length % 2 == 1 ? fano[fano.Length / 2] :
                (fano[fano.Length / 2 - 1] + fano[fano.Length / 2]) / 2;
            double? timestampShare = report.PublicPrints == 0
                ? null : (double)report.PrintsSharingTimestamp / report.PublicPrints;
            double? nearSecondShare = report.PublicPrints == 0 ? null :
                report.Windows.Sum(w => w.NearWholeSecondPrintShare * w.PublicPrints) /
                    report.PublicPrints;
            double? activityShare = report.PopulatedWindows == 0 ? null :
                (double)report.ElevatedActivityWindows / report.PopulatedWindows;

            string instruments = string.Join(", ", report.Groups.Select(g => g.Ticker)
                .Distinct(StringComparer.Ordinal).OrderBy(x => x, StringComparer.Ordinal));
            string modes = string.Join(", ", report.Groups
                .Select(g => g.TradeSource + "/" + g.TradingMode)
                .Distinct(StringComparer.Ordinal)
                .OrderBy(x => x, StringComparer.Ordinal));
            rows.Add(new ResearchComparisonRow(
                report.SourceFileName, report.SourceSha256, report.DataKind,
                instruments, modes, report.DistinctInstruments, report.Groups.Count,
                report.PublicPrints, report.ObservedLots, report.PopulatedWindows,
                report.ElevatedActivityWindows, activityShare, timestampShare,
                nearSecondShare, medianFano, report.FeedCoverageVerified));
        }

        bool sameKind = rows.Select(r => r.DataKind)
            .Distinct(StringComparer.Ordinal).Count() <= 1;
        int prints = checked(rows.Sum(x => x.PublicPrints));
        long lots = checked(rows.Sum(x => x.ObservedLots));
        return new ResearchComparisonReport(
            "0.1-multi-archive-observations", rows.Count, width,
            prints, lots, sameKind, rows.All(r => r.FeedCoverageVerified),
            false, false, rows,
            new[]
            {
                "OBSERVATIONAL_COMPARISON: differences in prints, Fano and clock phases do not identify individual robots.",
                "INDEPENDENT_ARCHIVE_HASHES: source SHA duplicates are refused, but different files can still contain overlapping market data.",
                "NO_TRADING_SIGNAL: no independent out-of-sample forecasting advantage has been established.",
                "SOURCE_MIX: venue/side/session and changing trade regimes confound direct comparisons of activity.",
                sameKind
                    ? "DATA_KIND_MATCH: labels match, but market data comparability is still unverified."
                    : "MIXED_DATA_KINDS: synthetic/live/historical sources are not directly comparable.",
                "UNKNOWN_COVERAGE: event-free intervals, market halts and incomplete vendor archives may change ratios.",
                "READ_ONLY_OFFLINE: contains no account, token, order, owner identity or raw trade prints."
            });
    }

    public static string ToStandaloneHtml(ResearchComparisonReport report)
    {
        if (report.InputArchiveCount != report.Archives.Count ||
            report.Archives.Count is < 2 or > 20 ||
            report.TotalPublicPrints != report.Archives.Sum(r => r.PublicPrints) ||
            report.TotalObservedLots != report.Archives.Sum(r => r.ObservedLots) ||
            report.ActualBotCountKnown || report.StatisticalSignificanceEstablished)
            throw new InvalidDataException("Invalid archive comparison summary.");

        static string E(string? s) => WebUtility.HtmlEncode(s ?? "");
        static string N(long v) => v.ToString("N0", CultureInfo.InvariantCulture);
        static string P(double? v) => v.HasValue
            ? (100 * v.Value).ToString("0.##", CultureInfo.InvariantCulture) + "%" : "—";
        static string D(double? v) => v.HasValue
            ? v.Value.ToString("0.###", CultureInfo.InvariantCulture) : "—";
        var sb = new StringBuilder(13000);
        sb.AppendLine("<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">");
        sb.AppendLine("<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; form-action 'none'; base-uri 'none'\">");
        sb.AppendLine("<title>Robot Detector · сравнение архивов</title><style>body{background:#121a2a;color:#edf3f9;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;margin:0;line-height:1.55}main{max-width:1140px;margin:auto;padding:28px 20px}h1{font-size:1.7rem}h2{font-size:1.15rem;margin-top:28px}.muted{color:#abbdd1}.notice{border-left:3px solid #91a5bd;padding:12px 15px;background:#223047}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{text-align:left;padding:10px;border-bottom:1px solid #35445b;font-size:.85rem}th{background:#24334c}tr:nth-child(even){background:#1b283e}.scroll{overflow-x:auto}.metricgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:20px 0}.metric{padding:15px;background:#213048;border-radius:10px}.metric strong{font-size:1.4rem;display:block}.foot{font-size:.78rem;overflow-wrap:anywhere}@media print{body{background:white;color:black}.notice,.metric,th{background:#eee;color:black}}</style></head><body><main>");
        sb.AppendLine("<h1>Сравнение независимых архивов рынка</h1>");
        sb.AppendLine("<p class=\"notice\"><strong>Исследовательская статистика, не поиск владельцев.</strong> Сходство или различие частот, объёмов и времени сделок не подтверждает наличие определённого количества торговых роботов. Прогностическая точность не откалибрована.</p>");
        sb.AppendLine("<section class=\"metricgrid\">");
        Metric("Файлов", N(report.InputArchiveCount));
        Metric("Сделок суммарно", N(report.TotalPublicPrints));
        Metric("Лотов суммарно", N(report.TotalObservedLots));
        Metric("Ширина окна, мин", N(report.WindowMinutes));
        sb.AppendLine("</section><h2>Сопоставление источников</h2><div class=\"scroll\"><table><thead><tr><th>Архив</th><th>Инструмент</th><th>Источник/режим</th><th>Сделок</th><th>Лотов</th><th>Окон</th><th>Всплески</th><th>Совпадающий timestamp</th><th>Начало секунды</th><th>Медиана Fano</th></tr></thead><tbody>");
        foreach (var row in report.Archives)
        {
            sb.Append("<tr><td>").Append(E(row.SourceFileName))
                .Append("</td><td>").Append(E(row.InstrumentNames))
                .Append("</td><td>").Append(E(row.SourceModes))
                .Append("</td><td>").Append(N(row.PublicPrints))
                .Append("</td><td>").Append(N(row.ObservedLots))
                .Append("</td><td>").Append(N(row.PopulatedWindows))
                .Append("</td><td>").Append(N(row.ElevatedActivityWindows))
                .Append("</td><td>").Append(P(row.TimestampCollisionShare))
                .Append("</td><td>").Append(P(row.NearWholeSecondPrintShare))
                .Append("</td><td>").Append(D(row.MedianWindowFano))
                .Append("</td></tr>\n");
        }
        sb.AppendLine("</tbody></table></div>");
        sb.AppendLine("<h2>Ограничения интерпретации</h2><ul>");
        foreach (string warning in report.Warnings)
            sb.Append("<li>").Append(E(warning)).Append("</li>\n");
        sb.AppendLine("</ul><p class=\"muted\">Никаких исходных сделок, токенов или исполняемых скриптов в HTML нет.</p><h2>Контрольные отпечатки файлов</h2><ul class=\"foot\">");
        foreach (var row in report.Archives)
            sb.Append("<li>").Append(E(row.SourceFileName)).Append(": <code>")
                .Append(E(row.SourceSha256)).Append("</code></li>\n");
        sb.AppendLine("</ul></main></body></html>");
        return sb.ToString();

        void Metric(string label, string value) => sb.Append("<div class=\"metric\"><small>")
            .Append(E(label)).Append("</small><strong>").Append(E(value))
            .Append("</strong></div>\n");
    }
}
