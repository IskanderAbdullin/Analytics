using System.Globalization;

namespace RobotDetector.Core;

/// <summary>
/// Chronological evaluation at multiple predeclared UTC cutoffs. Each
/// candidate is discovered only from prints at/before the cutoff.
/// A half-period phase shift is the uncalibrated matched-placebo comparator.
/// No probability, physical trader ID or complete feed is inferred.
/// </summary>
public sealed record RollingForecastObservation(
    string SessionId,
    string InstrumentUid,
    string TradeSource,
    string ReportedDirection,
    long ExpectedQuantityLots,
    int PeriodMilliseconds,
    string CutoffUtc,
    string TargetUtc,
    string PhaseShiftPlaceboUtc,
    string? MatchedEventId,
    string? PlaceboMatchedEventId,
    bool Hit,
    bool PlaceboHit
);

public sealed record RollingForecastReport(
    string SchemaVersion,
    string SourceSha256,
    int SourcePrintCount,
    int SessionSourceGroups,
    int CutoffsExamined,
    int ForecastsEvaluated,
    int ObservedHits,
    int PlaceboHits,
    double? ObservedHitRate,
    double? PlaceboHitRate,
    bool DataCoverageVerified,
    bool Calibrated,
    bool ActualBotCountKnown,
    IReadOnlyList<RollingForecastObservation> Observations,
    IReadOnlyList<string> Warnings
);

public static class RollingForecast
{
    public static RollingForecastReport Evaluate(
        TradeImportResult source,
        DetectorConfig config,
        int warmupMinutes = 20,
        int strideMinutes = 15,
        int maximumCutoffsPerSession = 24)
    {
        config.Validate();
        if (warmupMinutes is < 1 or > 1440 || strideMinutes is < 1 or > 1440 ||
            maximumCutoffsPerSession is < 1 or > 100)
            throw new ArgumentException("Invalid chronological replay settings.");
        if (source.Trades.Count > 500_000)
            throw new ArgumentException("Split inputs by instrument and trading day.");

        var observations = new List<RollingForecastObservation>();
        int totalCutoffs = 0;
        int sessionGroups = 0;
        var seenObservedPrints = new HashSet<string>(StringComparer.Ordinal);
        var seenPlaceboPrints = new HashSet<string>(StringComparer.Ordinal);

        // Never mix venue/source/trading mode/session in either candidate
        // discovery or placebo evaluation.
        foreach (var group in source.Trades
            .GroupBy(t => (t.InstrumentUid, t.TradeSource, t.TradingMode, t.SessionId))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal))
        {
            var events = group.OrderBy(t => t.ExchangeTimeUtc)
                .ThenBy(t => t.ArrivalSequence).ToArray();
            if (events.Length < config.MinMatches) continue;
            sessionGroups++;
            var groupInput = new TradeImportResult(
                events, source.RejectedRows, source.FileName, source.FileSha256,
                source.HasVerifiedFeedCoverage, source.RejectedRowTotal);
            var lastTargetBySignature = new Dictionary<string, DateTimeOffset>(
                StringComparer.Ordinal);

            int cutoffsThisSession = 0;
            var cutoff = events[0].ExchangeTimeUtc.AddMinutes(warmupMinutes);
            while (cutoff < events[^1].ExchangeTimeUtc &&
                   cutoffsThisSession < maximumCutoffsPerSession)
            {
                totalCutoffs++;
                cutoffsThisSession++;
                var report = WalkForward.Evaluate(groupInput, cutoff, config);
                foreach (var check in report.Checks)
                {
                    var target = DateTimeOffset.Parse(check.PredictedTargetUtc,
                        CultureInfo.InvariantCulture, DateTimeStyles.AdjustToUniversal);
                    var originalWindowEnd = DateTimeOffset.Parse(check.WindowEndUtc,
                        CultureInfo.InvariantCulture, DateTimeStyles.AdjustToUniversal);
                    double toleranceMs = (originalWindowEnd - target).TotalMilliseconds;
                    var placeboTarget = target.AddMilliseconds(check.PeriodMs / 2.0);
                    var placeboEnd = placeboTarget.AddMilliseconds(toleranceMs);

                    // The original forecast and its placebo must both be
                    // fully scorable within the available future observation.
                    if (placeboEnd > events[^1].ExchangeTimeUtc) continue;

                    string signature = string.Join("|", check.InstrumentUid, check.TradeSource,
                        check.ReportedDirection, check.SessionId,
                        check.ExpectedQuantityLots, check.PeriodMs);
                    if (lastTargetBySignature.TryGetValue(signature, out var lastTarget) &&
                        Math.Abs((target - lastTarget).TotalMilliseconds) < check.PeriodMs / 4.0)
                        continue; // Don't count repeated predictions of the same slot.
                    lastTargetBySignature[signature] = target;

                    string? hitId = null;
                    if (check.Hit && check.FutureMatchedEventId is { } eventId &&
                        seenObservedPrints.Add(eventId))
                        hitId = eventId;

                    var placeboStart = placeboTarget.AddMilliseconds(-toleranceMs);
                    var placeboMatch = events
                        .Where(t => t.ExchangeTimeUtc > cutoff &&
                                    t.ExchangeTimeUtc >= placeboStart &&
                                    t.ExchangeTimeUtc <= placeboEnd &&
                                    t.InstrumentUid == check.InstrumentUid &&
                                    t.TradeSource == check.TradeSource &&
                                    t.ReportedDirection == check.ReportedDirection &&
                                    t.SessionId == check.SessionId &&
                                    t.QuantityLots == check.ExpectedQuantityLots &&
                                    !seenPlaceboPrints.Contains(t.EventId))
                        .OrderBy(t => Math.Abs((t.ExchangeTimeUtc - placeboTarget).TotalMilliseconds))
                        .ThenBy(t => t.ArrivalSequence)
                        .FirstOrDefault();
                    if (placeboMatch is not null) seenPlaceboPrints.Add(placeboMatch.EventId);

                    observations.Add(new RollingForecastObservation(
                        check.SessionId, check.InstrumentUid, check.TradeSource,
                        check.ReportedDirection, check.ExpectedQuantityLots,
                        check.PeriodMs, cutoff.ToUniversalTime().ToString("O"),
                        target.ToUniversalTime().ToString("O"),
                        placeboTarget.ToUniversalTime().ToString("O"),
                        hitId, placeboMatch?.EventId,
                        hitId is not null, placeboMatch is not null));
                }
                cutoff = cutoff.AddMinutes(strideMinutes);
            }
        }

        int hits = observations.Count(x => x.Hit);
        int placeboHits = observations.Count(x => x.PlaceboHit);
        return new RollingForecastReport(
            "0.1-exploratory-chronological", source.FileSha256,
            source.Trades.Count, sessionGroups, totalCutoffs,
            observations.Count, hits, placeboHits,
            observations.Count == 0 ? null : (double)hits / observations.Count,
            observations.Count == 0 ? null : (double)placeboHits / observations.Count,
            source.HasVerifiedFeedCoverage, false, false,
            observations, new[]
            {
                "STRICT_CHRONOLOGY: patterns were discovered at/before each cutoff and checked only on later prints.",
                "UNVALIDATED_PLACEBO: half-period shift is a simple descriptive comparator, not a p-value/FDR.",
                "NO_OWNER_INFERENCE: a matching future print is not evidence of the same owner or bot.",
                "SESSION_ISOLATED: instrument/source/mode/session groups never share evidence.",
                "INCOMPLETE_FEED_CAVEAT: observed misses cannot prove an algo stopped when feed completeness is unknown.",
                "MULTIPLE_TESTING_CAVEAT: numerous candidate periods/cutoffs can yield accidental matches; no calibrated confidence."
            });
    }
}
