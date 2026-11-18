using System.Globalization;

namespace RobotDetector.Core;

/// <summary>
/// Strict chronological, one-step forecast evaluation. Candidate discovery sees only
/// training events. Forecast outcomes are read strictly after the frozen cut-off.
/// Does not calculate confidence or make a claim about unique trading programs.
/// </summary>
public sealed record ForecastCheck(
    string PatternId,
    string ForecastOriginUtc,
    string PredictedTargetUtc,
    string WindowStartUtc,
    string WindowEndUtc,
    string? FutureMatchedEventId,
    bool Hit,
    int PeriodMs,
    long ExpectedQuantityLots,
    string InstrumentUid = "",
    string TradeSource = "",
    string ReportedDirection = "",
    string SessionId = "",
    string LastTrainingEvidenceUtc = "",
    int TrainingMatchedCount = 0
);

public sealed record WalkForwardReport(
    string SchemaVersion, string CutoffUtc, int TrainingPrints, int FuturePrints,
    int TrainingCandidates, int ForecastsIssued, int Hits,
    bool Calibrated, bool CoverageVerified, IReadOnlyList<ForecastCheck> Checks,
    IReadOnlyList<string> Warnings
);

public static class WalkForward
{
    public static WalkForwardReport Evaluate(TradeImportResult input, DateTimeOffset cutoffUtc,
        DetectorConfig config)
    {
        config.Validate();
        if (cutoffUtc.Offset != TimeSpan.Zero)
            throw new ArgumentException("Use explicit UTC cutoff.");
        var training = input.Trades.Where(t => t.ExchangeTimeUtc <= cutoffUtc).ToList();
        var future = input.Trades.Where(t => t.ExchangeTimeUtc > cutoffUtc).ToList();

        var trainingImport = new TradeImportResult(training, input.RejectedRows,
            input.FileName, input.FileSha256, input.HasVerifiedFeedCoverage, input.RejectedRowTotal);
        var candidates = PeriodicDetector.Detect(trainingImport, config);
        var checks = new List<ForecastCheck>();
        var trainingEvidenceById = training.GroupBy(t => t.EventId, StringComparer.Ordinal)
            .ToDictionary(g => g.Key, g => g.Max(t => t.ExchangeTimeUtc), StringComparer.Ordinal);
        var assignedFuture = new HashSet<string>(StringComparer.Ordinal);
        foreach (var pattern in candidates.Patterns)
        {
            var anchor = DateTimeOffset.Parse(pattern.PhaseUtc, CultureInfo.InvariantCulture,
                DateTimeStyles.AdjustToUniversal);
            double cycles = (cutoffUtc - anchor).TotalMilliseconds / pattern.PeriodMilliseconds;
            long nextCycle = Math.Max(0, checked((long)Math.Floor(cycles) + 1));
            var target = anchor.AddMilliseconds(nextCycle * pattern.PeriodMilliseconds);
            if (target <= cutoffUtc) target = target.AddMilliseconds(pattern.PeriodMilliseconds);
            double tolerance = Math.Max(config.MinimumTimeToleranceMilliseconds,
                Math.Min(config.MaximumTimeToleranceMilliseconds,
                         config.RelativeTimeTolerance * pattern.PeriodMilliseconds));
            var windowStart = target.AddMilliseconds(-tolerance);
            var windowEnd = target.AddMilliseconds(tolerance);
            if (windowStart <= cutoffUtc) windowStart = cutoffUtc.AddTicks(1);
            // If the target was beyond available future data, skip scoring:
            // lack of future coverage is NOT a negative.
            if (future.Count == 0 || windowEnd > future[^1].ExchangeTimeUtc)
                continue;
            var match = future
                .Where(t => t.InstrumentUid == pattern.InstrumentUid &&
                            t.TradeSource == pattern.TradeSource &&
                            t.ReportedDirection == pattern.ReportedDirection &&
                            t.SessionId == pattern.SessionId &&
                            t.QuantityLots == pattern.TypicalQuantityLots &&
                            t.ExchangeTimeUtc >= windowStart && t.ExchangeTimeUtc <= windowEnd &&
                            !assignedFuture.Contains(t.EventId))
                .OrderBy(t => Math.Abs((t.ExchangeTimeUtc - target).TotalMilliseconds))
                .ThenBy(t => t.ArrivalSequence)
                .FirstOrDefault();
            if (match is not null) assignedFuture.Add(match.EventId);
            var lastEvidence = pattern.EvidenceEventIds.Select(id =>
                trainingEvidenceById.TryGetValue(id, out var timestamp) ? timestamp :
                    throw new InvalidDataException("Candidate evidence not present in historical training prefix.")).Max();
            checks.Add(new ForecastCheck(pattern.PatternId, cutoffUtc.ToString("O"),
                target.ToString("O"), windowStart.ToString("O"), windowEnd.ToString("O"),
                match?.EventId, match is not null, pattern.PeriodMilliseconds,
                pattern.TypicalQuantityLots, pattern.InstrumentUid, pattern.TradeSource,
                pattern.ReportedDirection, pattern.SessionId,
                lastEvidence.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
                pattern.MatchedCount));
        }
        return new WalkForwardReport("0.1-prospective-evaluation", cutoffUtc.ToString("O"),
            training.Count, future.Count, candidates.CandidatePatternCount,
            checks.Count, checks.Count(x => x.Hit), false, input.HasVerifiedFeedCoverage,
            checks, new[]
            {
                "Forecasts are generated from prints at or before cutoff; outcomes are later prints.",
                "An observed matching trade is not proof of the same trader, order, or algorithm.",
                "No calibrated probabilities or participant identities.",
                "Missing future coverage cannot be interpreted as a negative outcome."
            });
    }
}
