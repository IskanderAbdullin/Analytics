namespace RobotDetector.Core;

/// <summary>
/// Observed best-quote oscillation signature, not proof of a particular
/// algorithm, iceberg, trader, or any illegal practice.
/// </summary>
public sealed record BestQuote(
    DateTimeOffset TimeUtc, string InstrumentUid, decimal Bid, decimal Ask, decimal TickSize,
    long BidLots, long AskLots
);
public sealed record QuoteOscillationResult(
    int Observations, decimal AskCarry, decimal AskNetMove,
    decimal BidCarry, decimal BidNetMove, decimal AskNormalized,
    decimal BidNormalized, int AskReversals, int BidReversals,
    string Classification, bool CoverageVerified, bool PhysicalBotCountKnown
);
public static class QuoteOscillation
{
    public static QuoteOscillationResult Calculate(IReadOnlyList<BestQuote> quotes, bool coverageVerified)
    {
        if (quotes.Count < 2) throw new ArgumentException("At least two quotes are needed.");
        string uid = quotes[0].InstrumentUid;
        decimal tick = quotes[0].TickSize;
        if (tick <= 0) throw new ArgumentException("Tick size must be positive.");
        if (quotes.Any(q => q.InstrumentUid != uid || q.TickSize != tick ||
                            q.Ask <= 0 || q.Bid <= 0 || q.Ask < q.Bid))
            throw new ArgumentException("Incompatible or invalid best quotes.");
        for (int i = 1; i < quotes.Count; i++)
            if (quotes[i].TimeUtc <= quotes[i - 1].TimeUtc)
                throw new ArgumentException("Quote observations must have strictly increasing times.");
        decimal askCarry = 0, bidCarry = 0;
        int askReversals = 0, bidReversals = 0;
        int askDirection = 0, bidDirection = 0;
        for (int i = 1; i < quotes.Count; i++)
        {
            decimal askDelta = quotes[i].Ask - quotes[i - 1].Ask;
            decimal bidDelta = quotes[i].Bid - quotes[i - 1].Bid;
            askCarry += Math.Abs(askDelta);
            bidCarry += Math.Abs(bidDelta);
            int nextAskDir = Math.Sign(askDelta);
            int nextBidDir = Math.Sign(bidDelta);
            if (nextAskDir != 0)
            {
                if (askDirection != 0 && nextAskDir != askDirection) askReversals++;
                askDirection = nextAskDir;
            }
            if (nextBidDir != 0)
            {
                if (bidDirection != 0 && nextBidDir != bidDirection) bidReversals++;
                bidDirection = nextBidDir;
            }
        }
        decimal askNet = Math.Abs(quotes[^1].Ask - quotes[0].Ask);
        decimal bidNet = Math.Abs(quotes[^1].Bid - quotes[0].Bid);
        decimal askNorm = askCarry / Math.Max(tick, askNet);
        decimal bidNorm = bidCarry / Math.Max(tick, bidNet);
        string kind = askReversals >= 2 && bidReversals >= 2 ? "both_quote_oscillation_observed" :
            askReversals >= 2 ? "ask_only_quote_oscillation_observed" :
            bidReversals >= 2 ? "bid_only_quote_oscillation_observed" : "no_repeated_reversal";
        return new QuoteOscillationResult(quotes.Count, askCarry, askNet, bidCarry, bidNet,
            askNorm, bidNorm, askReversals, bidReversals, kind, coverageVerified, false);
    }
}
