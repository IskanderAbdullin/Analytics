using System.Text.Json;
using RobotDetector.Core;

namespace RobotDetector.SelfTests;

internal static partial class Program
{
    private static void BlindOpaquePublicIdentifiers()
    {
        var scenario = new BlindedMarketScenario("fixed_twap", 2027, 60);
        var generated = BlindExecutionBenchmark.Generate(scenario);
        Assert(generated.PublicTape.Trades.Count == 72, "12 injected + 60 background prints");
        Assert(generated.InjectedExecutionPrintCount == 12 &&
               generated.DistinctHiddenProducerCount == 1, "private one-parent truth");
        Assert(generated.PublicTape.Trades.All(t => t.EventId.Length == 20 &&
               t.EventId.All(Uri.IsHexDigit)), "only opaque hexadecimal public identifiers");
        Assert(generated.PublicTape.Trades.Select(t => t.EventId)
               .Distinct(StringComparer.Ordinal).Count() == generated.PublicTape.Trades.Count,
            "no public source-ID collisions");
        Assert(generated.PublicTape.Trades.All(t =>
               !t.EventId.Contains("parent", StringComparison.OrdinalIgnoreCase) &&
               !t.EventId.Contains("robot", StringComparison.OrdinalIgnoreCase)),
            "public fields do not reveal producer provenance");
    }

    private static void BlindFixedAndVariableClips()
    {
        var fixedTape = BlindExecutionBenchmark.Generate(
            new BlindedMarketScenario("fixed_twap", 42, 0));
        var variableTape = BlindExecutionBenchmark.Generate(
            new BlindedMarketScenario("variable_twap", 43, 0));
        var config = new DetectorConfig();
        var variable = new VariableCadenceConfig();

        var fixedResult = BlindExecutionBenchmark.Evaluate(fixedTape, 42, config, variable);
        var variableResult = BlindExecutionBenchmark.Evaluate(variableTape, 43, config, variable);
        Assert(fixedResult.PublicPrints == 12 &&
               fixedResult.InjectedExecutionPrints == 12, "source and fixed truth counts");
        Assert(fixedResult.Models.Single(x => x.Model == "fixed_quantity").TruePositivePrints >= 6,
            "fixed time/q synthetic prints must be recoverable as candidates");
        Assert(fixedResult.Models.Single(x => x.Model == "variable_quantity").CandidateSequences == 0,
            "experimental variable clip model excludes constant q by design");
        Assert(variableResult.Models.Single(x => x.Model == "variable_quantity").TruePositivePrints >= 8,
            "varying clip cadence synthetic prints should be recovered");
        Assert(variableResult.Models.All(x => !x.PhysicalProducerCountInferred),
            "the synthetic truth label is not leaked as a physical owner claim");
    }

    private static void BlindNullTruthUndefinedRecall()
    {
        var nullTape = BlindExecutionBenchmark.Generate(
            new BlindedMarketScenario("clustered_null", 88, 100));
        Assert(nullTape.InjectedExecutionPrintCount == 0 &&
               nullTape.DistinctHiddenProducerCount == 0,
            "pure clustered null contains no controlled execution program");
        var scored = BlindExecutionBenchmark.Evaluate(nullTape, 88);
        Assert(scored.Models.All(m => m.EventRecall is null),
            "undefined recall denominator must stay null, not 0% or 100%");
        Assert(scored.Models.All(m => m.TruePositivePrints == 0 &&
                   m.FalsePositivePrints == m.AttributedPublicPrints),
            "any detected null events are false positive attributions");
        Assert(scored.PublicPrints == 100, "all clustered null prints remain");
    }

    private static void BlindPartialFills()
    {
        var tape = BlindExecutionBenchmark.Generate(
            new BlindedMarketScenario("partial_fill_twap", 11, 0));
        Assert(tape.InjectedExecutionPrintCount == 24 &&
               tape.PublicTape.Trades.Count == 24, "two child prints per synthetic cycle");
        Assert(tape.PublicTape.Trades.GroupBy(t => t.ExchangeTimeUtc).Count() == 12,
            "simulated two prints share each of 12 timestamps");
        Assert(tape.PublicTape.Trades.Sum(t => t.QuantityLots) == 1200,
            "splitting a parent slice cannot destroy traded volume");
        var result = BlindExecutionBenchmark.Evaluate(tape, 11);
        Assert(result.Models.All(m => m.TruePositivePrints + m.FalsePositivePrints ==
               m.AttributedPublicPrints), "evidence exact conservation");
        Assert(result.Models.All(m => m.MissedInjectedPrints ==
               tape.InjectedExecutionPrintCount - m.TruePositivePrints),
            "all missed injected prints counted");
        Assert(result.Models.All(m => !m.PhysicalProducerCountInferred),
            "partial fills do not reveal the parent identity");
    }

    private static void BlindNonIdentifiability()
    {
        var one = BlindExecutionBenchmark.Generate(
            new BlindedMarketScenario("fixed_twap", 1001, 50));
        var two = BlindExecutionBenchmark.RelabelSamePublicTape(one, 2);
        Assert(one.DistinctHiddenProducerCount == 1 &&
               two.DistinctHiddenProducerCount == 2, "different latent producer assignments");
        Assert(ReferenceEquals(one.PublicTape, two.PublicTape),
            "the observable public tape is byte-for-byte identical");
        Assert(one.PublicTape.Trades.Select(t => t.EventId).SequenceEqual(
               two.PublicTape.Trades.Select(t => t.EventId)), "same public print identifiers");
        var firstResult = BlindExecutionBenchmark.Evaluate(one, 1001);
        var secondResult = BlindExecutionBenchmark.Evaluate(two, 1001);
        Assert(firstResult.TrueSyntheticProducerCount != secondResult.TrueSyntheticProducerCount,
            "hidden ground truth differs");
        Assert(JsonSerializer.Serialize(firstResult.Models) ==
               JsonSerializer.Serialize(secondResult.Models),
            "both detectors MUST produce identical evidence in observationally identical tapes");
        Assert(firstResult.Models.All(m => !m.PhysicalProducerCountInferred),
            "no observation establishes one vs two actual producers");
    }

    private static void BlindNoRealIdentityClaim()
    {
        var report = BlindExecutionBenchmark.Run(seedsPerKind: 1, backgroundPrints: 24);
        Assert(!report.CanInferActualRealWorldRobotOwners && !report.IsABidesExchangeSimulation,
            "limited synthetic experiment must not be sold as exchange-ground truth");
        Assert(report.Results.Count == 4, "all four prespecified scenario classes present");
        Assert(report.Results.Select(r => r.Kind).OrderBy(s => s).SequenceEqual(
            BlindExecutionBenchmark.ScenarioKinds.OrderBy(s => s)),
            "all scenario kinds covered");
        Assert(report.Limitations.Any(s => s.Contains("NON_IDENTIFIABILITY")),
            "describe fundamental observational limit");
        Assert(report.Results.All(r => r.Models.All(m =>
                   !m.PhysicalProducerCountInferred &&
                   m.TruePositivePrints + m.FalsePositivePrints == m.AttributedPublicPrints)),
            "no inferred physical robot counts and internally consistent scoring");
    }

    private static void BlindDeterminism()
    {
        var first = BlindExecutionBenchmark.Run(2, 35);
        var second = BlindExecutionBenchmark.Run(2, 35);
        Assert(first.SeedsPerKind == 2 && first.Cases == 8, "2 seeds times 4 classes");
        Assert(JsonSerializer.Serialize(first) == JsonSerializer.Serialize(second),
            "identical seeds and model parameters must produce identical per-case metrics");
    }

    private static void BlindRejectInvalid()
    {
        bool rejected = false;
        try { BlindExecutionBenchmark.Generate(
            new BlindedMarketScenario("incomplete_config", 7)); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "unknown model kind must fail closed");

        rejected = false;
        try { BlindExecutionBenchmark.Run(0, 10); }
        catch (ArgumentOutOfRangeException) { rejected = true; }
        Assert(rejected, "zero iterations must fail");

        var nullCase = BlindExecutionBenchmark.Generate(
            new BlindedMarketScenario("clustered_null", 8, 10));
        rejected = false;
        try { BlindExecutionBenchmark.RelabelSamePublicTape(nullCase, 2); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "cannot assign synthetic execution owners to a null-only tape");
    }
}
