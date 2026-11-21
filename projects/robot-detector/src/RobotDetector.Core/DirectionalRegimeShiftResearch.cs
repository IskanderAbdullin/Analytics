using System.Globalization;

namespace RobotDetector.Core;

/// <summary>
/// Retrospective, bounded, past-baseline-only shifts in the publicly reported
/// BUY proportion of known-side market lots. Does NOT identify metaorders,
/// algorithmic traders, owners or market-calibrated statistical change points.
/// </summary>
public sealed class DirectionalShiftConfig
{
    public int BinSeconds { get; init; } = 30;
    public int ReferenceBins { get; init; } = 6;
    public int MinimumCurrentKnownLots { get; init; } = 100;
    public long MinimumReferenceKnownLots { get; init; } = 500;
    public double MinimumKnownSideFraction { get; init; } = 0.90;
    public double MinimumAbsoluteBuyShareChange { get; init; } = 0.25;
    public int CooldownBins { get; init; } = 2;
    public int MaximumPopulatedBinsPerGroup { get; init; } = 10000;

    public void Validate()
    {
        if (BinSeconds is < 1 or > 3600 ||
            ReferenceBins is < 3 or > 100 ||
            MinimumCurrentKnownLots < 1 ||
            MinimumReferenceKnownLots < MinimumCurrentKnownLots ||
            MinimumKnownSideFraction is < 0.5 or > 1 ||
            MinimumAbsoluteBuyShareChange is <= 0 or > 1 ||
            CooldownBins is < 0 or > 100 ||
            MaximumPopulatedBinsPerGroup < ReferenceBins + 1 ||
            MaximumPopulatedBinsPerGroup > 100000)
            throw new ArgumentException("Invalid public directional regime-shift settings.");
    }
}

public sealed record ObservedDirectionalShift(
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string TradingMode,
    string SessionId,
    string DataKind,
    string CurrentBinStartUtc,
    int ReferenceBins,
    int CurrentPublicPrints,
    long CurrentTotalLots,
    long CurrentKnownSideLots,
    long ReferenceKnownSideLots,
    double ReferenceReportedBuyShare,
    double CurrentReportedBuyShare,
    double SignedReportedBuyShareChange,
    string Direction,
    string State,
    bool PhysicalOwnerIdentified,
    bool SignificanceCalibrated);

public sealed record DirectionalShiftReport(
    string SchemaVersion,
    string SourceSha256,
    int InputPublicPrints,
    int SourceGroups,
    int SkippedDenseSourceGroups,
    int EvaluatedClockBins,
    int UnscorableWarmupOrGapBins,
    int UnscorableSideQualityBins,
    int ClockGapTransitions,
    int CandidateShiftWindows,
    bool PhysicalBotCountKnown,
    bool StatisticalSignificanceEstablished,
    bool SourceCoverageVerified,
    IReadOnlyList<ObservedDirectionalShift> ShiftWindows,
    IReadOnlyList<string> Warnings);

public static class DirectionalRegimeShiftResearch
{
    private sealed class PublicBin
    {
        public long BuyLots;
        public long SellLots;
        public long UnknownLots;
        public int PublicPrints;
        public long Known => checked(BuyLots + SellLots);
        public long Total => checked(Known + UnknownLots);
    }

    public static DirectionalShiftReport Describe(
        TradeImportResult source, DirectionalShiftConfig? config = null)
    {
        config ??= new DirectionalShiftConfig();
        config.Validate();

        if (source.Trades.Select(t => t.EventId).Distinct(StringComparer.Ordinal).Count()
            != source.Trades.Count)
            throw new InvalidDataException("Duplicate public event identity.");
        if (source.Trades.Any(t => t.QuantityLots <= 0 ||
            t.ReportedDirection is not ("BUY" or "SELL" or "UNKNOWN")))
            throw new InvalidDataException("Invalid public lot size or reported direction.");

        int groups = 0, skipped = 0, evaluated = 0, unscorable = 0, poorSide = 0, gaps = 0;
        var shifts = new List<ObservedDirectionalShift>();
        foreach (var sourceGroup in source.Trades
            .GroupBy(t => (t.InstrumentUid, t.Ticker, t.TradeSource,
                           t.TradingMode, t.SessionId, t.DataKind))
            .OrderBy(g => g.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(g => g.Key.Ticker, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(g => g.Key.TradingMode, StringComparer.Ordinal)
            .ThenBy(g => g.Key.SessionId, StringComparer.Ordinal)
            .ThenBy(g => g.Key.DataKind, StringComparer.Ordinal))
        {
            var bins = new SortedDictionary<long, PublicBin>();
            foreach (var trade in sourceGroup)
            {
                long ordinal = Math.DivRem(trade.ExchangeTimeUtc.ToUnixTimeSeconds(),
                    config.BinSeconds, out long remainder);
                if (remainder < 0) ordinal--; // UTC bins even before Unix epoch.
                if (!bins.TryGetValue(ordinal, out var bin))
                {
                    bin = new PublicBin();
                    bins.Add(ordinal, bin);
                }
                checked
                {
                    bin.PublicPrints++;
                    if (trade.ReportedDirection == "BUY") bin.BuyLots += trade.QuantityLots;
                    else if (trade.ReportedDirection == "SELL") bin.SellLots += trade.QuantityLots;
                    else bin.UnknownLots += trade.QuantityLots;
                }
            }
            if (bins.Count == 0) continue;
            groups++;
            if (bins.Count > config.MaximumPopulatedBinsPerGroup)
            {
                skipped++;
                continue; // Never sample an overlarge group or claim total coverage.
            }

            var prior = new Queue<PublicBin>();
            long? previousOrdinal = null;
            long? lastAlertOrdinal = null;
            foreach (var (ordinal, bin) in bins)
            {
                if (previousOrdinal is not null && ordinal != previousOrdinal + 1)
                {
                    prior.Clear();
                    gaps++;
                }
                previousOrdinal = ordinal;

                if (bin.Known < config.MinimumCurrentKnownLots ||
                    (double)bin.Known / bin.Total < config.MinimumKnownSideFraction)
                {
                    prior.Clear();
                    poorSide++;
                    continue; // Do not borrow incomplete-side or tiny bins as baselines.
                }

                if (prior.Count != config.ReferenceBins)
                {
                    unscorable++;
                }
                else
                {
                    long priorBuy = 0, priorKnown = 0;
                    foreach (var window in prior)
                    {
                        checked
                        {
                            priorBuy += window.BuyLots;
                            priorKnown += window.Known;
                        }
                    }
                    if (priorKnown >= config.MinimumReferenceKnownLots)
                    {
                        evaluated++;
                        double baselineShare = (double)priorBuy / priorKnown;
                        double currentShare = (double)bin.BuyLots / bin.Known;
                        double change = currentShare - baselineShare;
                        if (Math.Abs(change) >= config.MinimumAbsoluteBuyShareChange &&
                            (lastAlertOrdinal is null || ordinal - lastAlertOrdinal.Value > config.CooldownBins))
                        {
                            shifts.Add(new ObservedDirectionalShift(
                                sourceGroup.Key.InstrumentUid, sourceGroup.Key.Ticker,
                                sourceGroup.Key.TradeSource, sourceGroup.Key.TradingMode,
                                sourceGroup.Key.SessionId, sourceGroup.Key.DataKind,
                                DateTimeOffset.FromUnixTimeSeconds(checked(ordinal * (long)config.BinSeconds))
                                    .ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
                                config.ReferenceBins, bin.PublicPrints, bin.Total,
                                bin.Known, priorKnown, baselineShare, currentShare,
                                change, change > 0 ? "reported_buy_share_increase" :
                                    "reported_buy_share_decrease",
                                "unvalidated_public_directional_shift", false, false));
                            lastAlertOrdinal = ordinal;
                        }
                    }
                    else unscorable++;
                }

                prior.Enqueue(bin);
                if (prior.Count > config.ReferenceBins) prior.Dequeue();
            }
        }

        return new DirectionalShiftReport(
            "0.1-public-directional-shift", source.FileSha256, source.Trades.Count,
            groups, skipped, evaluated, unscorable, poorSide, gaps, shifts.Count,
            false, false, source.HasVerifiedFeedCoverage, shifts,
            new[]
            {
                "NOT_OWNER_IDENTIFICATION: anonymous reported-side share changes do not identify metaorders, algorithms or physical bots.",
                "RETROSPECTIVE_BINS: all windows use observed file contents; the terminal source bin might be incomplete and is not independently verified.",
                "DIRECTION_PROVIDER_REPORTED: BUY/SELL meanings depend on the public data source.",
                "KNOWN_SIDE_QUALITY: incomplete or unknown-side dominated clock bins reset the baseline.",
                "MISSING_CLOCK_GAP_RESETS: absence of prints is not assumed to be a zero-volume bin or full feed coverage.",
                "UNCALIBRATED_HEURISTIC: thresholds, cooldown and data-dependent repeated screening have no calibrated false-alarm probability.",
                "REGIME_CONFOUNDERS: sessions, auctions, price moves, unrelated traders, volume shocks and feed changes can produce identical labels.",
                "NOT_BAYESIAN_CUSUM: this is a simple past-window proportion-shift screen, not BOCPD, CUSUM or a proven sequential test.",
                "NO_REAL_TRADING: read-only public print analytics, no broker account access, private agent identities or order placement."
            });
    }
}
