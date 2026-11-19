using System.Globalization;

namespace RobotDetector.Core;

/// <summary>
/// Deterministic, read-only event-time replay with a bounded pending queue.
/// ArrivalSequence simulates receipt order for archives; it is NOT measured
/// network latency or proof of a complete live feed.
/// </summary>
public sealed class ReplayAuditConfig
{
    public int AllowedLatenessMilliseconds { get; init; } = 500;
    public int MaximumPendingEvents { get; init; } = 10_000;
    public int WindowMinutes { get; init; } = 5;
    public string ReceiptOrdering { get; init; } = "archive_row";

    public void Validate()
    {
        if (AllowedLatenessMilliseconds is < 0 or > 600_000 ||
            MaximumPendingEvents is < 16 or > 1_000_000 ||
            WindowMinutes is < 1 or > 1440 ||
            ReceiptOrdering is not ("archive_row" or "exchange_time_ideal"))
            throw new ArgumentException("Replay lateness, pending queue or window parameters invalid.");
    }
}

public sealed record ReplayObservedWindow(
    string InstrumentUid,
    string Ticker,
    string TradeSource,
    string TradingMode,
    string SessionId,
    string WindowStartUtc,
    int PublicPrints,
    long ObservedLots,
    long ReportedBuyLots,
    long ReportedSellLots,
    long UnknownDirectionLots,
    string FirstObservedEventUtc,
    string LastObservedEventUtc
);

public sealed record ReplayAuditReport(
    string SchemaVersion,
    string SourceSha256,
    int InputPrints,
    int ReplayedPrints,
    long ReplayedLots,
    int OutOfOrderArrivalCount,
    int LateAfterWatermarkCount,
    int ForcedQueueFlushCount,
    int MaximumPendingObserved,
    int MaximumPendingAllowed,
    int PopulatedWindows,
    int WindowMinutes,
    int AllowedLatenessMilliseconds,
    bool SourceCoverageVerified,
    bool HasActualNetworkReceiveTimestamps,
    bool AnyPrintsDropped,
    bool ActualBotCountKnown,
    IReadOnlyList<ReplayObservedWindow> Windows,
    IReadOnlyList<string> Warnings,
    string ReceiptOrdering = "archive_row"
);

public static class BoundedEventReplay
{
    private sealed class WindowState
    {
        public string Ticker = "";
        public int PrintCount;
        public long Lots;
        public long Buy;
        public long Sell;
        public long Unknown;
        public DateTimeOffset? First;
        public DateTimeOffset? Last;

        public void Add(MarketTrade t)
        {
            PrintCount = checked(PrintCount + 1);
            Lots = checked(Lots + t.QuantityLots);
            switch (t.ReportedDirection)
            {
                case "BUY": Buy = checked(Buy + t.QuantityLots); break;
                case "SELL": Sell = checked(Sell + t.QuantityLots); break;
                default: Unknown = checked(Unknown + t.QuantityLots); break;
            }
            First = First.HasValue && First.Value <= t.ExchangeTimeUtc
                ? First : t.ExchangeTimeUtc;
            Last = Last.HasValue && Last.Value >= t.ExchangeTimeUtc
                ? Last : t.ExchangeTimeUtc;
            Ticker = t.Ticker;
        }
    }

    /// <summary>
    /// Replays rows in ArrivalSequence order. No file/network reads here.
    /// Buffered events are emitted at watermark; queue overflow forces earliest
    /// emissions and is counted, never silently dropped. All windows remain
    /// correct as commutative aggregates even when late prints appear.
    /// </summary>
    public static ReplayAuditReport Analyse(TradeImportResult input, ReplayAuditConfig? config = null)
    {
        config ??= new ReplayAuditConfig();
        config.Validate();

        long graceTicks = checked((long)config.AllowedLatenessMilliseconds *
            TimeSpan.TicksPerMillisecond);
        long windowTicks = checked((long)config.WindowMinutes * TimeSpan.TicksPerMinute);
        var queue = new PriorityQueue<MarketTrade, (long Ticks, long ArrivalOrdinal)>();
        var states = new Dictionary<
            (string InstrumentUid, string TradeSource, string Mode, string SessionId, long WindowIndex),
            WindowState>();
        long? maximumObservedTicks = null;
        long? lastArrivalTicks = null;
        int seen = 0, replayed = 0, outOfOrder = 0, tooLate = 0,
            forced = 0, maxPending = 0;
        long lots = 0;

        void Emit(MarketTrade trade)
        {
            if (trade.QuantityLots <= 0)
                throw new InvalidDataException("Public trade quantity is not positive.");
            long ticks = trade.ExchangeTimeUtc.ToUniversalTime().Ticks;
            long index = ticks / windowTicks;
            var key = (trade.InstrumentUid, trade.TradeSource, trade.TradingMode,
                trade.SessionId, index);
            if (!states.TryGetValue(key, out var state))
            {
                state = new WindowState();
                states.Add(key, state);
            }
            state.Add(trade);
            replayed = checked(replayed + 1);
            lots = checked(lots + trade.QuantityLots);
        }

        void FlushThrough(long watermark)
        {
            while (queue.TryPeek(out _, out var key) && key.Ticks <= watermark)
                Emit(queue.Dequeue());
        }

        // The *original row sequence* is retained by the importer as
        // ArrivalSequence; its Sorted Trades property may have been reordered
        // into exchange-time order for historical analysis.
        var orderedInput = config.ReceiptOrdering == "archive_row"
            ? input.Trades.OrderBy(t => t.ArrivalSequence)
                .ThenBy(t => t.EventId, StringComparer.Ordinal)
            : input.Trades.OrderBy(t => t.ExchangeTimeUtc)
                .ThenBy(t => t.ArrivalSequence);
        foreach (var t in orderedInput)
        {
            long ticks = t.ExchangeTimeUtc.ToUniversalTime().Ticks;
            long precedingWatermark = maximumObservedTicks.HasValue
                ? Math.Max(0, maximumObservedTicks.Value - graceTicks)
                : 0;
            if (lastArrivalTicks.HasValue && ticks < lastArrivalTicks.Value)
                outOfOrder = checked(outOfOrder + 1);
            if (maximumObservedTicks.HasValue && ticks < precedingWatermark)
                tooLate = checked(tooLate + 1);
            lastArrivalTicks = ticks;
            maximumObservedTicks = maximumObservedTicks.HasValue
                ? Math.Max(maximumObservedTicks.Value, ticks) : ticks;

            queue.Enqueue(t, (ticks, seen));
            seen = checked(seen + 1);
            FlushThrough(Math.Max(0, maximumObservedTicks.Value - graceTicks));

            // If a malicious or anomalous source sends unlimited same-time
            // records, keep memory bounded without dropping source evidence.
            while (queue.Count > config.MaximumPendingEvents)
            {
                Emit(queue.Dequeue());
                forced = checked(forced + 1);
            }
            maxPending = Math.Max(maxPending, queue.Count);
        }

        while (queue.Count != 0) Emit(queue.Dequeue());
        var windows = states.OrderBy(k => k.Key.InstrumentUid, StringComparer.Ordinal)
            .ThenBy(k => k.Key.TradeSource, StringComparer.Ordinal)
            .ThenBy(k => k.Key.Mode, StringComparer.Ordinal)
            .ThenBy(k => k.Key.SessionId, StringComparer.Ordinal)
            .ThenBy(k => k.Key.WindowIndex)
            .Select(k =>
            {
                var key = k.Key;
                var v = k.Value;
                string windowStart = new DateTimeOffset(
                    checked(key.WindowIndex * windowTicks), TimeSpan.Zero)
                    .ToUniversalTime().ToString("O", CultureInfo.InvariantCulture);
                return new ReplayObservedWindow(
                    key.InstrumentUid, v.Ticker, key.TradeSource,
                    key.Mode, key.SessionId, windowStart,
                    v.PrintCount, v.Lots, v.Buy, v.Sell, v.Unknown,
                    v.First!.Value.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture),
                    v.Last!.Value.ToUniversalTime().ToString("O", CultureInfo.InvariantCulture));
            }).ToArray();

        if (replayed != input.Trades.Count || windows.Sum(x => x.PublicPrints) != replayed ||
            windows.Sum(x => x.ObservedLots) != lots ||
            windows.Any(w => w.ReportedBuyLots + w.ReportedSellLots + w.UnknownDirectionLots != w.ObservedLots))
            throw new InvalidDataException("Replay does not conserve source prints/quantity.");
        if (maxPending > config.MaximumPendingEvents)
            throw new InvalidDataException("Replay buffer exceeded configured hard cap.");

        var warnings = new List<string>
        {
            config.ReceiptOrdering == "archive_row"
                ? "ARCHIVE_ROW_ORDER: source row order is NOT actual network delivery time; late counts reflect file ordering artifacts."
                : "EXCHANGE_TIME_IDEAL: artificially sorted by market timestamps; zero late events here are not evidence of a fast live feed.",
            "EVENT_TIME_WATERMARK: records older than max-event-time minus lateness are flagged, not silently dropped.",
            "FORCED_FLUSH_WARNING: queue pressure may emit events before watermark; counts still correct but ordering guarantees are reduced.",
            "COVERAGE_NOT_PROVEN: neither sorted receipt order nor an error-free archive proves full market delivery.",
            "WINDOWS_NOT_A_SESSION_CALENDAR: missing clock windows do not imply the market was inactive.",
            "NO_OWNER_BOT_INFERENCE: output has no parent order or actual bot identities.",
            "READ_ONLY: this accumulator makes no network, broker account or trading requests."
        };
        if (forced > 0)
            warnings.Add($"QUEUE_PRESSURE: forced {forced} early event emissions, no prints discarded.");
        if (tooLate > 0)
            warnings.Add($"LATE_PRINTS: {tooLate} public prints arrived after the event-time watermark.");
        return new ReplayAuditReport(
            "0.1-bounded-event-replay", input.FileSha256, input.Trades.Count,
            replayed, lots, outOfOrder, tooLate, forced, maxPending,
            config.MaximumPendingEvents, windows.Length, config.WindowMinutes,
            config.AllowedLatenessMilliseconds, input.HasVerifiedFeedCoverage,
            false, false, false, windows, warnings, config.ReceiptOrdering);
    }
}
