using System.Security.Cryptography;
using System.Text.Json;
using RobotDetector.Core;

namespace RobotDetector.SelfTests;

internal static partial class Program
{
    private static (string Directory, string Public, string Truth) MakeAbidesProjection(
        bool withControlled = true)
    {
        string root = Path.Combine(Path.GetTempPath(), "rd-abides-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        string csvPath = Path.Combine(root, "public.csv");
        string jsonPath = Path.Combine(root, "private.json");
        var lines = new List<string>
        {
            "TRADE_TS,INSTRUMENT_UID,DIRECTION,PRICE,QUANTITY,TRADE_SOURCE,EVENT_ID,TICKER,TRADING_MODE,SESSION_ID,DATA_KIND"
        };
        var labels = new List<object>();
        for (int index = 0; index < 12; index++)
        {
            string eventId = index.ToString("x32");
            var when = new DateTimeOffset(2026, 11, 19, 7, 0, 0, TimeSpan.Zero)
                .AddSeconds(index * 5);
            lines.Add($"{when:yyyy-MM-ddTHH:mm:ss.fffZ},ABIDES-ABM,BUY,100.50,100,EXCHANGE,{eventId},ABM,SIM-LOB,2026-11-19,SIMULATED_ABIDES_NG");
            labels.Add(new
            {
                event_id = eventId,
                passive_agent_id = index < 8 ? 7 : 55,
                aggressive_agent_id = 99
            });
        }
        File.WriteAllText(csvPath, string.Join("\n", lines) + "\n");
        string sha = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(csvPath))).ToLowerInvariant();
        var manifest = new
        {
            schema_version = "abides-blind-v1",
            seed = 19,
            simulator = "abides-ng",
            simulator_revision = "unit-test-fake",
            instrument_uid = "ABIDES-ABM",
            public_sha256 = sha,
            complete_execution_attribution = true,
            controlled_agent_ids = withControlled ? new[] { 7 } : Array.Empty<int>(),
            events = labels
        };
        File.WriteAllText(jsonPath, JsonSerializer.Serialize(manifest));
        return (root, csvPath, jsonPath);
    }

    private static void AbidesPrivateTruthScoring()
    {
        var x = MakeAbidesProjection();
        try
        {
            string publicText = File.ReadAllText(x.Public).ToLowerInvariant();
            Assert(!publicText.Contains("agent") && !publicText.Contains("controlled"),
                "public projection must not contain privileged producer identities");
            var report = AbidesBlindEvaluation.Score(x.Public, x.Truth);
            Assert(report.PublicPrints == 12 &&
                   report.ControlledPrints == 8 &&
                   report.BackgroundPrints == 4 &&
                   report.ConfiguredControlledAgents == 1 &&
                   report.ObservedControlledAgents == 1,
                "hidden event-truth and public print counts must be exact");
            Assert(!report.PhysicalOwnerIdentityKnown &&
                   !report.RealMarketAccuracyCalibrated && !report.LiveTradingEnabled,
                "private synthetic identities must not be marketed as real identities");
            Assert(report.PostHocControlledDiagnostics.PrintCount == 8 &&
                   report.PostHocControlledDiagnostics.DistinctQuantityCount == 1 &&
                   report.PostHocControlledDiagnostics.UniqueExecutionTimestampCount == 8 &&
                   report.PostHocControlledDiagnostics.PrintsSharingTimestamp == 0 &&
                   report.PostHocControlledDiagnostics.MedianQuantity == 100 &&
                   report.PostHocControlledDiagnostics.MedianInterprintGapMs == 5000,
                "private post-hoc diagnostics must preserve exact controlled-fill timing");
            Assert(report.Models.Count == 2 &&
                   report.Models.All(m => m.TruePositivePrints + m.FalsePositivePrints ==
                       m.AttributedPublicPrints &&
                       m.MissedInjectedPrints + m.TruePositivePrints == 8),
                "both detector scoring paths conserve hidden synthetic truth");
        }
        finally { Directory.Delete(x.Directory, recursive: true); }
    }

    private static void AbidesNullRecallUndefined()
    {
        var x = MakeAbidesProjection(withControlled: false);
        try
        {
            var result = AbidesBlindEvaluation.Score(x.Public, x.Truth);
            Assert(result.PostHocControlledDiagnostics.PrintCount == 0 &&
                   result.PostHocControlledDiagnostics.MedianQuantity is null &&
                   result.PostHocControlledDiagnostics.MedianInterprintGapMs is null,
                "null source has no private controlled timing diagnostics");
            Assert(result.ControlledPrints == 0 &&
                   result.ConfiguredControlledAgents == 0 &&
                   result.Models.All(m => m.TruePositivePrints == 0 &&
                      m.EventRecall is null &&
                      m.FalsePositivePrints == m.AttributedPublicPrints),
                "pure ABIDES background must not have an injected TP denominator");
        }
        finally { Directory.Delete(x.Directory, recursive: true); }
    }

    private static void AbidesIntegrityRejectsTampering()
    {
        var x = MakeAbidesProjection();
        try
        {
            var original = File.ReadAllText(x.Public);
            File.WriteAllText(x.Public, original.Replace("100.50", "100.51"));
            bool rejected = false;
            try { _ = AbidesBlindEvaluation.Score(x.Public, x.Truth); }
            catch (InvalidDataException) { rejected = true; }
            Assert(rejected, "modified public tape must fail SHA reconciliation");
            File.WriteAllText(x.Public, original);

            var originalTruth = File.ReadAllText(x.Truth);
            using (var parsed = JsonDocument.Parse(originalTruth))
            {
                var root = parsed.RootElement;
                var events = root.GetProperty("events").EnumerateArray()
                    .Select(e => new {
                        event_id = e.GetProperty("event_id").GetString(),
                        passive_agent_id = e.GetProperty("passive_agent_id").GetInt32(),
                        aggressive_agent_id = e.GetProperty("aggressive_agent_id").GetInt32()
                    }).ToArray();
                events[1] = events[0];
                var corrupt = new {
                    schema_version = "abides-blind-v1",
                    seed = 19, simulator = "abides-ng", simulator_revision = "unit-test-fake",
                    instrument_uid = "ABIDES-ABM",
                    public_sha256 = root.GetProperty("public_sha256").GetString(),
                    complete_execution_attribution = true,
                    controlled_agent_ids = new[] { 7 },
                    events
                };
                File.WriteAllText(x.Truth, JsonSerializer.Serialize(corrupt));
            }
            rejected = false;
            try { _ = AbidesBlindEvaluation.Score(x.Public, x.Truth); }
            catch (InvalidDataException) { rejected = true; }
            Assert(rejected, "duplicate private event must fail closed");
            File.WriteAllText(x.Truth, originalTruth);

            rejected = false;
            try { _ = AbidesBlindEvaluation.Score(x.Public, x.Public); }
            catch (InvalidDataException) { rejected = true; }
            Assert(rejected, "private truth must be a distinct file");
        }
        finally { Directory.Delete(x.Directory, recursive: true); }
    }
}
