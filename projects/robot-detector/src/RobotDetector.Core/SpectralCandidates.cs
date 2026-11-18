using System.Numerics;

namespace RobotDetector.Core;

/// <summary>
/// Independent clock-time spectral screen. Unlike event-index FFT, the input
/// series is binned by UTC. Peaks are only candidate periods, never bot IDs.
/// Implemented with an in-place radix-2 FFT, without third-party dependencies.
/// </summary>
public sealed record SpectralPeak(
    string InstrumentUid, string TradeSource, string ReportedDirection,
    string SessionId, string Feature, int BinMs, int ObservedBinCount,
    double FrequencyHz, double CandidatePeriodMs, double SpectralPower,
    double ObservedCycles, bool IsPeriodResolutionAdequate
);
public sealed record SpectralReport(
    string SchemaVersion, int AnalysedGroups, IReadOnlyList<SpectralPeak> Peaks,
    IReadOnlyList<string> Warnings
);

public static class SpectralCandidates
{
    public static SpectralReport Analyse(TradeImportResult input,
        int binMs = 500, int maximumBins = 262144, int topPeaks = 8, double thresholdSigma = 3.0)
    {
        if (binMs < 10 || maximumBins < 64 || topPeaks < 1 || thresholdSigma < 0)
            throw new ArgumentException("Invalid spectrum options.");
        var peaks = new List<SpectralPeak>();
        var warnings = new List<string>
        {
            "SPECTRAL_PEAK_IS_NOT_BOT: market-wide clock synchronisation and harmonics can create peaks.",
            "NO_SIGNIFICANCE: sigma threshold is a heuristic, not a calibrated probability.",
            "NO_OWNER_IDENTITY: cannot infer actual participant count."
        };
        int groups = 0;
        foreach (var group in input.Trades
                     .Where(t => t.ReportedDirection is "BUY" or "SELL")
                     .GroupBy(t => (t.InstrumentUid, t.TradeSource, t.ReportedDirection,
                                    t.TradingMode, t.SessionId)))
        {
            var list = group.OrderBy(t => t.ExchangeTimeUtc).ToList();
            if (list.Count < 6) continue;
            groups++;
            long firstMs = list[0].ExchangeTimeUtc.ToUnixTimeMilliseconds();
            long lastMs = list[^1].ExchangeTimeUtc.ToUnixTimeMilliseconds();
            long originMs = (firstMs / binMs) * binMs;
            long countLong = (lastMs - originMs) / binMs + 1;
            if (countLong > maximumBins)
            {
                warnings.Add($"SPECTRUM_WINDOW_TOO_LONG uid={group.Key.InstrumentUid}, bins={countLong}");
                continue;
            }
            if (countLong < 32)
            {
                warnings.Add($"SPECTRUM_WINDOW_TOO_SHORT uid={group.Key.InstrumentUid}, bins={countLong}");
                continue;
            }
            int count = checked((int)countLong);
            var counts = new double[count];
            var lots = new double[count];
            foreach (var trade in list)
            {
                int index = checked((int)((trade.ExchangeTimeUtc.ToUnixTimeMilliseconds() - originMs) / binMs));
                counts[index]++;
                lots[index] += trade.QuantityLots;
            }
            FindPeaks(counts, "trade_count", group.Key.InstrumentUid, group.Key.TradeSource,
                group.Key.ReportedDirection, group.Key.SessionId, binMs, topPeaks,
                thresholdSigma, peaks);
            FindPeaks(lots, "lots", group.Key.InstrumentUid, group.Key.TradeSource,
                group.Key.ReportedDirection, group.Key.SessionId, binMs, topPeaks,
                thresholdSigma, peaks);
        }
        return new SpectralReport("0.1-experimental", groups, peaks, warnings.Distinct().ToList());
    }

    private static void FindPeaks(double[] observations, string feature,
        string uid, string source, string side, string session, int binMs,
        int top, double sigma, List<SpectralPeak> result)
    {
        int m = observations.Length;
        int n = 1;
        while (n < m) n <<= 1;
        var signal = new Complex[n];

        // Linear least-squares detrending, then Hann taper on observed samples.
        double sumY = 0, sumXY = 0;
        for (int i = 0; i < m; i++)
        {
            sumY += observations[i];
            sumXY += i * observations[i];
        }
        double sumX = m * (m - 1.0) / 2.0;
        double sumX2 = m * (m - 1.0) * (2.0 * m - 1) / 6.0;
        double denominator = m * sumX2 - sumX * sumX;
        double slope = denominator == 0 ? 0 : (m * sumXY - sumX * sumY) / denominator;
        double intercept = (sumY - slope * sumX) / m;
        for (int i = 0; i < m; i++)
        {
            double window = 0.5 * (1 - Math.Cos(2 * Math.PI * i / (m - 1)));
            signal[i] = new Complex((observations[i] - (intercept + slope * i)) * window, 0);
        }

        FftInPlace(signal);
        int half = n / 2;
        var powers = new double[half + 1];
        double mean = 0;
        for (int k = 1; k <= half; k++)
        {
            powers[k] = 2 * signal[k].Magnitude * signal[k].Magnitude / (m * (double)m);
            mean += powers[k];
        }
        mean /= half;
        double variance = 0;
        for (int k = 1; k <= half; k++)
            variance += (powers[k] - mean) * (powers[k] - mean);
        double threshold = mean + sigma * Math.Sqrt(variance / half);
        var selected = Enumerable.Range(1, half)
            .Where(k => powers[k] > threshold &&
                        (k == 1 || powers[k] >= powers[k - 1]) &&
                        (k == half || powers[k] >= powers[k + 1]))
            .OrderByDescending(k => powers[k]).Take(top);

        foreach (int k in selected)
        {
            double hz = (1000.0 * k) / (n * binMs);
            double periodMs = 1000.0 / hz;
            double observedCycles = (m * (double)binMs) / periodMs;
            // Three cycles are only a spectral identifiability floor;
            // a separate detector/holdout must confirm any stream.
            result.Add(new SpectralPeak(uid, source, side, session, feature,
                binMs, m, hz, periodMs, powers[k], observedCycles, observedCycles >= 3));
        }
    }

    private static void FftInPlace(Complex[] values)
    {
        int n = values.Length;
        if (n < 2 || (n & (n - 1)) != 0)
            throw new ArgumentException("FFT length must be a power of two.");
        for (int i = 1, j = 0; i < n; i++)
        {
            int bit = n >> 1;
            while ((j & bit) != 0)
            {
                j ^= bit;
                bit >>= 1;
            }
            j ^= bit;
            if (i < j) (values[i], values[j]) = (values[j], values[i]);
        }
        for (int length = 2; length <= n; length <<= 1)
        {
            var step = Complex.FromPolarCoordinates(1, -2 * Math.PI / length);
            for (int i = 0; i < n; i += length)
            {
                Complex weight = Complex.One;
                for (int k = 0; k < length / 2; k++)
                {
                    Complex u = values[i + k];
                    Complex v = values[i + k + length / 2] * weight;
                    values[i + k] = u + v;
                    values[i + k + length / 2] = u - v;
                    weight *= step;
                }
            }
        }
    }
}
