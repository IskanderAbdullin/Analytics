using System.Globalization;

namespace RobotDetector.Core;

/// <summary>
/// Post-hoc descriptive audit of rolling misses. It MUST NOT be consulted
/// during prediction discovery or used to refit a previously held-out date.
/// Public prints cannot identify parent orders, algorithms or owners.
/// </summary>
public sealed record ForecastAgeBucket(
    string Name,
    int EvaluatedForecasts,
    int ObservedHits,
    int PlaceboHits,
    double? ObservedHitRate,
    double? PlaceboHitRate
);

public sealed record ForecastFailureDiagnosticReport(
    string SchemaVersion,
    string SourceSha256,
    string ForecastSchemaVersion,
    int ForecastsEvaluated,
    int ExactHits,
    int PlaceboHits,
    int Misses,
    int MissesWithSameSizeOutsideExactWindow,
    int MissesWithDifferentSizeInsideExactWindow,
    int MissesWithDifferentSizeNearTarget,
    int MissesWithOppositeDirectionInsideExactWindow,
    int MissesWithNoSameSidePrintNearTarget,
    int MissesWithIncompleteNearbyWindow,
    int MissesWithStaleTrainingPattern,
    int NearWholeSecondTargetForecasts,
    int NearWholeSecondTargetHits,
    IReadOnlyList<ForecastAgeBucket> HistoricalAgeBuckets,
    bool ActualBotCountKnown,
    bool StatisticalSignificanceEstablished,
    bool DataCoverageVerified,
    IReadOnlyList<string> Warnings
);

public static class ForecastFailureDiagnostics
{
    public static ForecastFailureDiagnosticReport Analyse(
        TradeImportResult source,
        RollingForecastReport forecast,
        DetectorConfig config,
        double nearFractionOfPeriod = 0.25,
        int maximumNearMilliseconds = 10000)
    {
        config.Validate();
        if (source.FileSha256 != forecast.SourceSha256)
            throw new ArgumentException("Source hash and frozen forecast report differ.");
        if (nearFractionOfPeriod <= 0 || nearFractionOfPeriod > 0.49 ||
            maximumNearMilliseconds < 250 || maximumNearMilliseconds > 60000)
            throw new ArgumentException("Invalid post-hoc diagnostic window.");
        if (forecast.ForecastsEvaluated != forecast.Observations.Count ||
            forecast.ObservedHits != forecast.Observations.Count(x => x.Hit) ||
            forecast.PlaceboHits != forecast.Observations.Count(x => x.PlaceboHit))
            throw new InvalidDataException("Forecast metadata and individual checks disagree.");

        var lookups = source.Trades.GroupBy(t => (
                t.InstrumentUid, t.TradeSource, t.TradingMode, t.SessionId))
            .ToDictionary(g => g.Key,
                g => g.OrderBy(t => t.ExchangeTimeUtc)
                    .ThenBy(t => t.ArrivalSequence).ToArray());

        int misses = 0, shiftedSameSize = 0, changedSizeAtTarget = 0,
            changedSizeNear = 0, oppositeAtTarget = 0, noSameSideNearby = 0,
            unscorableNearby = 0, stale = 0, roundSecondTargets = 0,
            roundSecondHits = 0;
        var bucketCounts = new Dictionary<string, (int Count, int Hits, int PlaceboHits)>
        {
            ["fresh_0_2_cycles"] = (0, 0, 0),
            ["age_2_8_cycles"] = (0, 0, 0),
            ["stale_over_8_cycles"] = (0, 0, 0)
        };

        foreach (var o in forecast.Observations)
        {
            if (o.PeriodMilliseconds <= 0 || o.ExpectedQuantityLots <= 0 ||
                string.IsNullOrWhiteSpace(o.TradingMode) ||
                string.IsNullOrWhiteSpace(o.LastTrainingEvidenceUtc) ||
                o.TrainingMatchedCount < config.MinMatches)
                throw new InvalidDataException("Rolling check lacks frozen historical provenance.");

            var target = DateTimeOffset.Parse(o.TargetUtc, CultureInfo.InvariantCulture,
                DateTimeStyles.AdjustToUniversal);
            var cutoff = DateTimeOffset.Parse(o.CutoffUtc, CultureInfo.InvariantCulture,
                DateTimeStyles.AdjustToUniversal);
            var lastEvidence = DateTimeOffset.Parse(o.LastTrainingEvidenceUtc,
                CultureInfo.InvariantCulture, DateTimeStyles.AdjustToUniversal);
            if (lastEvidence > cutoff || target <= cutoff)
                throw new InvalidDataException("Future events leaked into historical evidence.");
            double ageCycles = (cutoff - lastEvidence).TotalMilliseconds / o.PeriodMilliseconds;
            string bucket = ageCycles <= 2 ? "fresh_0_2_cycles" :
                ageCycles <= 8 ? "age_2_8_cycles" : "stale_over_8_cycles";
            var b = bucketCounts[bucket];
            bucketCounts[bucket] = (b.Count + 1, b.Hits + (o.Hit ? 1 : 0),
                b.PlaceboHits + (o.PlaceboHit ? 1 : 0));

            if (target.ToUnixTimeMilliseconds() % 1000 is >= 0 and <= 100)
            {
                roundSecondTargets++;
                if (o.Hit) roundSecondHits++;
            }
            if (o.Hit) continue;
            misses++;
            if (ageCycles > 8) stale++;

            var key = (o.InstrumentUid, o.TradeSource, o.TradingMode, o.SessionId);
            if (!lookups.TryGetValue(key, out var tape) || tape.Length == 0)
                throw new InvalidDataException("Forecast source/session group is absent in imported tape.");

            double strictMs = Math.Max(config.MinimumTimeToleranceMilliseconds,
                Math.Min(config.MaximumTimeToleranceMilliseconds,
                    config.RelativeTimeTolerance * o.PeriodMilliseconds));
            double nearMs = Math.Max(250,
                Math.Min(maximumNearMilliseconds, o.PeriodMilliseconds * nearFractionOfPeriod));
            // Always require a wider-than-exact diagnostic interval. It is for
            // descriptive inspection, not a second, optimized prediction window.
            nearMs = Math.Max(nearMs, strictMs + 1);
            var nearStart = target.AddMilliseconds(-nearMs);
            var nearEnd = target.AddMilliseconds(nearMs);
            if (nearStart <= cutoff || nearEnd > tape[^1].ExchangeTimeUtc)
            {
                unscorableNearby++;
                continue;
            }

            bool sameSideNear = false, sameSizeOutsideExact = false,
                otherSizeAtTarget = false, otherSizeNear = false, otherSideAtTarget = false;
            int begin = LowerBound(tape, nearStart);
            for (int i = begin; i < tape.Length && tape[i].ExchangeTimeUtc <= nearEnd; i++)
            {
                var t = tape[i];
                if (t.ExchangeTimeUtc <= cutoff) continue;
                double errorMs = Math.Abs((t.ExchangeTimeUtc - target).TotalMilliseconds);
                bool exact = errorMs <= strictMs;
                bool sameSide = t.ReportedDirection == o.ReportedDirection;
                if (sameSide)
                {
                    sameSideNear = true;
                    if (t.QuantityLots == o.ExpectedQuantityLots)
                    {
                        if (!exact) sameSizeOutsideExact = true;
                    }
                    else
                    {
                        otherSizeNear = true;
                        if (exact) otherSizeAtTarget = true;
                    }
                }
                else if (exact)
                    otherSideAtTarget = true;
            }

            if (!sameSideNear) noSameSideNearby++;
            if (sameSizeOutsideExact) shiftedSameSize++;
            if (otherSizeAtTarget) changedSizeAtTarget++;
            if (otherSizeNear) changedSizeNear++;
            if (otherSideAtTarget) oppositeAtTarget++;
        }

        var ageBuckets = bucketCounts.Select(k =>
            new ForecastAgeBucket(k.Key, k.Value.Count, k.Value.Hits,
                k.Value.PlaceboHits,
                k.Value.Count == 0 ? null : (double)k.Value.Hits / k.Value.Count,
                k.Value.Count == 0 ? null : (double)k.Value.PlaceboHits / k.Value.Count))
            .ToArray();

        return new ForecastFailureDiagnosticReport(
            "0.1-post-hoc-audit", source.FileSha256, forecast.SchemaVersion,
            forecast.ForecastsEvaluated, forecast.ObservedHits, forecast.PlaceboHits,
            misses, shiftedSameSize, changedSizeAtTarget,
            changedSizeNear, oppositeAtTarget, noSameSideNearby,
            unscorableNearby, stale, roundSecondTargets, roundSecondHits,
            ageBuckets, false, false, source.HasVerifiedFeedCoverage,
            new[]
            {
                "POST_HOC_ONLY: audit reads later prints; NEVER feed these findings into historical forecasts.",
                "AMBIGUOUS_CAUSES: nearby size/time/direction matches can belong to unrelated traders.",
                "NON_EXCLUSIVE_COUNTS: multiple descriptive flags can apply to one missed prediction.",
                "STALENESS_IS_HISTORIC: training age in forecast periods was known at cutoff.",
                "UNVERIFIED_COVERAGE: no print near target does not prove absence of executed orders.",
                "NO_OWNER_ID: no access to individual order IDs, parent orders, traders or actual robot count.",
                "NOT_CALIBRATED: diagnostic counts are not p-values, false discovery rates or trading signals.",
                "RUN_CONTEXT: validate explanations on development data, never optimize thresholds on sealed test dates."
            });
    }

    private static int LowerBound(MarketTrade[] rows, DateTimeOffset value)
    {
        int low = 0, high = rows.Length;
        while (low < high)
        {
            int mid = low + (high - low) / 2;
            if (rows[mid].ExchangeTimeUtc < value) low = mid + 1;
            else high = mid;
        }
        return low;
    }
}
