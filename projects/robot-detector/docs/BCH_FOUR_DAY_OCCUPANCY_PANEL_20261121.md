# 2026-11-21 — Four consecutive source-verified BCHUSDT UTC days

The [first cross-asset transfer](REAL_SPOT_PRECOMMITTED_TRANSFER_20261120.md)
failed on BCHUSDT (2026-11-20), and the later
[>=5-print conditioned UTC-day test](REAL_SPOT_OCCUPANCY_TRANSFER_20261117.md)
also failed on BCHUSDT 2026-11-17. This is why the
research did **not** promote an LTCUSDT public-print
timing signal to a universal algorithmic-trading detector.

## Previously uninspected BCH sessions, preregistered before download

Exactly **BCHUSDT 2026-11-18 and 2026-11-19 UTC** were pinned
*before downloading either file* in research precommit commit
`a71958e59f8195852a2f664a82c3969c934d26f5`.
The supporting **already-inspected** BCH 2026-11-20
five-print recomputation was also frozen before new-source
download in amendment
`e2a71147990659a19e43c4949be33795045398e1`.
BCH 2026-11-17 occupancy numbers were already inspected
and came from the pinned old-source fixture.

[Original successful provider-checksummed GitHub Actions
#44921851326](https://github.com/IskanderAbdullin/Analytics/actions/runs/44921851326)
first ran 38 no-network unit/negative cases, then downloaded
the two novel BCH dates, separately recomputed the seen
Nov20 archive, validated all three source ZIP SHA256 values
against official provider checksums, and reconciled a
strict 4-day panel with the original Nov17 fixture.

### Four observed real exchange spot execution archives

| BCHUSDT UTC day | Source prints | Observed first trade ID | Observed last trade ID | Official ZIP SHA256 |
|---|---:|---:|---:|---|
| 2026-11-17 (seen) | 42,678 | 296851413 | 296894090 | `dca1e3983106d787d10a80e6a8a6b7fd9dc4866afef6ea25379e065abdae1b53` |
| **2026-11-18 (new)** | **28,466** | 296894091 | 296922556 | `52db334a1d9bd96e2f6ea1673a8e8f0f39aa2f9872d0482121bd174f9090fed5` |
| **2026-11-19 (new)** | **50,213** | 296922557 | 296972769 | `bea94c8e9280824ced48ceb5aeccfa322662e8c96203eb6b9cf74f2e58b264c3` |
| 2026-11-20 (seen/recomputed) | 73,279 | 296972770 | 297046048 | `553421be8eaf1e339eb0e111a25604ce7d2965e85ad15cea1650ffa0d012e46c` |
| **Four days total** | **194,636** | 296851413 | 297046048 | Four distinct checksums above |

No within-file observed trade-ID gaps. All three
original adjacent daily provider files have observed
last-ID+1 == next day's observed first-ID, so the
four-day observed public trade-ID range is contiguous.
This is useful **provider dataset continuity**
evidence, **not** a cryptographic proof that every
real matching-engine event was publicly distributed.

## Frozen primary: origin 0s, 30s complete UTC bins, >=5 prints/bin

| Real BCH day | Eligible >=5 bins | Actual one-sided >=5 | Eight strong controls median / maximum | Exceeded all eight? |
|---|---:|---:|---|---|
| Nov17 (seen) | 2,025 | 504 | 509.5 / 519 | **NO** |
| **Nov18 (new)** | 1,885 | 610 | 620.5 / 626 | **NO** |
| **Nov19 (new)** | 2,183 | 541 | 530.5 / 539 | **YES**, difference vs max only 2 bins |
| Nov20 (seen) | 2,562 | 334 | 323.5 / 343 | **NO** |

Thus **only one of the two genuinely uninspected
BCH source days** met the already-fixed primary envelope
condition. Across four days, three primary measurements
are not above the eight-shuffle maximum, but
only Nov18–19 form the newly preregistered source pair.
This is **descriptive**, not a binomial statistical
test, p-value, or physical bot-detection FDR.

### Secondary phases: explicitly not substitutes for 0s

| BCH UTC day | 10s observed / strong median / max | 20s observed / strong median / max |
|---|---|---|
| Nov17 | 495 / 503.5 / 537 | 503 / 488.5 / 500 |
| Nov18 | 638 / 637 / 644 | 637 / 619.5 / 635 |
| Nov19 | 557 / 552.5 / 562 | 553 / 545.5 / 558 |
| Nov20 | 308 / 322 / 332 | 322 / 319 / 340 |

A 20s phase would change apparent classification
for BCH Nov17/18, but **it was secondary** and cannot
retroactively rescue negative 0s results. Furthermore
each phase reuses one source tape.

## Aggregate market evidence across two spot instruments

Four contiguous LTCUSDT days, 2026-11-17..20,
had previously yielded **581,371** public prints.
BCHUSDT for the same four days has now yielded
**194,636**. Overall the project has verified
**776,007 real public execution prints** spread over
**8 different instrument-day source archives**, with
provider-published ZIP SHA256 for each original file.

Both LTC and BCH have continuous observed trade IDs
across their four dates, but neither has an independently
certified complete exchange order book L2 or any
real participant identity ground truth.

The study is limited by close dates, shared market
conditions, non-independence of phase shifts, eight
simulated side shuffles and the failure of a realistic
causal null. We cannot claim robot identities,
significance or actual-market FDR/accuracy.

**License**: all Binance Vision source use is
noncommercial research under the provider's
Dataset Terms/CC BY-NC-SA 4.0, with no commercial
proprietary trading permission. No raw trade archive,
identity or large replay is uploaded into Git.
Only small aggregate source artifacts have 7-day
retention. Network workflow changed to **manual
dispatch only** after the original successful run.

The exact original original-case scalars are pinned at
[`fixtures/binance_bch_four_day_public_panel_20261121.json`](../fixtures/binance_bch_four_day_public_panel_20261121.json);
original GitHub artifact ID `14714440828`.
