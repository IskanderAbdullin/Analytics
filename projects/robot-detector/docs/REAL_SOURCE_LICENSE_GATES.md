# Market Robot Detector source licensing and capability — 2026-11-21

A public URL is not a commercial trading or data redistribution license.
Reverify updated provider terms before any *new* acquisition.

| Provider | Availability | Allowed project use |
|---|---|---|
| Binance Vision | Official daily spot *raw executed trades* ZIP and SHA256 provider checksums | Bounded **non-commercial** public-print research only under Dataset Terms / CC BY-NC-SA 4.0; no live/commercial trading or unauthorized dissemination |
| MOEX ISS | Anonymous delayed market summaries and trading history results; not automatically a raw trades archive or full historical L2 | No automated non-display trading-data processing without a suitable MOEX contract |
| Coinbase | Exchange L2 real-time APIs are publicly documented | **BLOCKED_PENDING_PERMISSION:** Market Data Terms prohibit using these data to develop/train/validate AI/ML models and algorithms without prior express written permission |
| ABIDES-NG | Genuine simulation matching-engine synthetic L2 + execution prints | Research development only; no physical market participant identification |

Authoritative provider pages:

- Binance terms (updated 2026-08-26): https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md
- MOEX information-use requirements: https://www.moex.com/s3503
- Coinbase Market Data Terms (including clause 3.5): https://www.coinbase.com/legal/market_data

## Actual source acquisition, separate research-only sample

Public GitHub Actions run https://github.com/IskanderAbdullin/Analytics/actions/runs/44916791033
verified 116,446 original LTCUSDT spot prints from 2026-11-18 UTC,
provider ZIP SHA-256 2fbf1fe2f85c813b3d5e4922d674799adced6f306effe0e5cf9add62a57e6522.

Separate precommitted next-day run
https://github.com/IskanderAbdullin/Analytics/actions/runs/44917086043
verified 161,957 source prints for 2026-11-19 UTC,
provider ZIP SHA-256 9208231cbd6b55e4de42d04d9c07aa636be235be6d1c08ddb3c6953dbc6f3c1a.

Together 278,403 actual public exchange prints, including consecutive
visible trade IDs across midnight. Exchange completeness and full book
depth history are **NOT independently attested**.

All downloaded sources were research-only and are **NOT** uploaded
as raw GitHub artifacts, reused for proprietary trading or
exposed as physical robot or owner IDs. The public description
of 30-second print-origin robustness is **not** a real market
false-alarm benchmark.

Full data interpretation:
[REAL_PUBLIC_SPOT_TRADE_ARCHIVE_2026-11-21.md](REAL_PUBLIC_SPOT_TRADE_ARCHIVE_2026-11-21.md).

## Release stop conditions

The following must remain **BLOCKED** without new independent
evidence/permissions: non-display MOEX commercial use, Coinbase AI
processing, historical synchronized L2, physical owner identification,
actual market FDR, and live trading integration.

Provider checksum verifies identity of published ZIP, not guarantee
that the exchange emitted every historical execution.
