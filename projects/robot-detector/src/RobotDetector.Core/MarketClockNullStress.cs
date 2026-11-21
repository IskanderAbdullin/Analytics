using System.Security.Cryptography;
using System.Text;

namespace RobotDetector.Core;

/// <summary>
/// Public-clock negative control: all prints are anonymous and independently
/// generated, while shared timestamps, sizes, and sides mimic a trading cadence.
/// This is deliberately adversarial, not a calibrated exchange simulation.
/// </summary>
public static class MarketClockNullStress
{
    public sealed record ModelSummary(
        string Model,
        int Trials,
        int FalseAlarmTrials,
        int FalsePositivePublicPrints,
        double TrialFalseAlarmFraction,
        bool CalibratedMarketFalsePositiveRate
    );

    public sealed record Report(
        string SchemaVersion,
        int Trials,
        int BackgroundPrintsPerTrial,
        int PeriodMilliseconds,
        int Cycles,
        string ClipMode,
        IReadOnlyList<BlindedScenarioResult> Cases,
        IReadOnlyList<ModelSummary> Models,
        bool IdentifiesRealRobotOwners,
        bool IsExchangeCalibrated,
        IReadOnlyList<string> Limitations
    );

    public static BlindedMarketFixture Generate(int seed, int backgroundPrints = 120,
        int cycles = 12, int periodMilliseconds = 5000,
        string clipMode = "fixed")
    {
        if (clipMode is not ("fixed" or "variable"))
            throw new ArgumentException("clipMode must be fixed or variable.", nameof(clipMode));
        if (seed < 0 || backgroundPrints is < 0 or > 3000 ||
            cycles is < 8 or > 100 || periodMilliseconds is < 1000 or > 300000)
            throw new ArgumentOutOfRangeException(nameof(seed),
                "Unsupported market-clock null settings.");

        var rng = new Random(seed);
        var origin = new DateTimeOffset(2026, 11, 19, 7, 0, 0, TimeSpan.Zero);
        var trades = new List<MarketTrade>(backgroundPrints);
        var truth = new Dictionary<string, string>(StringComparer.Ordinal);
        for (int index = 0; index < backgroundPrints; index++)
        {
            int slot = index % cycles;
            int timestamp = checked(1000 + slot * periodMilliseconds) +
                            rng.Next(-25, 26);
            string id = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(
                $"clocked-null-v2|{clipMode}|{seed}|{index}")))[..20].ToLowerInvariant();
            long quantity = clipMode == "variable" ?
                25L * ((slot % 4) + 1) : 100L;
            trades.Add(new MarketTrade(id, origin.AddMilliseconds(timestamp),
                "CLOCK-NULL", "SYNTH", "EXCHANGE", "SELL",
                100m, quantity, "TQBR", "TEST-DAY-1", "SYNTHETIC", index));
            truth.Add(id, $"background-{index}");
        }
        trades.Sort((a, b) =>
        {
            int comparison = a.ExchangeTimeUtc.CompareTo(b.ExchangeTimeUtc);
            return comparison != 0 ? comparison : a.ArrivalSequence.CompareTo(b.ArrivalSequence);
        });

        return new BlindedMarketFixture(
            new TradeImportResult(trades, Array.Empty<BadRow>(), "clocked-null",
                $"synthetic-market-clock-null:{clipMode}:{seed}", true),
            truth, 0, 0,
            clipMode == "fixed" ? "market_clock_null" : "market_clock_variable_null");
    }

    public static Report Run(int trials = 20, int backgroundPrints = 120,
        int cycles = 12, int periodMilliseconds = 5000,
        string clipMode = "fixed")
    {
        if (trials is < 1 or > 100)
            throw new ArgumentOutOfRangeException(nameof(trials));
        // Validate even an empty-background run before creating any output.
        _ = Generate(21001, 0, cycles, periodMilliseconds, clipMode);
        if (backgroundPrints is < 0 or > 3000)
            throw new ArgumentOutOfRangeException(nameof(backgroundPrints));

        var cases = new List<BlindedScenarioResult>(trials);
        for (int i = 0; i < trials; i++)
        {
            int seed = 21001 + i;
            cases.Add(BlindExecutionBenchmark.Evaluate(
                Generate(seed, backgroundPrints, cycles, periodMilliseconds, clipMode), seed));
        }
        var models = cases.SelectMany(c => c.Models)
            .GroupBy(m => m.Model, StringComparer.Ordinal)
            .OrderBy(g => g.Key, StringComparer.Ordinal)
            .Select(g => new ModelSummary(g.Key, g.Count(),
                g.Count(m => m.AttributedPublicPrints > 0),
                g.Sum(m => m.FalsePositivePrints),
                (double)g.Count(m => m.AttributedPublicPrints > 0) / g.Count(),
                false))
            .ToArray();

        return new Report("0.2-synthetic-clock-negative-control", trials,
            backgroundPrints, periodMilliseconds, cycles, clipMode, cases, models,
            false, false,
            new[]
            {
                "INDEPENDENT_BACKGROUND: each public print has a different private synthetic producer.",
                "GLOBAL_SCHEDULER: deliberately shared interval/size/side can mimic an execution algorithm.",
                "CLIP_MODE: fixed or periodic variable quantities are imposed market-wide without a repeat producer.",
                "NO_CONTROLLED_EXECUTIONS: true positive and recall denominators are absent.",
                "NOT_ABIDES: no matching engine, book queue, Hawkes calibration or empirical volume model.",
                "NO_SIGNIFICANCE_CLAIMS: false-alarm trial fraction is descriptive for these toy seeds only.",
                "NO_MARKET_IDENTITY_OR_SIGNAL: real-world owners and trading profit remain unidentifiable."
            });
    }
}
