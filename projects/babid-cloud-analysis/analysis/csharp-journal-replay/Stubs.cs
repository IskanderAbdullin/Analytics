using System.Text.Json;

namespace Babid01;

// Compile-only shims for source symbols outside this narrow Journal test;
// never call persistence or broker methods. Tests use Journal(path: null).
public sealed class PnlState { }

public sealed class ConfigException(string message) : Exception(message) { }

public static class AtomicFile
{
    public static JsonSerializerOptions Json { get; } = new();
    public static T? ReadJson<T>(string path) =>
        throw new NotSupportedException("Persistence is not part of this synthetic test.");
    public static void WriteAllText(string path, string text) =>
        throw new NotSupportedException("Persistence is not part of this synthetic test.");
}
