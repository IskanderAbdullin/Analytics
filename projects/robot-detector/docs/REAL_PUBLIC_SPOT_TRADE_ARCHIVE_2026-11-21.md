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
