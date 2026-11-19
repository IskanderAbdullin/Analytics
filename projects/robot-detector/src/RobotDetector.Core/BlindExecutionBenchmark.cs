using System.Security.Cryptography;
using System.Text;

namespace RobotDetector.Core;

/// <summary>
/// Tiny, seeded, public-projection generator with privately held producer truth.
/// Neither the fixed-size nor variable-size detector receives any agent labels.
/// This is a SCIENTIFIC UNIT TEST sandbox, not a replacement for ABIDES-NG,
/// exchange order queues, Hawkes calibration or real market provenance.
/// </summary>
public sealed record BlindedMarketScenario(
    string Kind, int Seed, int BackgroundPrints = 120,
    int ExpectedAgentCycles = 12, int PeriodMilliseconds = 5000);

public sealed record BlindedMarketFixture(
    TradeImportResult PublicTape,
    IReadOnlyDictionary<string, string> HiddenProducerByEventId,
    int DistinctHiddenProducerCount,
    int InjectedExecutionPrintCount,
    string ScenarioKind
);

public sealed record BlindedModelResult(
    string Model,
    int CandidateSequences,
    int AttributedPublicPrints,
    int TruePositivePrints,
    int FalsePositivePrints,
    int MissedInjectedPrints,
    double? EventPrecision,
    double? EventRecall,
    bool PhysicalProducerCountInferred
);

public sealed record BlindedScenarioResult(
    string Kind,
    int Seed,
    int PublicPrints,
    int InjectedExecutionPrints,
    int TrueSyntheticProducerCount,
    IReadOnlyList<BlindedModelResult> Models
);

public sealed record BlindExecutionBenchmarkReport(
    string SchemaVersion,
    int SeedsPerKind,
    int Cases,
    IReadOnlyList<BlindedScenarioResult> Results,
    bool CanInferActualRealWorldRobotOwners,
    bool IsABidesExchangeSimulation,
    IReadOnlyList<string> Limitations
);

public static class BlindExecutionBenchmark
{
    public static readonly string[] ScenarioKinds =
    {
        "clustered_null",
        "fixed_twap",
        "variable_twap",
        "partial_fill_twap"
    };

    public static BlindedMarketFixture Generate(BlindedMarketScenario scenario)
    {
        if (!ScenarioKinds.Contains(scenario.Kind, StringComparer.Ordinal) ||
            scenario.Seed < 0 || scenario.BackgroundPrints is < 0 or > 3000 ||
            scenario.ExpectedAgentCycles is < 8 or > 100 ||
            scenario.PeriodMilliseconds is < 1000 or > 300000)
            throw new ArgumentException("Unsupported blinded research scenario.");

        var rng = new Random(scenario.Seed);
        var origin = new DateTimeOffset(2026, 11, 19, 7, 0, 0, TimeSpan.Zero);
        var buffer = new List<MarketTrade>(scenario.BackgroundPrints + 2 * scenario.ExpectedAgentCycles);
        var hidden = new Dictionary<string, string>(StringComparer.Ordinal);
        var injected = new HashSet<string>(StringComparer.Ordinal);
        int ordinal = 0;

        void Add(int millis, long quantity, string side, string hiddenProducer)
        {
            if (quantity <= 0 || millis < 0)
                throw new InvalidOperationException("Invalid generated execution.");
            // Public event IDs are deterministic opaque SHA prefixes, not
            // semantic strings such as "robot-1" or "background-3".
            string raw = $"{scenario.Seed}|{ordinal}|opaque_public_trade";
            string id = Convert.ToHexString(
                SHA256.HashData(Encoding.UTF8.GetBytes(raw)))[..20].ToLowerInvariant();
            var trade = new MarketTrade(
                id, origin.AddMilliseconds(millis), "SYNTH-OPQ", "SYNTH",
                "EXCHANGE", side, 100m, quantity, "TQBR", "TEST-DAY-1",
                "SYNTHETIC", ordinal);
            if (!hidden.TryAdd(id, hiddenProducer))
                throw new InvalidOperationException("Generated duplicate opaque event ID.");
            if (hiddenProducer.StartsWith("controlled-", StringComparison.Ordinal))
                injected.Add(id);
            buffer.Add(trade);
            ordinal++;
        }

        long[] sizes = { 25, 50, 75, 100 };
        if (scenario.Kind != "clustered_null")
        {
            for (int i = 0; i < scenario.ExpectedAgentCycles; i++)
            {
                int eventMillis = 1000 + scenario.PeriodMilliseconds * i +
                                  rng.Next(-25, 26);
                if (scenario.Kind == "partial_fill_twap")
                {
                    long firstClip = 40 + (i % 3) * 10;
                    Add(eventMillis, firstClip, "SELL", "controlled-parent-1");
                    Add(eventMillis, 100 - firstClip, "SELL", "controlled-parent-1");
                }
                else
                {
                    long q = scenario.Kind == "fixed_twap" ? 100 : sizes[i % sizes.Length];
                    Add(eventMillis, q, "SELL", "controlled-parent-1");
                }
            }
        }

        // Clustered null: build several short-lived bursts, with an independent
        // background producer per print. It is deliberately NOT a calibrated
        // Hawkes/LOB simulator and may create accidental temporal regularity.
        int horizon = checked((scenario.ExpectedAgentCycles + 3) *
            scenario.PeriodMilliseconds);
        int burstCenters = Math.Max(1, scenario.BackgroundPrints / 12);
        int[] centers = Enumerable.Range(0, burstCenters)
            .Select(_ => rng.Next(0, horizon)).ToArray();
        for (int i = 0; i < scenario.BackgroundPrints; i++)
        {
            int center = centers[rng.Next(centers.Length)];
            int offset = rng.Next(-180, 181);
            int time = Math.Clamp(center + offset, 0, horizon);
            // A fraction of background prints use public-clock boundaries
            // to simulate a market-wide scheduler confounder.
            if (i % 9 == 0)
                time = (time / 1000) * 1000;
            Add(time, sizes[rng.Next(sizes.Length)],
                rng.Next(2) == 0 ? "BUY" : "SELL",
                $"background-{i}");
        }

        buffer.Sort((a, b) =>
        {
            int c = a.ExchangeTimeUtc.CompareTo(b.ExchangeTimeUtc);
            return c != 0 ? c : a.ArrivalSequence.CompareTo(b.ArrivalSequence);
        });
        return new BlindedMarketFixture(
            new TradeImportResult(buffer, Array.Empty<BadRow>(), "blind-synthetic",
                "blind-synthetic-sha:" + scenario.Kind + ":" + scenario.Seed,
                true),
            hidden, hidden.Values.Where(x => x.StartsWith("controlled-",
                StringComparison.Ordinal)).Distinct(StringComparer.Ordinal).Count(),
            injected.Count, scenario.Kind);
    }

    public static BlindedScenarioResult Evaluate(
        BlindedMarketFixture fixture, int seed,
        DetectorConfig? fixedConfig = null, VariableCadenceConfig? variableConfig = null)
    {
        fixedConfig ??= new DetectorConfig();
        variableConfig ??= new VariableCadenceConfig();
        var fixedReport = PeriodicDetector.Detect(fixture.PublicTape, fixedConfig);
        var variableReport = VariableSizeCadence.Detect(fixture.PublicTape, variableConfig);
        var trueIds = fixture.HiddenProducerByEventId
            .Where(x => x.Value.StartsWith("controlled-", StringComparison.Ordinal))
            .Select(x => x.Key).ToHashSet(StringComparer.Ordinal);

        BlindedModelResult Score(string model, int candidates, IEnumerable<string> evidence)
        {
            var publicIds = evidence.ToHashSet(StringComparer.Ordinal);
            if (publicIds.Any(id => !fixture.HiddenProducerByEventId.ContainsKey(id)))
                throw new InvalidDataException("Detector returned an event ID absent in blinded public tape.");
            int truePos = publicIds.Count(trueIds.Contains);
            int falsePos = publicIds.Count - truePos;
            int missed = trueIds.Count - truePos;
            return new BlindedModelResult(model, candidates, publicIds.Count,
                truePos, falsePos, missed,
                publicIds.Count == 0 ? null : (double)truePos / publicIds.Count,
                trueIds.Count == 0 ? null : (double)truePos / trueIds.Count,
                false);
        }

        return new BlindedScenarioResult(fixture.ScenarioKind, seed,
            fixture.PublicTape.Trades.Count, fixture.InjectedExecutionPrintCount,
            fixture.DistinctHiddenProducerCount,
            new[]
            {
                Score("fixed_quantity", fixedReport.CandidatePatternCount,
                    fixedReport.Patterns.SelectMany(p => p.EvidenceEventIds)),
                Score("variable_quantity", variableReport.CandidateSequenceCount,
                    variableReport.Candidates.SelectMany(p => p.EvidenceEventIds))
            });
    }

    public static BlindExecutionBenchmarkReport Run(
        int seedsPerKind = 5, int backgroundPrints = 120)
    {
        if (seedsPerKind is < 1 or > 200)
            throw new ArgumentOutOfRangeException(nameof(seedsPerKind));
        if (backgroundPrints is < 0 or > 3000)
            throw new ArgumentOutOfRangeException(nameof(backgroundPrints));
        var cases = new List<BlindedScenarioResult>();
        foreach (var kind in ScenarioKinds)
        {
            for (int seed = 0; seed < seedsPerKind; seed++)
            {
                var scenario = new BlindedMarketScenario(kind, seed + 1091,
                    backgroundPrints);
                cases.Add(Evaluate(Generate(scenario), scenario.Seed));
            }
        }
        return new BlindExecutionBenchmarkReport(
            "0.1-truth-blinded-simulation", seedsPerKind,
            cases.Count, cases, false, false,
            new[]
            {
                "BLINDED_PROJECTION: detectors only receive MarketTrade public records, not hidden agent labels.",
                "OPAQUE_EVENT_IDS: source ID hashes do not identify the generator; evaluation uses truth after detection.",
                "EVENT_LEVEL_ONLY: precision and recall concern injected synthetic trade prints, not live bot identities.",
                "CLOCKED_AND_CLUSTERED_NULL: the background is seeded and stylized, NOT a validated Hawkes/ABIDES exchange simulator.",
                "PARTIAL_FILLS: two prints can belong to one controlled execution; public data cannot confirm this in real trading.",
                "NON_IDENTIFIABILITY: the same observable public tape admits multiple physical owner assignments.",
                "NO_OUT_OF_SAMPLE_MARKET_ACCURACY: simulated counts may not generalize to MOEX/SPB.",
                "NO_TRADING_RECOMMENDATIONS: candidate models remain uncalibrated and read-only."
            });
    }

    public static BlindedMarketFixture RelabelSamePublicTape(
        BlindedMarketFixture original, int syntheticProducerCount)
    {
        if (syntheticProducerCount is < 1 or > 10 ||
            original.InjectedExecutionPrintCount == 0)
            throw new ArgumentException("Provide a positive synthetic execution tape and 1..10 producers.");
        var mapping = new Dictionary<string, string>(original.HiddenProducerByEventId,
            StringComparer.Ordinal);
        int index = 0;
        foreach (var trade in original.PublicTape.Trades)
        {
            if (mapping[trade.EventId].StartsWith("controlled-", StringComparison.Ordinal))
            {
                mapping[trade.EventId] = $"controlled-parent-{(index % syntheticProducerCount) + 1}";
                index++;
            }
        }
        return original with
        {
            HiddenProducerByEventId = mapping,
            DistinctHiddenProducerCount = syntheticProducerCount
        };
    }
}
