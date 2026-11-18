using System.Globalization;
using System.Security.Cryptography;
using System.Text;

namespace RobotDetector.Core;

/// <summary>
/// Conservative grouping of already selected, disjoint candidate episodes.
/// This is an observable continuity summary, NOT a way to infer owner identity.
/// </summary>
public sealed record ObservableCadenceGroup(
    string GroupId,
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string ReportedDirection,
    string TradingMode,
    string SessionId,
    string ModelFamily,
    long TypicalQuantityLots,
    int PeriodMilliseconds,
    string FirstSeenUtc,
    string LastSeenUtc,
    int EpisodeCount,
    IReadOnlyList<string> EpisodePatternIds,
    int UniquePrintCount,
    long ObservedLots,
    string State,
    double? ConfidenceCalibrated,
    bool OwnerIdentityKnown,
    string Interpretation
);

public sealed record EpisodeFusionReport(
    string SchemaVersion,
    string SourceSha256,
    int CandidateEpisodeCount,
    int ConservativelyLinkedGroupCount,
    int LinkedEpisodeCount,
    int UniqueAttributedPrintCount,
    long UniqueAttributedLots,
    bool ActualBotCountKnown,
    IReadOnlyList<ObservableCadenceGroup> Groups,
    IReadOnlyList<string> Warnings
);

public static class EpisodeFusion
{
    private sealed record ObservedEpisode(
        PatternHypothesis Pattern,
        string TradingMode,
        DateTimeOffset First,
        DateTimeOffset Last,
        IReadOnlyList<MarketTrade> Evidence);

    private sealed class Chain
    {
        public List<ObservedEpisode> Episodes { get; } = new();
        public ObservedEpisode Last => Episodes[^1];
    }

    /// <summary>
    /// Link consecutive candidate episodes only if they agree on source/session/mode,
    /// direction, exact fixed-quantity and period, and have compatible observed phase.
    /// No evidence event can be attributed to two groups. Large gaps are not bridged.
    /// </summary>
    public static EpisodeFusionReport Group(TradeImportResult source,
        DetectionReport detected, DetectorConfig config, int maxGapCycles = 12)
    {
        config.Validate();
        if (maxGapCycles is < 1 or > 100)
            throw new ArgumentOutOfRangeException(nameof(maxGapCycles));
        if (source.FileSha256 != detected.SourceSha256)
            throw new ArgumentException("Detection report and source file hashes differ.");

        var byId = new Dictionary<string, MarketTrade>(StringComparer.Ordinal);
        foreach (var trade in source.Trades)
        {
            if (!byId.TryAdd(trade.EventId, trade))
                throw new InvalidDataException("Non-unique source event ID; cannot safely attribute episodes.");
        }
        var allEvidence = new HashSet<string>(StringComparer.Ordinal);
        var episodes = new List<ObservedEpisode>();
        foreach (var p in detected.Patterns)
        {
            if (p.EvidenceEventIds.Count == 0)
                throw new InvalidDataException("Pattern has no evidence events.");
            var evidence = new List<MarketTrade>(p.EvidenceEventIds.Count);
            foreach (var id in p.EvidenceEventIds)
            {
                if (!byId.TryGetValue(id, out var trade))
                    throw new InvalidDataException($"Pattern refers to unavailable print: {id}");
                if (!allEvidence.Add(id))
                    throw new InvalidDataException("Same source event occurs in two accepted patterns.");
                if (trade.InstrumentUid != p.InstrumentUid ||
                    trade.TradeSource != p.TradeSource ||
                    trade.ReportedDirection != p.ReportedDirection ||
                    trade.SessionId != p.SessionId ||
                    trade.QuantityLots != p.TypicalQuantityLots)
                    throw new InvalidDataException("Pattern metadata and referenced print disagree.");
                evidence.Add(trade);
            }
            evidence.Sort((a, b) => a.ExchangeTimeUtc != b.ExchangeTimeUtc
                ? a.ExchangeTimeUtc.CompareTo(b.ExchangeTimeUtc)
                : a.ArrivalSequence.CompareTo(b.ArrivalSequence));
            var mode = evidence[0].TradingMode;
            if (evidence.Any(t => t.TradingMode != mode))
                throw new InvalidDataException("Evidence crosses trading modes.");
            if (p.PeriodMilliseconds <= 0)
                throw new InvalidDataException("Non-positive cadence period.");
            if (p.MatchedCount != evidence.Count || p.ObservedLots != evidence.Sum(t => t.QuantityLots))
                throw new InvalidDataException("Pattern event count or attributed volume disagrees with tape.");

            episodes.Add(new ObservedEpisode(p, mode,
                evidence[0].ExchangeTimeUtc, evidence[^1].ExchangeTimeUtc, evidence));
        }

        var linked = new List<Chain>();
        foreach (var cluster in episodes.GroupBy(e => (
                     e.Pattern.InstrumentUid, e.Pattern.TradeSource,
                     e.Pattern.ReportedDirection, e.Pattern.SessionId,
                     e.TradingMode, e.Pattern.TypicalQuantityLots,
                     e.Pattern.PeriodMilliseconds, e.Pattern.ModelFamily))
                 .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
                 .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
                 .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal)
                 .ThenBy(g => g.Key.ReportedDirection, StringComparer.Ordinal)
                 .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
                 .ThenBy(g => g.Key.TypicalQuantityLots)
                 .ThenBy(g => g.Key.PeriodMilliseconds))
        {
            var active = new List<Chain>();
            foreach (var e in cluster.OrderBy(e => e.First).ThenBy(e => e.Last)
                         .ThenBy(e => e.Pattern.PatternId, StringComparer.Ordinal))
            {
                var best = active.Where(c => CanLink(c.Last, e, config, maxGapCycles))
                    .OrderByDescending(c => c.Last.Last)
                    .ThenBy(c => c.Episodes[0].Pattern.PatternId, StringComparer.Ordinal)
                    .FirstOrDefault();
                if (best is null)
                {
                    best = new Chain();
                    active.Add(best);
                }
                best.Episodes.Add(e);
            }
            linked.AddRange(active);
        }

        var groups = linked.Select(chain =>
        {
            var items = chain.Episodes;
            var first = items[0];
            var last = items[^1];
            var ids = items.Select(e => e.Pattern.PatternId).ToArray();
            var prints = items.SelectMany(e => e.Evidence).ToArray();
            string key = string.Join("|", first.Pattern.InstrumentUid,
                first.Pattern.TradeSource, first.Pattern.ReportedDirection,
                first.TradingMode, first.Pattern.SessionId,
                first.Pattern.TypicalQuantityLots, first.Pattern.PeriodMilliseconds,
                string.Join(",", ids));
            string groupId = Convert.ToHexString(
                SHA256.HashData(Encoding.UTF8.GetBytes(key)))[..16].ToLowerInvariant();
            return new ObservableCadenceGroup(
                groupId, first.Pattern.InstrumentUid, first.Pattern.Ticker,
                first.Pattern.TradeSource, first.Pattern.ReportedDirection,
                first.TradingMode, first.Pattern.SessionId, first.Pattern.ModelFamily,
                first.Pattern.TypicalQuantityLots, first.Pattern.PeriodMilliseconds,
                first.First.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
                last.Last.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
                items.Count, ids, prints.Length, prints.Sum(t => t.QuantityLots),
                "candidate", null, false,
                "Conservatively linked observation episodes; not identified trading programs or owners.");
        }).OrderBy(g => g.InstrumentUid, StringComparer.Ordinal)
          .ThenBy(g => g.FirstSeenUtc, StringComparer.Ordinal)
          .ThenBy(g => g.GroupId, StringComparer.Ordinal)
          .ToArray();

        return new EpisodeFusionReport("0.1-exploratory-fusion", source.FileSha256,
            detected.CandidatePatternCount, groups.Length,
            linked.Sum(c => Math.Max(0, c.Episodes.Count - 1)),
            allEvidence.Count, groups.Sum(g => g.ObservedLots), false,
            groups, new[]
            {
                "GROUPS_ARE_NOT_ROBOTS: linking observed cadence episodes does not identify individual traders or algorithms.",
                "EXACT_MODEL: only identical period, quantity, side, venue/source, session and trading mode may be linked.",
                "SHORT_GAP_PHASE_GATE: a gap beyond the configured cycle limit or a phase mismatch forbids a link.",
                "UNVALIDATED: no calibrated confidence, per-pattern statistical significance or owner ID.",
                "Different behavioural modes of one actual program may remain separate groups."
            });
    }

    private static bool CanLink(ObservedEpisode previous, ObservedEpisode next,
        DetectorConfig config, int maxGapCycles)
    {
        // The outer grouping guarantees consistent metadata, including the period.
        if (next.First <= previous.Last) return false;
        int periodMs = previous.Pattern.PeriodMilliseconds;
        double gap = (next.First - previous.Last).TotalMilliseconds;
        if (gap > (double)maxGapCycles * periodMs) return false;
        double nearest = Math.Round(gap / periodMs, MidpointRounding.AwayFromZero);
        if (nearest < 1 || nearest > maxGapCycles) return false;
        double tolerance = Math.Max(config.MinimumTimeToleranceMilliseconds,
            Math.Min(config.MaximumTimeToleranceMilliseconds,
                config.RelativeTimeTolerance * periodMs));
        // Two jittered observed prints can each deviate from their theoretical
        // slot by tolerance. Allow their *combined* discrepancy only.
        return Math.Abs(gap - nearest * periodMs) <= 2 * tolerance;
    }
}
