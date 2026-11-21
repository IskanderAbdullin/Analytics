# Windows local build and test

This standalone `.NET 10` solution is in `projects/robot-detector/RobotDetector.slnx`.

```powershell
dotnet build RobotDetector.slnx
dotnet test RobotDetector.slnx
```

The upstream deterministic self-tests are a standalone executable with no NuGet dependencies. The **optional** `tests/RobotDetector.DotnetTests` project provides an MSTest/VSTest bridge, so `dotnet test` actually invokes the console checks instead of misleadingly exiting successfully without discovering tests. It uses `Microsoft.NET.Test.Sdk 17.14.1`, `MSTest.TestAdapter 3.7.3` and `MSTest.TestFramework 3.7.3`; the Core, CLI, Server and original console self-tests remain NuGet-free. The VSTest summary shows **one adapter test**; that adapter runs the complete internal console suite (at least 116 checks in the baseline, plus new stress checks). It fails if any inner check fails.

Verified on the user's Windows PC-Agent 2026-11-21: .NET SDK 10.0.402; solution build succeeded with 0 warnings and 0 errors; `dotnet test` found and passed the adapter, which executes the inner checks. This is a **local synthetic test**, not a live market data, browser/GUI, T-Invest account or trading integration.

For a **dependency-free** run (from repository project root) use:

```powershell
dotnet run --project tests/RobotDetector.SelfTests
```

This launches only deterministic offline checks. It is not a broker connection or trading robot.

For the new Stage 2 false-attribution control:

```powershell
dotnet run --project src/RobotDetector.Cli -- benchmark-clock-null --trials 20 --background-prints 120 --output data/results/clock-null.json
```

This produces JSON describing a deliberately adversarial common-clock **negative** background. The resulting false-alarm fraction is not a real market false-discovery probability. [Protocol](CLOCKED_NULL_STRESS.md).
