using System.Text.Json;
using RobotDetector.Core;

namespace RobotDetector.SelfTests;

internal static partial class Program
{
    private static MarketTrade[] VolumeResponseRows(int count = 12, int missingBin = -1)
    {
        var first = new DateTimeOffset(2026, 11, 19, 7, 0, 0, TimeSpan.Zero);
        var items = new List<MarketTrade>();
        for (int bin = 0; bin < count; bin++)
        {
            if (bin == missingBin) continue;
            long total = (bin + 1) * 100L;
            long buy = 40L * bin;
            long sell = total - buy;
            if (buy > 0)
                items.Add(new MarketTrade($"VOL-B-{bin}", first.AddSeconds(30 * bin),
                    "UID-VOLUME", "VOL", "EXCHANGE", "BUY", 100m,
                    buy, "SIM", "S1", "SYNTHETIC", items.Count));
            items.Add(new MarketTrade($"VOL-S-{bin}", first.AddSeconds(30 * bin),
                "UID-VOLUME", "VOL", "EXCHANGE", "SELL", 100m,
                sell, "SIM", "S1", "SYNTHETIC", items.Count));
        }
        return items.ToArray();
    }

    private static void VolumeResponsePerfectLagAndConservation()
    {
        var events = VolumeResponseRows();
        var result = VolumeResponseResearch.Describe(From(events), new VolumeResponseConfig());
        Assert(result.InputPublicPrints == events.Length && result.EvaluatedSourceGroups == 1 &&
               result.SkippedDenseGroups == 0 && result.SideProfiles.Count == 2 &&
               result.Observations.Count == 11,
            "expected a single instrument, source and session with 11 adjacent bins");
        Assert(result.Observations.Sum(x => x.CurrentPublicPrints) == events.Length - 1,
            "all rows except the first reference bin must be counted once");
        var buy = result.SideProfiles.Single(x => x.ReportedDirection == "BUY");
        Assert(buy.PublicPrintsForSide == 11 && buy.ObservedLotsForSide == 2640,
            "directional print and lot conservation");
        Assert(buy.EligibleAdjacentPairs == 11 && buy.UnobservedClockTransitions == 0 &&
               buy.SpearmanPreviousMarketLotsToCurrentSideLots is > 0.999999 &&
               buy.MedianCurrentSideLotsOverPreviousMarketLots is > 0.399999 and < 0.400001,
            "positive public lag association should be measured without source labels");
        Assert(!result.PhysicalBotCountKnown && !result.StatisticalSignificanceEstablished &&
               !buy.OwnerIdentityKnown && !buy.SignificanceCalibrated,
            "positive synthetic public correlation does not prove a trading agent");
        Assert(result.Warnings.Any(x => x.Contains("MARKET_WIDE_CONFOUND")),
            "risk of market-wide autocorrelation must be explicit");
    }

    private static void VolumeResponseMissingBinsNotZeroImputed()
    {
        var output = VolumeResponseResearch.Describe(From(VolumeResponseRows(missingBin: 5)));
        Assert(output.SideProfiles.All(x => x.PopulatedClockBins == 11 &&
               x.EligibleAdjacentPairs == 9 && x.UnobservedClockTransitions == 1),
            "a gap must break lagged pairing, never be zero-imputed");
        Assert(output.Observations.Count == 9 &&
               output.Observations.All(x =>
                   DateTimeOffset.Parse(x.CurrentBinStartUtc) -
                   DateTimeOffset.Parse(x.PreviousBinStartUtc) == TimeSpan.FromSeconds(30)),
            "all emitted predictors must refer to exactly the previous completed bin");
    }

    private static void VolumeResponseFutureDoesNotRewritePastObservations()
    {
        var a = VolumeResponseResearch.Describe(From(VolumeResponseRows(10)));
        var b = VolumeResponseResearch.Describe(From(VolumeResponseRows(12)));
        Assert(a.Observations.Count == 9 && b.Observations.Count == 11,
            "two later bins create exactly two later observations");
        Assert(a.Observations.SequenceEqual(b.Observations.Take(9)),
            "new later public prints cannot change prior-bin volume/side observations");
    }

    private static void VolumeResponseNullAndSeparateSource()
    {
        var constant = VolumeResponseRows().Where(x => x.ReportedDirection == "SELL")
            .Select(x => x with { QuantityLots = 100 }).ToArray();
        var result = VolumeResponseResearch.Describe(From(constant));
        Assert(result.SideProfiles.All(x =>
               x.SpearmanPreviousMarketLotsToCurrentSideLots is null),
            "no spurious rank coefficient when lagged volume or reported side never varies");

        var first = VolumeResponseRows();
        var other = first.Select(x => x with {
            EventId = "OTHER-" + x.EventId, InstrumentUid = "UID-SECOND",
            Ticker = "V2", SessionId = "S2",
        }).ToArray();
        var combined = VolumeResponseResearch.Describe(From(first.Concat(other).Reverse().ToArray()));
        Assert(combined.EvaluatedSourceGroups == 2 &&
               combined.SideProfiles.Count == 4 && combined.Observations.Count == 22 &&
               combined.SideProfiles.All(x => x.ObservedLotsForSide > 0) &&
               combined.Observations.All(x =>
                   x.InstrumentUid == "UID-VOLUME" ? x.SessionId == "S1" : x.SessionId == "S2"),
            "separate source/session identities must never share lagged market exposure");
        var ordered = VolumeResponseResearch.Describe(From(first.Concat(other).ToArray()));
        Assert(JsonSerializer.Serialize(combined) == JsonSerializer.Serialize(ordered),
            "public observation order must not depend on input arrival order");
    }

    private static void VolumeResponseRefuseDuplicatesAndUnsafeBounds()
    {
        var first = VolumeResponseRows();
        bool duplicate = false;
        try
        {
            _ = VolumeResponseResearch.Describe(From(first.Append(first[0]).ToArray()));
        }
        catch (InvalidDataException) { duplicate = true; }
        Assert(duplicate, "same public event ID twice must be rejected");

        var dense = VolumeResponseResearch.Describe(From(first),
            new VolumeResponseConfig { MinimumAdjacentPairs = 3, MaxPopulatedBinsPerGroup = 9 });
        Assert(dense.SkippedDenseGroups == 1 && dense.SideProfiles.Count == 0 &&
               dense.Observations.Count == 0 &&
               dense.Warnings.Any(x => x.StartsWith("OVERSIZE_GROUP_NOT_EVALUATED")),
            "overlarge group must fail closed, not silently truncate the sample");

        bool invalid = false;
        try { _ = VolumeResponseResearch.Describe(From(first),
            new VolumeResponseConfig { BinSeconds = 0 }); }
        catch (ArgumentException) { invalid = true; }
        Assert(invalid, "invalid bin size must be rejected");
    }
}
