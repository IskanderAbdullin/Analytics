using System.Globalization;

namespace TInvestAnalytics;

/// <summary>
/// Noncontiguous day aggregation. Values are partial settled/realized figures, not full NAV.
/// Replays all prior fills to carry security cost basis into selected dates.
/// </summary>
public sealed record DailyPnl(
    string UtcDay, bool Included,
    IReadOnlyList<PnlComponent> Components, string Quality,
    int OperationCount, IReadOnlyList<string> Warnings);

public sealed record DailyPnlReport(
    string AccountRef, DateTimeOffset FromUtc, DateTimeOffset ToUtc,
    IReadOnlyList<string> ExcludedUtcDays, IReadOnlyList<DailyPnl> Days,
    IReadOnlyDictionary<string, decimal> SelectedSubtotalByCurrency,
    string Quality, string Method = "realized-plus-settled-utc-days/v1");

public static class DailyReporting
{
    public static DailyPnlReport Calculate(string accountId,
        IReadOnlyList<BrokerOperation> allOperationsBeforeTo,
        IReadOnlyDictionary<string, string> assetTypes,
        DateTimeOffset from, DateTimeOffset to, IReadOnlySet<DateOnly> excludedDays)
    {
        if (from >= to) throw new ArgumentException("Empty daily reporting period.");
        if ((to - from).TotalDays > 366)
            throw new ArgumentOutOfRangeException(nameof(to), "Initial version limits daily reports to 366 days.");
        var startUtc = from.ToUniversalTime();
        var endUtc = to.ToUniversalTime();
        var cursor = new DateTimeOffset(startUtc.UtcDateTime.Date, TimeSpan.Zero);
        var result = new List<DailyPnl>();
        var sums = new Dictionary<string, decimal>(StringComparer.Ordinal);
        while (cursor < endUtc)
        {
            var windowFrom = cursor < startUtc ? startUtc : cursor;
            var windowTo = cursor.AddDays(1) < endUtc ? cursor.AddDays(1) : endUtc;
            var day = DateOnly.FromDateTime(cursor.UtcDateTime);
            var report = PnlCalculator.Calculate(accountId, allOperationsBeforeTo,
                assetTypes, windowFrom, windowTo);
            bool included = !excludedDays.Contains(day);
            result.Add(new DailyPnl(day.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), included,
                report.Components, report.Status, report.SourceOperationCount, report.Warnings));
            if (included)
            {
                foreach (var (ccy, amount) in report.TotalsByCurrency)
                    sums[ccy] = sums.GetValueOrDefault(ccy) + amount;
            }
            cursor = cursor.AddDays(1);
        }
        return new DailyPnlReport(PnlCalculator.Mask(accountId), startUtc, endUtc,
            excludedDays.Order().Select(x => x.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)).ToList(),
            result, sums, "partial");
    }
}
