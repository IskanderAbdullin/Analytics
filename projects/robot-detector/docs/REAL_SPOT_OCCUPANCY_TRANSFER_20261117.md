# Preregistered 5+ public-print occupancy controls — LTC/BCH 2026-11-17

The original **LTCUSDT/BCHUSDT 2026-11-20** source transfer
failed its across-two-instruments preregistered envelope test:
LTCUSDT exceeded all 8 strong-null controls, but BCHUSDT did
not. The result was frozen and documented without editing
the threshold or asset sample after observing the failure.

To test a specific proposed explanation, **before any acquisition
of a separate previously unseen archived UTC day** we froze
[`research/real_spot_occupancy_precommit_20261121.json`](../research/real_spot_occupancy_precommit_20261121.json)
in commit **`c64303eac0aa9da8ee9de97f8af4381bbd7fcd1f`**:

- **2026-11-17 UTC** spot raw public trades in exactly
  `LTCUSDT` and `BCHUSDT`, with fixed original eight
  seeded **same-size same-timestamp cluster-side-vector**
  within-minute permutations.
- Primary outcome: at origin **0 seconds** with complete
  **30-second bins containing at least FIVE** actual public
  prints, count the all-BUY or all-SELL bins. For *each*
  instrument, compare observed count with the **maximum**
  of eight fixed strong-control permutations, recording
  any failure without changing anything afterward.
- Fixed mutually exclusive occupancy strata: exactly
  **1, 2, 3–4, 5–9, 10+** prints per complete 30-second
  bin. All 0/10/20s phase changes are secondary sensitivity.
- The day 17 is a distinct **previously uninspected historical
  archive**, *earlier* than days 18–20 development evidence.
  It is **not forward-chronological validation**. Both
  assets on the same date share macro market conditions.

[Original **successful** source-verified GitHub Actions
#44921288804](https://github.com/IskanderAbdullin/Analytics/actions/runs/44921288804)
ran deterministic source-negative tests **before** either
download, matched the official Binance Vision provider
ZIP SHA256 and checked exact day, source and null
population conservation.

| UTC day and symbol | Real public executions | Official source ZIP SHA256 |
|---|---:|---|
| 2026-11-17 LTCUSDT | **107,788** | `2b17c1d697815615bcd15c42119ec40ae8c918da85373afc8f573ecfca85a6ce` |
| 2026-11-17 BCHUSDT | **42,678** | `dca1e3983106d787d10a80e6a8a6b7fd9dc4866afef6ea25379e065abdae1b53` |

Combined **150,466 genuine source public prints**, no
observed ID gaps inside the original provider daily files.
Provider checksum confirms identity of published archives
but **not independent completeness** of the matching engine.

## Original predeclared 5+ one-sided 30-second bin results

| Instrument | Fixed phase | Eligible 5+ bins | Observed one-sided 5+ | Strong null 8-shuffle min / median / max | Observed above all 8? |
|---|---:|---:|---:|---|---|
| LTCUSDT | **0s primary** | 2,827 | **133** | 88 / 98.5 / 103 | **YES** |
| LTCUSDT | 10s | 2,835 | 127 | 87 / 94.5 / 104 | Yes |
| LTCUSDT | 20s | 2,834 | 138 | 75 / 92.5 / 100 | Yes |
| BCHUSDT | **0s primary** | 2,025 | **504** | 502 / 509.5 / 519 | **NO** |
| BCHUSDT | 10s | 2,012 | 495 | 476 / 503.5 / 537 | No |
| BCHUSDT | 20s | 2,003 | 503 | 473 / 488.5 / 500 | Yes (secondary only) |

**The preregistered across-instrument primary FAILS again.**
LTCUSDT 133 exceeds its strong control maximum 103.
BCHUSDT 504 is below strong-null median 509.5 and
below maximum 519. The 20-second alternative phase
on BCHUSDT happens to exceed the envelope, but
**must not replace the failed 0-second primary endpoint**.

## Why bin occupancy matters

| 2026-11-17 original 0s | Nonempty 30s bins with 1 fill | 2 fills | 3–4 fills | 5–9 fills | 10+ fills |
|---|---:|---:|---:|---:|---:|
| LTCUSDT | 4 | 8 | 37 | 150 | 2,677 |
| BCHUSDT | **90** | **160** | **323** | **801** | **1,224** |

An exactly **one-print** bin is automatically **100%
one-sided** in every possible real or shuffled sample.
BCHUSDT has **90** such bins vs only **4** for LTCUSDT
on the same UTC day; it also has many more low-occupancy
bins overall. Conditioning at five prints removes
mechanically trivial one-print bins from the primary
endpoint and retains exact source bin membership
under all eight permutations.

However **BCHUSDT still fails** the predeclared
strong-null comparison even after this fixed
conditioning. Do not infer robot absence or market
efficiency from this, either: our null is not an
exchange-realistic causal model; it shuffles entire
same-timestamp side vectors **between equal-size
timestamp clusters** within each minute.

## Research safeguards

- Real source trade-print timing only. **No** historical
  synchronized L2 book, actual parent orders, account
  identities or labelled real robots.
- Eight shuffles do **not** estimate p-values,
  trading precision, source-actor counts or FDR.
  All three clock origins reuse one source tape.
- This method was refined *after* inspecting
  prior data on 2026-11-20; precommitted Nov17
  archives were not inspected before freezing this
  specific metric. Not a broad blind model test.
- No commercial/trading use of Binance Vision
  data under CC BY-NC-SA 4.0 without a separate
  appropriate license.
- Source ZIPs never uploaded into Git; 7-day
  aggregate-only Actions artifact
  `robot-detector-real-occupancy-preregistered-20261117`
  ID **14714090863**. Small original metrics pinned at
  [`fixtures/binance_spot_occupancy_20261117_observed.json`](../fixtures/binance_spot_occupancy_20261117_observed.json).
- The original network-fetch workflow was made
  **manual-only** after the successful execution.
