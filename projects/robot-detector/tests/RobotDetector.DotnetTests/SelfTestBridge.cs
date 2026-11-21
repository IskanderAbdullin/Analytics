using System.Reflection;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace RobotDetector.DotnetTests;

/// <summary>
/// VSTest wrapper around the original no-NuGet console self-tests.
/// This assembly is optional and never uses broker APIs.
/// </summary>
[TestClass]
public sealed class SelfTestBridge
{
    [TestMethod]
    public void UpstreamDeterministicSuitePasses()
    {
        var assembly = Assembly.Load("RobotDetector.SelfTests");
        var type = assembly.GetType("RobotDetector.SelfTests.Program", throwOnError: true)!;
        const BindingFlags flags = BindingFlags.Static | BindingFlags.NonPublic;
        var main = type.GetMethod("Main", flags)
            ?? throw new InvalidOperationException("Upstream self-test entry point missing.");
        var passed = type.GetField("_passed", flags)
            ?? throw new InvalidOperationException("Upstream passed counter missing.");
        var failed = type.GetField("_failed", flags)
            ?? throw new InvalidOperationException("Upstream failed counter missing.");
        passed.SetValue(null, 0);
        failed.SetValue(null, 0);
        main.Invoke(null, null);
        int passedCount = (int)passed.GetValue(null)!;
        int failedCount = (int)failed.GetValue(null)!;
        Assert.AreEqual(0, failedCount, "Upstream deterministic tests failed.");
        Assert.IsTrue(passedCount >= 123,
            $"Expected at least 123 registered upstream checks but only {passedCount} passed.");
    }
}
