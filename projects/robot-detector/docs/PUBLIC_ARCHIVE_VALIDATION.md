# Pilot: public T-Invest historical trade archive (read-only)

This file describes a **single-instrument, single-day** empirical data-access smoke. It is separate from statistical correctness, live streaming and trading.

- Official endpoint: https://invest-public-api.tbank.ru/history-trades/{date}?instrumentId={ticker_class_code}
- Official documentation: https://developer.tbank.ru/invest/services/history-md/head-history-md
- Proposed example: 2026-11-17, SBER_TQBR (not asserted available until run).
- Workflow: [robot-detector-public-history.yml](../../../.github/workflows/robot-detector-public-history.yml).
- No token; no broker account reads or order commands. Only one or two GETs if CSV/ZIP format differs; below the advertised limit of 30 files/min/IP.
- The workflow **never uploads the raw trade tape as an artifact**. It logs only row counts, rejected rows, candidate episode count, unverified coverage flag and SHA-256 of the archive.
- If a 404, HTTP error, size cap, or missing/invalid format prevents processing, it prints `BLOCKED_BY_DATA` rather than pretending no trading robots were found.
- Even if real data parse succeeds, the reported candidate count is not statistically validated; the script asserts `physicalBotCountKnown=false` and patterns remain `candidate`.
- A one-day 1,000,000-row cap and 250 MB download bound are intentional safety limits; high-volume instruments may need chunk processing/streaming import later.

## Acceptance / evidence

1. GitHub Actions can obtain the public file without authorization and without secrets.
2. Parser reads actual schema and emits output, or documents a precise failure reason.
3. No data sharing, external trading API or market order calls.
4. If successful, log raw-file SHA and source coverage warning, then select multiple sessions for future quality study.
5. A successful smoke is **not** proof of data completeness, timestamp accuracy, price direction semantics, or bot detection precision.

Historical read-only test does not make Stage 3 (real-time MarketDataStream) complete.
