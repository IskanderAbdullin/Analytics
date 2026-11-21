# First new verified real-market execution archive — 2026-11-21

**Scope:** purely non-commercial research; new **real exchange public prints**,
not another ABIDES synthetic cohort, not MOEX/SPB events and not L2 orderbook.
No proprietary trading, investment execution or automatic signal publication.

## Frozen dataset and original successful run

The date, instrument and endpoints were committed in source **before**
download. [GitHub Actions original successful network run
#44916791033](https://github.com/IskanderAbdullin/Analytics/actions/runs/44916791033)
downloaded the official **LTCUSDT Binance Spot raw trade tape for
2026-11-18 UTC** and provider-published SHA-256 checksum:

- ZIP: https://data.binance.vision/data/spot/daily/trades/LTCUSDT/LTCUSDT-trades-2026-11-18.zip
- CHECKSUM: https://data.binance.vision/data/spot/daily/trades/LTCUSDT/LTCUSDT-trades-2026-11-18.zip.CHECKSUM
- Exact provider ZIP SHA-256: `2fbf1fe2f85c813b3d5e4922d674799adced6f306effe0e5cf9add62a57e6522`.
- ZIP bytes **1,342,515**, **116,446** accepted spot execution rows.
- First/last public raw trade IDs: **608186258 / 608302703**; **zero**
  missing IDs between *the observed endpoints*. This does **not** attest
  earlier/later events or independently verify provider completeness.
- Microsecond UTC exchange timestamps monotonically ordered:
  1794960000163697 through 1795046394287834.
- Buyer-initiated trades **59,593**; seller-initiated **56,853**;
  base-asset quantities **163,375.282** / **158,149.62 LTC**.
- Public trades observed in **all 1,440 UTC-minute bins**; largest
  observed minute 918 trades; median nonempty minute **62** trades.

The original 7-day GitHub artifact `robot-detector-new-public-spot-trades-20261118`
(ID **14711684055**) contains ONLY compact derived/provenance JSON.
A smaller pinned summary is at
`fixtures/binance_spot_ltcusdt_real_observed_20261118.json`.
The repository contains no raw trade archive or source row-level feed.

## Exact source contract and licensing

Binance Vision [official schema documentation](https://github.com/binance/binance-public-data)
confirms `trades` has seven fields: trade ID, price, quantity,
quote quantity, time, buyer-is-maker and best match. Since **2025-01-01**,
spot timestamps are **microseconds**, not milliseconds.
`isBuyerMaker=True` implies public aggressive SELL, otherwise BUY;
neither side identifies a physical participant or parent execution
program. This is **trades**, not compressed `aggTrades`.

The [Binance Vision Dataset Terms (last updated 2026-08-26)](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md)
govern data and derivatives under **CC BY-NC-SA 4.0** with
additional limitations on **commercial use, paid redistribution,
trading execution and paid signals**. The project uses these data
only for separated non-commercial source-coverage/scientific research.
The presence of open-source detector code does not license this
dataset for commercial proprietary trading. Confirm license scope
before reusing dataset-derived results in any commercial workflow.

## What the downloader proves and does not prove

`tools/binance_public_trade_archive.py` uses standard Python only:
bounded official ZIP/CHECKSUM HTTPS, byte-exact provider SHA-256,
single CSV member, UTC-day bounds, 16-digit timestamps,
exact decimal parsing, strictly increasing IDs and nondecreasing
exchange timestamps. Malformed source, duplicate IDs, tampered checksum,
unbounded uncompressed ZIP, wrong file or wrong side flags fail closed.
No account, market order or real-time broker access.

**Proven:** the observed file matches the file addressed by the
official published checksum and every decoded row passes source
invariants. **Not proven:** that Binance delivered every real execution,
that a full public L2 book exists, that signatures authenticate the
provider independently, that the date is a statistically independent
holdout after an analyst inspects the results, or that any algorithm
identifies an actual robot. No predictive threshold fitted, no
market-specific false alarm rate calculated.

## Replication and reproducibility

```bash
cd projects/robot-detector
python -m unittest discover -s tests_background -p 'test_binance_public_trade_archive.py' -v
python tools/binance_public_trade_archive.py \
    --symbol LTCUSDT --date 2026-11-18 \
    --output data/results/ltcusdt-20261118-source-audit.json
```

These commands are read-only and use only the provider's public archive.
Output refuses overwrite. The network workflow was made
**manual-only after the original successful run**, avoiding repeat
data downloads and GitHub Actions cost.

## Next scientific gate

Use an *uninspected, precommitted* distinct real session/instrument
for out-of-sample timing robustness. The original 2026-11-18
LTCUSDT data are now **seen** and must not be promoted to a fresh
blinded detector holdout. Without a complete verifiable L2 stream,
book-imbalance/quote-oscillation tests remain **BLOCKED_BY_L2_DATA**.

## Predeclared independent UTC-day public print timing sample (2026-11-19)

After the first 2026-11-18 observation became visible, a different UTC
source day **2026-11-19** was frozen and acquired through
[successful GitHub Actions #44917086043](https://github.com/IskanderAbdullin/Analytics/actions/runs/44917086043).
This is a distinct, previously uninspected *chronological real market
day* of public prints, **not** a blind test of a previously frozen
robot-detector classifier.

- **161,957** exchange public execution rows, official ZIP SHA-256:
  `9208231cbd6b55e4de42d04d9c07aa636be235be6d1c08ddb3c6953dbc6f3c1a`.
- First/last spot trade IDs **608302704 / 608464660**,
  zero missing IDs within the observed UTC day; official provider
  ZIP checksum matched.
- **71,851** aggressive BUY / **90,106** aggressive SELL prints;
  all 1,440 UTC minutes contain observed executions.
- The first ID of 2026-11-19 (**608302704**) directly follows
  the last ID of 2026-11-18 (**608302703**): strong observed
  adjacent-day continuity of this one provider archive, but
  **not** independent proof that every real exchange event exists.
- Three **predeclared 30-second** analytical phases use the *same*
  161,957-source-trade tape. They are correlated views, not 3 days.
  Only bins completely contained within the UTC date count;
  10s/20s shifted phase partially intersecting boundary bins are excluded.

| Frozen origin | Full UTC-day bins | Nonempty bins | Excluded edge prints | BUY-dominant / SELL-dominant / tied bins | One-sided bins |
|---|---:|---:|---:|---:|---:|
| 0s | 2880 | 2879 | 0 | 1363 / 1447 / 69 | 135 |
| 10s | 2879 | 2878 | 20 | 1312 / 1484 / 82 | 113 |
| 20s | 2879 | 2878 | 37 | 1337 / 1478 / 63 | 135 |

These **real exchange executed-trade** summaries show that the
researcher's arbitrary clock origin changes the assignment of
public buy/sell-dominant bins; no L2 book or individual identity
is observable. Comparing counts of dominant/one-sided bins with
different eligible interval memberships is descriptive, not a
calibrated FDR estimate.

A second compact no-raw-events fixture
`fixtures/binance_spot_ltcusdt_real_observed_20261119.json`
pins all source checksum and timing phase counts. Both provider
network-fetch workflows became **manual-only after successful
one-time executions**.

## Combined two-day provenance audit and licensing guard

The read-only no-network `tools/real_public_trade_pair_review.py`
consumes the two compact source-controlled summary fixtures, rechecks
their original provider ZIP SHA-256 identities, date/source paths,
time boundaries, exact numeric fields, buy/sell count conservation
and declared legal/unknown-truth constraints. It also independently
reconciles all three UTC-day phase-bin summaries from the second day.

| Real spot session | Public prints | Aggressive BUY | Aggressive SELL | BUY fraction |
|---|---:|---:|---:|---:|
| LTCUSDT 2026-11-18 UTC | 116,446 | 59,593 | 56,853 | 51.18% |
| LTCUSDT 2026-11-19 UTC | 161,957 | 71,851 | 90,106 | 44.36% |
| **Combined** | **278,403** | **131,444** | **146,959** | **47.21%** |

The observed adjacent-day ID range has no internal gaps:
608186258 through 608464660, inclusive, matching **278,403**
prints. All first/last timestamps are contained in the requested
UTC dates and ordered. That strengthens source continuity
evidence but does not certify provider coverage or complete
matching-engine origin history.

```bash
cd projects/robot-detector
python -m unittest discover -s tests_background \
  -p 'test_real_public_trade_pair_review.py' -v
python tools/real_public_trade_pair_review.py \
  --output data/results/public-two-day-provenance.json
```

This latter offline review verifies stored **metadata** and
fails closed on simulated tampering; it **does not re-download
or re-verify raw ZIP bytes**. Original independent provider
checksum verification is evidenced by the successful
two original Actions runs linked above.

### MOEX historical L2 and license gate

The free, public [MOEX ISS interface](https://www.moex.com/a8531)
provides anonymous delayed market statistics and historical trade
*results*, but those summary candles/NUMTRADES aggregates must not
be represented as event-level historical trade prints or
full-depth historical L2. More importantly, the
[MOEX information-use terms](https://www.moex.com/s3503)
identify a separate **non-display contract** for automated
market-information processing for algorithmic trading or
risk-management. **No automated MOEX dataset acquisition or
commercial execution has been attempted in this project**.
Verify legal entitlement before acquiring/training on MOEX
non-display feeds; an HTTP endpoint being publicly accessible
does not by itself grant unrestricted redistribution or
commercial trading rights.

**Next scientific limitation:** a real anonymous public execution
tape can reveal activity and time-bin artifacts but cannot reveal
parent-order or market participant counts. Validating L2-based
robot-detection hypotheses still requires lawful full-depth
synchronized quote snapshots and broker/source coverage evidence.
No stage-2 real-market accuracy/release gate has been opened.

## Already inspected real-market data: minute-preserving weak side controls

A separate source-committed stage tests an explicitly **weak null**
against the two already **inspected** LTCUSDT UTC days. The algorithm
shuffles each public execution's BUY/SELL flag *within its exact UTC
minute* using eight fixed deterministic seed values. It preserves:
all executed event microsecond timestamps (including ordering/ties),
per-minute exact BUY/SELL counts, market-wide print count, and
all 0/10/20-second complete UTC-day bin boundaries. It does **not**
preserve same-timestamp partial-fill correlation, real order
queue effects, cross-minute side persistence, or parent-order truth.

[Original successful verified-archive CI run #44918585645](https://github.com/IskanderAbdullin/Analytics/actions/runs/44918585645)
re-read both **original** official ZIPs, matched both original
source SHA-256 values, ran all deterministic negative tests, and
saved ONLY compact aggregate/source JSON (artifact ID
`14713021082`). The small observed scalar fixture is
`fixtures/binance_spot_weak_direction_nulls_20261121.json`.

| UTC source day | Predeclared origin | Actual one-sided complete 30s bins | 8 within-minute shuffle controls: min / median / max |
|---|---:|---:|---|
| 2026-11-18 | 0 s | 173 | 65 / 74 / 81 |
| 2026-11-18 | 10 s | 161 | 46 / 56.5 / 68 |
| 2026-11-18 | 20 s | 177 | 49 / 59 / 67 |
| 2026-11-19 | 0 s | 135 | 51 / 58.5 / 67 |
| 2026-11-19 | 10 s | 113 | 45 / 51 / 57 |
| 2026-11-19 | 20 s | 135 | 40 / 47 / 55 |

There is substantially more single-sided 30s public-print
concentration in the observed market data than in this permissive
toy randomization. **Do not infer real bot execution from this.**
Execution bursts from the *same actual market order* may appear in
several same-timestamp prints; independent per-print randomization
breaks this real microstructure. Eight realizations provide no
calibrated sampling distribution, p-value, market FDR or physical
owner count. Both tapes were **already inspected development data**
before this null protocol, so the exercise is retrospective,
not blinded out-of-sample confirmation.

A scientifically necessary follow-up is a **stronger null that
preserves equal-timestamp execution clusters**, plus independent
true external market validation. Source data remains under
non-commercial CC BY-NC-SA terms and must not enter live trading.
The original expensive workflow is now **manual-only**.
