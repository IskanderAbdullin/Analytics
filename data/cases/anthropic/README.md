# Anthropic IPO — first case study

## Identity

- Issuer: Anthropic, PBC
- SEC CIK: 0002130357
- SEC registration file: 333-299633
- Proposed ticker: ANT
- Proposed venue: Nasdaq Global Select Market (the S-1 states that the issuer applied to list there)
- Snapshot date: 2026-11-17

## Verified filing timeline

See filings.csv. It records the initial public S-1, three amendments, and the Form 8-A12B filing, with SEC accession numbers and direct SEC archive URLs.

The SEC filing index identifies the initial S-1 on 2026-10-26, amendments on 2026-11-02, 2026-11-10, and 2026-11-17, and a Form 8-A12B on 2026-11-17. The latest S-1/A includes interim financial statements for the nine months ended 2026-09-30.

## Point-in-time treatment

- The $70–$78 estimated offer-price range is recorded in the November 10 S-1/A-2 only. Do not assume it remained unchanged in later amendments without checking the latest cover page.
- Acceptance times in filings.csv are preserved exactly as displayed by SEC filing-index pages. SEC defines acceptance time as Eastern time, but also states that it does not provide a timestamp for when filing content first becomes available on sec.gov. The acceptance time is therefore not an exact feature-availability timestamp.
- Facts first disclosed in the November 17 S-1/A-3 must not be included in forecasts whose information cut-off predates that filing's public availability.
- If no independent dissemination timestamp can be verified, use a conservative next-session availability boundary and mark availability_precision as conservative_next_session.
- The Form 8-A12B is a securities-registration filing, not an observed first-trade or listing outcome.

## Current dataset status

This folder is a verified filing manifest, not a complete IPO dataset. No offer price, allocation, first-trade price, daily OHLCV, realised return, or model label has been entered. No model should be trained on this case until:
1. all material fields are extracted from the correct filing vintage;
2. the final prospectus and pricing announcement are identified;
3. the actual listing and first-trade timestamps are verified;
4. market prices and corporate-action treatment are sourced;
5. every observation receives a source, availability timestamp, availability precision, evidence type, and confidence grade.

Use this case to test the point-in-time pipeline and filing parser, not to tune the model to a single issuer.
