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


## Empirical run: 2026-11-18

**Succeeded as a data-access and parsing smoke, not a pattern-accuracy test.**

- T-Invest instrument: `SBER_TQBR`, session date: `2026-11-17`.
- GitHub Actions [run 44277857862](https://github.com/IskanderAbdullin/Analytics/actions/runs/44277857862).
- Downloaded body is **GZip compressed**, even though the endpoint/example filename is `.csv`. Importer now detects GZip by magic bytes, also supports ZIP.
- Decompressed data read: **121,920 public trade prints**; rejected rows: **0**.
- Raw-file SHA-256: `0af872b1c9c861e7af40a1c40e5bbdf565f9161dd997337c08da584c4dafc782`.
- Historical fixed-size cadence screen returned **195 candidate episodes**; this is emphatically **not** 195 proven bots. No p-value, calibrated confidence, owner IDs or completeness proof.
- One 60-minute dense segment (quantity 3, SELL, instrument UID e6123145-9665-43e0-8413-cd61b8aa9b13) was skipped because it contained **6,221 trades**, exceeding the configured 5,000-per-group limit.
- Approximate CLI detect step duration in hosted CI was 9 seconds including launch/JSON generation, not a controlled performance benchmark. Full peak memory and CPU were not measured.
- No raw exchange tape was committed, printed, or published as an artifact.

### Why first attempts failed and how the workflow handles TLS

- Initial standard GitHub Linux trust store rejected the T-Invest TLS chain, reported `SSL certificate OpenSSL verify result: self-signed certificate in certificate chain (19)`.
- The bank uses `Russian Trusted Root CA` / `Russian Trusted Sub CA`. Official bank documentation explains the additional root is not present in common default trust stores: https://developer.tbank.ru/funding/intro/certificates/migration-russian-trusted-ca .
- The isolated smoke job downloads a root CA over **normally validated HTTPS** from `https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt`, checks its subject and pins SHA-256 fingerprint `D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31`; it then sets `SSL_CERT_FILE` **only inside that ephemeral job**, never disables verification or modifies the user's machine trust store.
- On future legitimate root rotation, the pinned digest must be reviewed and updated; the job fails closed with `BLOCKED_UNVERIFIED_CA`.
- A root CA grants significant trust; this procedure must not be generalized to other hosts/flows without explicit security review.

### Interpretation

A successful one-day import proves the parser/endpoint can exchange **this file on this date**, nothing more. External market-data feed completeness, side semantics, other instruments/boards, real-time gRPC streaming and the false-discovery rate of 195 candidates still require separate measurements.

Next: Stage-2 negative controls / matched nulls on real session data and date-separated walk-forward evaluation, followed by stream adapter. See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md).
