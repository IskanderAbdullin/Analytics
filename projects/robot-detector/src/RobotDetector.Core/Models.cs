using System.Text.Json.Serialization;

namespace RobotDetector.Core;

/// <summary>
/// One public trade print, not an order or an identified owner.
/// EventId is a source-record identity; identical timestamps do not imply duplicates.
/// </summary>
public sealed record MarketTrade(
    string EventId,
    DateTimeOffset ExchangeTimeUtc,
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string ReportedDirection,
    decimal Price,
    long QuantityLots,
    string TradingMode,
    string SessionId,
    string DataKind,
    long ArrivalSequence
);

public sealed record BadRow(long LineNumber, string Reason, string RawExcerpt);

public sealed record TradeImportResult(
    IReadOnlyList<MarketTrade> Trades,
    IReadOnlyList<BadRow> RejectedRows,
    string FileName,
    string FileSha256,
    bool HasVerifiedFeedCoverage,
    int RejectedRowTotal = 0
);

public sealed class DetectorConfig
{
    public int MinMatches { get; init; } = 6;
    public double MinCoverage { get; init; } = 0.55;
    public int MinimumPeriodMilliseconds { get; init; } = 200;
    public int MaximumPeriodMilliseconds { get; init; } = 600000;
    public int PeriodGridMilliseconds { get; init; } = 50;
    public int MinimumTimeToleranceMilliseconds { get; init; } = 10;
    public int MaximumTimeToleranceMilliseconds { get; init; } = 200;
    public double RelativeTimeTolerance { get; init; } = 0.02;
    public int MaximumCycleGap { get; init; } = 8;
    public int MaximumEventsPerGroup { get; init; } = 5000;
    public int AnalysisWindowMinutes { get; init; } = 60;
    public int CandidateLag { get; init; } = 24;
    public int CandidateLimit { get; init; } = 128;
    public int AnchorLimit { get; init; } = 32;

    public void Validate()
    {
        if (MinMatches < 3 || MinCoverage <= 0 || MinCoverage > 1 ||
            MinimumPeriodMilliseconds <= 0 || MaximumPeriodMilliseconds < MinimumPeriodMilliseconds ||
            PeriodGridMilliseconds <= 0 || MinimumTimeToleranceMilliseconds < 0 ||
            MaximumTimeToleranceMilliseconds < MinimumTimeToleranceMilliseconds ||
            RelativeTimeTolerance < 0 || RelativeTimeTolerance > 1 ||
            MaximumCycleGap < 1 || MaximumEventsPerGroup < MinMatches ||
            AnalysisWindowMinutes < 1 || AnalysisWindowMinutes > 1440 ||
            CandidateLag < 1 || CandidateLimit < 1 || AnchorLimit < 1)
            throw new ArgumentException("Invalid detector configuration.");
    }
}

public sealed record PatternHypothesis(
    string PatternId,
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string ReportedDirection,
    string SessionId,
    long TypicalQuantityLots,
    int PeriodMilliseconds,
    string PhaseUtc,
    int MatchedCount,
    int ExpectedCycles,
    int MissedCycles,
    long ObservedLots,
    double MeanAbsoluteTimingResidualMs,
    double CoverageRatio,
    IReadOnlyList<string> EvidenceEventIds,
    string ModelFamily,
    string State,
    double? ConfidenceCalibrated,
    string EvidenceLimitations
);

public sealed record DetectionReport(
    string SchemaVersion,
    string EngineVersion,
    string DataKind,
    string SourceSha256,
    int SourceTradeCount,
    int RejectedRowCount,
    bool CoverageVerified,
    int CandidatePatternCount,
    bool PhysicalBotCountKnown,
    IReadOnlyList<PatternHypothesis> Patterns,
    IReadOnlyList<string> Warnings
)
{
    [JsonIgnore]
    public long AssignedLots => Patterns.Sum(p => p.ObservedLots);
}
