using RobotDetector.Core;

namespace RobotDetector.SelfTests;

internal static partial class Program
{
    private static MarketTrade[] ClockTape(
        string prefix, string source = "EXCHANGE", string mode = "TQBR",
        string session = "SESSION-A", int count = 120, int phaseMs = 20)
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        return Enumerable.Range(0, count).Select(i =>
            new MarketTrade($"{prefix}-{i}", start.AddSeconds(i).AddMilliseconds(phaseMs),
                "CLOCK-TEST", "CLOCK", source, "SELL", 100m, 10,
                mode, session, "SYNTHETIC", i)).ToArray();
    }

    private static void ClockPhaseConcentrated()
    {
        var tape = From(ClockTape("ROUND"));
        var report = ClockPhaseAudit.Analyse(tape,
            new ClockPhaseConfig { NullTrials = 99, Seed = 42 });
        Assert(report.SourceGroups == 1 && report.EligibleSourceGroups == 1,
            "two-minute source should support a clock-phase control");
        var group = report.Groups.Single();
        Assert(group.PublicPrintCount == 120 && group.UtcMinuteBlocks == 2,
            "the same public print total should be retained");
        Assert(group.PrintsInFirstMilliseconds == 120 &&
            group.ObservedFirstPhaseShare == 1, "every synthetic print hits the first 100ms");
        Assert(group.PhaseHistogram100Ms[0] == 120 &&
            group.PhaseHistogram100Ms.Skip(1).All(x => x == 0),
            "phase histogram bins should reconcile");
        Assert(group.RotatedControlCounts.Count == 99 && group.NullMeanFirstPhaseShare < 0.5,
            "minute rotations reduce alignment while preserving local bursts");
        Assert(!report.OwnerCountKnown && !report.StatisticalSignificanceEstablished,
            "market-level clock synchronization is not a bot count");
    }

    private static void ClockPhaseEvenlyDistributed()
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var trades = Enumerable.Range(0, 50).Select(i =>
            new MarketTrade($"EQUAL-{i}", start.AddMinutes(i / 10)
                    .AddMilliseconds(50 + (i % 10) * 100),
                "CLOCK-TEST", "CLOCK", "EXCHANGE", "BUY", 100m, 10,
                "TQBR", "SESSION-A", "SYNTHETIC", i)).ToArray();
        var report = ClockPhaseAudit.Analyse(From(trades),
            new ClockPhaseConfig { NullTrials = 49, MinPrintsPerGroup = 20 });
        var g = report.Groups.Single();
        Assert(g.PublicPrintCount == 50 && g.UtcMinuteBlocks == 5, "five minutes");
        Assert(g.PhaseHistogram100Ms.All(x => x == 5), "exactly five prints in each 100ms phase");
        Assert(Math.Abs(g.ObservedFirstPhaseShare - 0.1) < 1e-12,
            "uniform histogram should have exactly 10% within first 100ms");
        Assert(Math.Abs(g.NullMeanFirstPhaseShare!.Value - 0.1) < 1e-12,
            "minute rotations of evenly-spaced 100ms phases should remain uniform");
    }

    private static void ClockPhaseSourceSeparation()
    {
        var a = ClockTape("EX", "EXCHANGE", "TQBR", "SESSION-A", 120);
        var b = ClockTape("DL", "DEALER", "TQBR", "SESSION-A", 120);
        var c = ClockTape("AM", "EXCHANGE", "OTHER", "SESSION-A", 120);
        var d = ClockTape("DAY", "EXCHANGE", "TQBR", "SESSION-B", 120);
        var report = ClockPhaseAudit.Analyse(From(a.Concat(b).Concat(c).Concat(d).ToArray()),
            new ClockPhaseConfig { NullTrials = 5, MinPrintsPerGroup = 20 });
        Assert(report.SourceGroups == 4 && report.EligibleSourceGroups == 4,
            "EXCHANGE, DEALER, trading mode and session must be separate");
        Assert(report.Groups.Sum(x => x.PublicPrintCount) == 480,
            "no source prints may disappear or be doubled");
        Assert(report.Groups.All(x => x.PrintsInFirstMilliseconds == 120),
            "each group retains the original absolute second phase");
    }

    private static void ClockPhaseInsufficient()
    {
        var report = ClockPhaseAudit.Analyse(From(ClockTape("SHORT", count: 4)),
            new ClockPhaseConfig { NullTrials = 10, MinPrintsPerGroup = 5 });
        Assert(report.SourceGroups == 1 && report.IneligibleSourceGroups == 1,
            "insufficient or single-minute group cannot be treated as a controlled finding");
        var g = report.Groups.Single();
        Assert(!g.EligibleForControls && g.NullMeanFirstPhaseShare is null &&
            g.Null95FirstPhaseShare is null && g.DescriptiveGlobalTailFrequency is null &&
            g.RotatedControlCounts.Count == 0, "unscorable control result remains null");
    }

    private static void ClockPhaseDeterministic()
    {
        var tape = From(ClockTape("REPRO", count: 180));
        var a = ClockPhaseAudit.Analyse(tape,
            new ClockPhaseConfig { NullTrials = 21, Seed = 700 });
        var b = ClockPhaseAudit.Analyse(tape,
            new ClockPhaseConfig { NullTrials = 21, Seed = 700 });
        Assert(a.Groups.Single().RotatedControlCounts.SequenceEqual(
            b.Groups.Single().RotatedControlCounts), "same seed yields identical control distribution");
        Assert(a.Groups.Single().DescriptiveGlobalTailFrequency ==
            b.Groups.Single().DescriptiveGlobalTailFrequency, "same descriptive comparison");
    }

    private static void ClockPhaseBoundaryPrecision()
    {
        var start = new DateTimeOffset(2026, 11, 18, 7, 0, 0, TimeSpan.Zero);
        var a = ClockTape("BOUND", count: 4);
        a[0] = a[0] with { ExchangeTimeUtc = start.AddMilliseconds(99).AddTicks(9000) };
        a[1] = a[1] with { ExchangeTimeUtc = start.AddSeconds(1).AddMilliseconds(100) };
        a[2] = a[2] with { ExchangeTimeUtc = start.AddSeconds(2).AddMilliseconds(0) };
        a[3] = a[3] with { ExchangeTimeUtc = start.AddSeconds(3).AddMilliseconds(999) };
        var report = ClockPhaseAudit.Analyse(From(a),
            new ClockPhaseConfig { MinPrintsPerGroup = 1, NullTrials = 2 });
        var g = report.Groups.Single();
        Assert(g.PrintsInFirstMilliseconds == 2 && g.PhaseHistogram100Ms[0] == 2,
            "99.9ms and 0ms included, exactly 100ms and 999ms excluded");
        Assert(g.PhaseHistogram100Ms[1] == 1 && g.PhaseHistogram100Ms[9] == 1,
            "the edges map to expected phase bins");
        Assert(!g.EligibleForControls, "single minute has no independent minute-phase comparison");
    }

    private static void ClockPhaseValidation()
    {
        bool refused = false;
        try { ClockPhaseAudit.Analyse(From(ClockTape("X")),
            new ClockPhaseConfig { FirstMilliseconds = 501 }); }
        catch (ArgumentException) { refused = true; }
        Assert(refused, "invalid clock threshold rejected");
        refused = false;
        try { ClockPhaseAudit.Analyse(From(ClockTape("X")),
            new ClockPhaseConfig { NullTrials = 0 }); }
        catch (ArgumentException) { refused = true; }
        Assert(refused, "zero repetitions rejected");
        var report = ClockPhaseAudit.Analyse(From(ClockTape("OTHER")),
            new ClockPhaseConfig { NullTrials = 3 });
        Assert(report.Groups.All(x => !x.FeedCoverageVerified) &&
               !report.StatisticalSignificanceEstablished && !report.OwnerCountKnown,
            "historical CSV cannot be promoted to complete-feed or owner-level truth");
    }
}
