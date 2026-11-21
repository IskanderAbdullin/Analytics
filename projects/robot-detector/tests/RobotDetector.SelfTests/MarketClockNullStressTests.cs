using System.Text.Json;
using RobotDetector.Core;

namespace RobotDetector.SelfTests;

internal static partial class Program
{
    private static void ClockedNullNoControlledExecution()
    {
        var fixture = MarketClockNullStress.Generate(501, 120);
        Assert(fixture.PublicTape.Trades.Count == 120 &&
               fixture.InjectedExecutionPrintCount == 0 &&
               fixture.DistinctHiddenProducerCount == 0,
            "all clocked-null prints must be synthetic background");
        Assert(fixture.HiddenProducerByEventId.Values.Distinct().Count() == 120,
            "each synthetic background print must have a distinct private producer");
        Assert(fixture.PublicTape.Trades.All(t => t.EventId.Length == 20 &&
               t.EventId.All(Uri.IsHexDigit) &&
               !t.EventId.Contains("background", StringComparison.OrdinalIgnoreCase)),
            "public IDs must be opaque and independent from truth labels");
        Assert(fixture.PublicTape.Trades.GroupBy(t => t.QuantityLots).Count() == 1 &&
               fixture.PublicTape.Trades.All(t => t.ReportedDirection == "SELL"),
            "stress profile shares size/side across independent background prints");

        var scored = BlindExecutionBenchmark.Evaluate(fixture, 501);
        Assert(scored.TrueSyntheticProducerCount == 0 &&
               scored.InjectedExecutionPrints == 0, "zero controlled truth");
        Assert(scored.Models.All(m => m.TruePositivePrints == 0 &&
               m.FalsePositivePrints == m.AttributedPublicPrints &&
               m.EventRecall is null && !m.PhysicalProducerCountInferred),
            "all clocked-null attributions are false positives, not verified robots");
    }

    private static void ClockedNullSummaryConservation()
    {
        var report = MarketClockNullStress.Run(3, 60);
        Assert(report.Trials == 3 && report.Cases.Count == 3 &&
               report.Models.Count == 2 &&
               !report.IdentifiesRealRobotOwners && !report.IsExchangeCalibrated,
            "three seeded trials and two uncalibrated detector variants");
        Assert(report.Cases.All(c => c.PublicPrints == 60 &&
               c.TrueSyntheticProducerCount == 0 && c.InjectedExecutionPrints == 0),
            "null scenario must not contain positive injections");
        foreach (var aggregate in report.Models)
        {
            var matching = report.Cases.SelectMany(c => c.Models)
                .Where(m => m.Model == aggregate.Model).ToArray();
            Assert(aggregate.Trials == 3 &&
                   aggregate.FalsePositivePublicPrints ==
                       matching.Sum(m => m.FalsePositivePrints) &&
                   aggregate.FalseAlarmTrials ==
                       matching.Count(m => m.AttributedPublicPrints > 0) &&
                   aggregate.TrialFalseAlarmFraction ==
                       (double)aggregate.FalseAlarmTrials / aggregate.Trials &&
                   !aggregate.CalibratedMarketFalsePositiveRate,
                "aggregate must exactly conserve independent per-case scores");
        }
    }

    private static void ClockedNullVariableQuantityStress()
    {
        var fixedTape = MarketClockNullStress.Generate(502, 60, clipMode: "fixed");
        var variableTape = MarketClockNullStress.Generate(502, 60, clipMode: "variable");
        Assert(variableTape.PublicTape.Trades.Count == fixedTape.PublicTape.Trades.Count,
            "both modes must preserve the number of public background prints");
        Assert(variableTape.PublicTape.Trades.Select(t => t.QuantityLots).Distinct().Count() == 4 &&
               fixedTape.PublicTape.Trades.Select(t => t.QuantityLots).Distinct().Count() == 1,
            "variable mode should stress a variable-clip detector, not only the fixed model");
        Assert(!variableTape.PublicTape.Trades.Select(t => t.EventId).Intersect(
               fixedTape.PublicTape.Trades.Select(t => t.EventId)).Any(),
            "different null generators must not alias public event identifiers");
        Assert(variableTape.HiddenProducerByEventId.Values.Distinct().Count() == 60 &&
               variableTape.InjectedExecutionPrintCount == 0,
            "variable-size clock null must remain entirely unrelated background");

        var report = MarketClockNullStress.Run(3, 60, clipMode: "variable");
        Assert(report.ClipMode == "variable" && report.Cases.Count == 3 &&
               report.Cases.All(c => c.Kind == "market_clock_variable_null" &&
                   c.TrueSyntheticProducerCount == 0 && c.InjectedExecutionPrints == 0),
            "variable-size null must not invent controlled producer truth");
        Assert(report.Cases.All(c => c.Models.All(m =>
                   m.TruePositivePrints == 0 &&
                   m.FalsePositivePrints == m.AttributedPublicPrints &&
                   m.EventRecall is null)),
            "all candidate evidence remains synthetic background false attribution");

        bool rejected = false;
        try { MarketClockNullStress.Run(1, 20, clipMode: "secret-third-mode"); }
        catch (ArgumentException) { rejected = true; }
        Assert(rejected, "unknown clip mode must fail closed");
    }

    private static void ClockedNullDeterministicAndValidated()
    {
        var first = MarketClockNullStress.Run(2, 45);
        var second = MarketClockNullStress.Run(2, 45);
        Assert(JsonSerializer.Serialize(first) == JsonSerializer.Serialize(second),
            "same synthetic seeds and settings must reproduce exactly");

        bool rejected = false;
        try { MarketClockNullStress.Run(0); }
        catch (ArgumentOutOfRangeException) { rejected = true; }
        Assert(rejected, "zero iterations rejected");

        rejected = false;
        try { MarketClockNullStress.Generate(3, cycles: 3); }
        catch (ArgumentOutOfRangeException) { rejected = true; }
        Assert(rejected, "too few cycles rejected");

        rejected = false;
        try { MarketClockNullStress.Generate(3, periodMilliseconds: 500); }
        catch (ArgumentOutOfRangeException) { rejected = true; }
        Assert(rejected, "too-short scheduling period rejected");

        rejected = false;
        try { MarketClockNullStress.Generate(3, backgroundPrints: 3001); }
        catch (ArgumentOutOfRangeException) { rejected = true; }
        Assert(rejected, "excessive background rejected");
    }
}
