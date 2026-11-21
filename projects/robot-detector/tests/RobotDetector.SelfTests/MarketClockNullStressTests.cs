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
