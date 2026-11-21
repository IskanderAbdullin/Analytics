using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace RobotDetector.Core;

/// <summary>
/// Evaluates ABIDES-NG exchange executions using an independently supplied
/// PRIVATE attribution manifest. The market CSV is read by both detectors;
/// private maker/taker identities are used ONLY after detection to score
/// print-level attribution. This does not validate the simulator's realism.
/// </summary>
public static class AbidesBlindEvaluation
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        PropertyNameCaseInsensitive = true
    };

    public sealed record PrivateExecution(
        string EventId, int PassiveAgentId, int AggressiveAgentId);

    public sealed record PrivateManifest(
        string SchemaVersion,
        int Seed,
        string Simulator,
        string SimulatorRevision,
        string InstrumentUid,
        string PublicSha256,
        bool CompleteExecutionAttribution,
        IReadOnlyList<int> ControlledAgentIds,
        IReadOnlyList<PrivateExecution> Events);

    /// <summary>
    /// Post-hoc PRIVATE truth diagnostics. Never passed to any candidate detector.
    /// These numbers describe executed fills, not order submission scheduling.
    /// </summary>
    public sealed record ControlledPrintDiagnostics(
        int PrintCount,
        int DistinctQuantityCount,
        int UniqueExecutionTimestampCount,
        int PrintsSharingTimestamp,
        double? MedianQuantity,
        double? MedianInterprintGapMs,
        double? MedianPositiveInterprintGapMs
    );

    public sealed record Report(
        string SchemaVersion,
        string Simulator,
        string SimulatorRevision,
        int Seed,
        string PublicSha256,
        int PublicPrints,
        int ControlledPrints,
        int BackgroundPrints,
        int ConfiguredControlledAgents,
        int ObservedControlledAgents,
        ControlledPrintDiagnostics PostHocControlledDiagnostics,
        IReadOnlyList<BlindedModelResult> Models,
        bool PhysicalOwnerIdentityKnown,
        bool RealMarketAccuracyCalibrated,
        bool LiveTradingEnabled,
        IReadOnlyList<string> Limitations);

    public static Report Score(string publicCsv, string privateManifest)
    {
        if (string.IsNullOrWhiteSpace(publicCsv) ||
            string.IsNullOrWhiteSpace(privateManifest))
            throw new ArgumentException("Public CSV and private truth paths are required.");
        if (Path.GetFullPath(publicCsv).Equals(Path.GetFullPath(privateManifest),
                StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Public projection and hidden truth cannot share a file.");

        var tape = CsvTradeReader.Read(publicCsv);
        if (tape.RejectedRowTotal != 0 || tape.RejectedRows.Count != 0)
            throw new InvalidDataException("ABIDES public projection has quarantined rows.");
        if (tape.Trades.Count == 0)
            throw new InvalidDataException("No executed public trades to evaluate.");
        if (tape.Trades.Any(t => t.DataKind != "SIMULATED_ABIDES_NG" ||
                                 t.TradeSource != "EXCHANGE"))
            throw new InvalidDataException("Mixed, unverified or non-exchange projection.");

        var json = File.ReadAllText(privateManifest);
        var manifest = JsonSerializer.Deserialize<PrivateManifest>(json, JsonOptions)
            ?? throw new InvalidDataException("Invalid private truth manifest.");
        if (manifest.SchemaVersion != "abides-blind-v1" ||
            manifest.Simulator != "abides-ng" ||
            manifest.Seed < 0 ||
            string.IsNullOrWhiteSpace(manifest.SimulatorRevision) ||
            string.IsNullOrWhiteSpace(manifest.InstrumentUid) ||
            !manifest.CompleteExecutionAttribution ||
            manifest.ControlledAgentIds is null || manifest.Events is null)
            throw new InvalidDataException("Missing required ABIDES private truth provenance.");
        if (manifest.ControlledAgentIds.Any(id => id < 0) ||
            manifest.ControlledAgentIds.Distinct().Count() != manifest.ControlledAgentIds.Count)
            throw new InvalidDataException("Invalid controlled-agent set.");
        if (manifest.PublicSha256.Length != 64 ||
            !manifest.PublicSha256.All(Uri.IsHexDigit) ||
            !manifest.PublicSha256.Equals(tape.FileSha256, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Private truth does not match public CSV SHA-256.");

        var observed = tape.Trades.Select(t => t.EventId).ToHashSet(StringComparer.Ordinal);
        if (observed.Count != tape.Trades.Count)
            throw new InvalidDataException("Duplicate public event ID.");
        if (tape.Trades.Any(t => t.InstrumentUid != manifest.InstrumentUid ||
                                 t.EventId.Length != 32 || !t.EventId.All(Uri.IsHexDigit)))
            throw new InvalidDataException("Invalid instrument or non-opaque event ID.");
        if (manifest.Events.Count != tape.Trades.Count)
            throw new InvalidDataException("Public/private trade counts differ.");

        var control = manifest.ControlledAgentIds.ToHashSet();
        var truth = new Dictionary<string, string>(StringComparer.Ordinal);
        var seenControl = new HashSet<int>();
        foreach (var execution in manifest.Events)
        {
            if (execution is null || string.IsNullOrEmpty(execution.EventId) ||
                execution.PassiveAgentId < 0 || execution.AggressiveAgentId < 0 ||
                !observed.Contains(execution.EventId))
                throw new InvalidDataException("Unmatched or invalid hidden execution event.");

            bool passive = control.Contains(execution.PassiveAgentId);
            bool aggressive = control.Contains(execution.AggressiveAgentId);
            string label;
            if (passive || aggressive)
            {
                int agent = passive ? execution.PassiveAgentId : execution.AggressiveAgentId;
                if (passive) seenControl.Add(execution.PassiveAgentId);
                if (aggressive) seenControl.Add(execution.AggressiveAgentId);
                label = "controlled-" + agent;
            }
            else label = "background-" + execution.EventId;
            if (!truth.TryAdd(execution.EventId, label))
                throw new InvalidDataException("Duplicate hidden execution event.");
        }
        int controlled = truth.Values.Count(x => x.StartsWith("controlled-", StringComparison.Ordinal));
        var fixture = new BlindedMarketFixture(
            tape, truth, seenControl.Count, controlled, "abides-execution");
        var score = BlindExecutionBenchmark.Evaluate(fixture, manifest.Seed);
        var controlledTrades = tape.Trades
            .Where(t => truth[t.EventId].StartsWith("controlled-", StringComparison.Ordinal))
            .OrderBy(t => t.ExchangeTimeUtc)
            .ThenBy(t => t.ArrivalSequence)
            .ToArray();

        static double? Median(double[] sortedValues)
        {
            if (sortedValues.Length == 0) return null;
            Array.Sort(sortedValues);
            int middle = sortedValues.Length / 2;
            return sortedValues.Length % 2 == 1
                ? sortedValues[middle]
                : (sortedValues[middle - 1] + sortedValues[middle]) / 2.0;
        }

        var gaps = controlledTrades.Skip(1)
            .Zip(controlledTrades, (later, earlier) =>
                (later.ExchangeTimeUtc - earlier.ExchangeTimeUtc).TotalMilliseconds)
            .ToArray();
        int uniqueTimes = controlledTrades.Select(t => t.ExchangeTimeUtc)
            .Distinct().Count();
        var diagnostics = new ControlledPrintDiagnostics(
            controlledTrades.Length,
            controlledTrades.Select(t => t.QuantityLots).Distinct().Count(),
            uniqueTimes,
            controlledTrades.GroupBy(t => t.ExchangeTimeUtc)
                .Where(group => group.Count() > 1).Sum(group => group.Count()),
            Median(controlledTrades.Select(t => (double)t.QuantityLots).ToArray()),
            Median(gaps),
            Median(gaps.Where(value => value > 0).ToArray()));

        return new Report("abides-blind-score-v2", manifest.Simulator,
            manifest.SimulatorRevision, manifest.Seed, tape.FileSha256,
            tape.Trades.Count, controlled, tape.Trades.Count - controlled,
            control.Count, seenControl.Count, diagnostics, score.Models,
            false, false, false,
            new[]
            {
                "SIMULATOR_PROVENANCE: filename and manifest claim ABIDES-NG; verify actual run and package revision separately.",
                "PRIVATE_TRUTH: maker/taker agent identifiers were not passed to the detectors.",
                "PUBLIC_SIDE: simulated aggressor direction derived from passive-order side; do not assume real vendor semantics.",
                "PRINT_METRICS_ONLY: event precision and recall are not parent-order or physical owner accuracy.",
                "POST_HOC_DIAGNOSTICS: controlled-fill sizes and timing are private truth diagnostics calculated strictly after the detector outputs.",
                "NULL_TRUTH: when zero controlled prints exist, event recall is null.",
                "NO_MARKET_CALIBRATION: this simulation is not a calibrated MOEX/SPB false-discovery rate.",
                "NO_TRADING: analysis only; neither broker connection nor order placement is supported."
            });
    }
}
