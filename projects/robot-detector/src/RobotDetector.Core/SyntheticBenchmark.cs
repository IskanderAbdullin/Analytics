namespace RobotDetector.Core;

/// <summary>
/// Publicly observable, synthetic trade tape and private ground truth kept in
/// separate records. Noise is intentionally simple; its metrics are NOT
/// calibrated estimates for real exchanges.
/// </summary>
public sealed record SyntheticScenario(
    int Seed, int Robots, int RobotCycles, int PeriodMs, long QuantityLots,
    int NoiseTrades, int JitterMs, int SessionLengthMs
);

public sealed record SyntheticTape(
    TradeImportResult PublicTrades,
    IReadOnlySet<string> InjectedTradeIds,
    int TrueGeneratorCount
);

public sealed record SyntheticTrialResult(
    int Seed, int TrueGeneratorCount, int CandidatePatterns,
    int AttributedEvents, int CorrectlyAttributedEvents, int TotalInjectedEvents,
    double EventPrecision, double EventRecall, bool PhysicalCountInferred
);

public sealed record SyntheticBenchmarkReport(
    string SchemaVersion, int NumberOfTrials, int InjectedTrials, int NullTrials,
    double MeanEventPrecisionOnInjected, double MeanEventRecallOnInjected,
    double MeanCandidateCountOnInjected, double MeanFalseCandidateCountOnNull,
    IReadOnlyList<SyntheticTrialResult> Trials,
    IReadOnlyList<string> Limitations
);

public static class SyntheticBenchmark
{
    public static SyntheticTape Generate(SyntheticScenario scenario)
    {
        if (scenario.Robots < 0 || scenario.Robots > 20 || scenario.RobotCycles < 1 ||
            scenario.PeriodMs < 200 || scenario.QuantityLots <= 0 ||
            scenario.NoiseTrades < 0 || scenario.NoiseTrades > 1_000_000 ||
            scenario.JitterMs < 0 || scenario.SessionLengthMs <= scenario.PeriodMs * (long)scenario.RobotCycles)
            throw new ArgumentException("Invalid synthetic scenario.");

        var random = new Random(scenario.Seed);
        var zero = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var events = new List<MarketTrade>();
        var trueIds = new HashSet<string>(StringComparer.Ordinal);
        long sequence = 0;
        for (int robot = 0; robot < scenario.Robots; robot++)
        {
            for (int k = 0; k < scenario.RobotCycles; k++)
            {
                int jitter = scenario.JitterMs == 0 ? 0 : random.Next(-scenario.JitterMs, scenario.JitterMs + 1);
                int time = 1000 + robot * 350 + scenario.PeriodMs * k + jitter;
                string id = $"SYN-R{robot}-{k}";
                trueIds.Add(id);
                events.Add(new MarketTrade(id, zero.AddMilliseconds(time), "SYNTH-BENCH",
                    "SYNTH", "EXCHANGE", "SELL", 100m, scenario.QuantityLots, "TQBR",
                    "SYNTH-DAY-1", "SYNTHETIC", sequence++));
            }
        }

        for (int i = 0; i < scenario.NoiseTrades; i++)
        {
            int time = random.Next(scenario.SessionLengthMs);
            // Preserves a small population of sizes; occasional collisions with
            // robot sizes are intentionally possible.
            long q = random.Next(1, 101) * 10L;
            string side = random.Next(2) == 0 ? "BUY" : "SELL";
            events.Add(new MarketTrade($"SYN-BG-{i}", zero.AddMilliseconds(time),
                "SYNTH-BENCH", "SYNTH", "EXCHANGE", side, 100m, q, "TQBR",
                "SYNTH-DAY-1", "SYNTHETIC", sequence++));
        }

        events.Sort((a, b) =>
        {
            int c = a.ExchangeTimeUtc.CompareTo(b.ExchangeTimeUtc);
            return c != 0 ? c : a.ArrivalSequence.CompareTo(b.ArrivalSequence);
        });
        return new SyntheticTape(new TradeImportResult(events, Array.Empty<BadRow>(),
            "generated", $"synthetic:{scenario.Seed}", true), trueIds, scenario.Robots);
    }

    public static SyntheticTrialResult Evaluate(SyntheticTape scenario, DetectorConfig config, int seed)
    {
        var report = PeriodicDetector.Detect(scenario.PublicTrades, config);
        var assigned = report.Patterns.SelectMany(p => p.EvidenceEventIds)
            .ToHashSet(StringComparer.Ordinal);
        int truePos = assigned.Count(scenario.InjectedTradeIds.Contains);
        double precision = assigned.Count == 0 ? 0 : (double)truePos / assigned.Count;
        double recall = scenario.InjectedTradeIds.Count == 0 ? 0 :
            (double)truePos / scenario.InjectedTradeIds.Count;
        return new SyntheticTrialResult(seed, scenario.TrueGeneratorCount, report.CandidatePatternCount,
            assigned.Count, truePos, scenario.InjectedTradeIds.Count, precision, recall,
            report.PhysicalBotCountKnown);
    }

    public static SyntheticBenchmarkReport Run(int seeds, DetectorConfig config, int noiseTrades = 200)
    {
        if (seeds < 1 || seeds > 2000) throw new ArgumentOutOfRangeException(nameof(seeds));
        var trials = new List<SyntheticTrialResult>(2 * seeds);
        for (int seed = 1; seed <= seeds; seed++)
        {
            foreach (int robots in new[] { 0, 1 })
            {
                var sc = new SyntheticScenario(seed * 2 + robots, robots, 12, 5000,
                    100, noiseTrades, 25, 70_000);
                trials.Add(Evaluate(Generate(sc), config, sc.Seed));
            }
        }
        var positive = trials.Where(t => t.TrueGeneratorCount > 0).ToArray();
        var nulls = trials.Where(t => t.TrueGeneratorCount == 0).ToArray();
        return new SyntheticBenchmarkReport(
            "0.1-experimental", trials.Count, positive.Length, nulls.Length,
            positive.Average(t => t.EventPrecision), positive.Average(t => t.EventRecall),
            positive.Average(t => t.CandidatePatterns),
            nulls.Average(t => t.CandidatePatterns),
            trials,
            new[]
            {
                "UNVALIDATED: simulation noise is simplified and does not model full exchange microstructure.",
                "These are candidate-pattern screening metrics, not calibrated bot-detection probabilities.",
                "One trading program can generate several streams; multiple programs can generate one stream.",
                "The evaluator sees hidden IDs only AFTER the screen has run on a public projection."
            });
    }
}
