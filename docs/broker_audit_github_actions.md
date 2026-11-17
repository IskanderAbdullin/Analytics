# Running the broker coverage audit in GitHub Actions

The project provides an opt-in manual workflow named **Broker IPO market-data coverage audit**. It is read-only and does not place orders.

## One-time setup

1. In the Analytics GitHub repository, open Settings -> Secrets and variables -> Actions.
2. Create the repository secrets FINAM_API_SECRET and/or TINVEST_TOKEN. Add only the brokers you actually intend to use.
3. Optionally set FINAM_SOURCE_APP_ID as a repository secret if your Finam account requires it.
4. Never commit tokens into code, YAML, documentation, the coverage CSV, or issue comments.

The workflow will refuse to proceed if a selected broker's required secret is missing.

## Run

1. Go to Actions -> Broker IPO market-data coverage audit -> Run workflow.
2. Select the providers (both / finam / tinvest).
3. Keep include_minute_archives=false for the initial coverage scan. Annual ZIP files can be large, and they are optional.
4. Select the date window (30, 90, or 180 days) and start the workflow.
5. On completion, download the broker-ipo-coverage artifact from the Actions run.

The artifact contains a CSV instrument/candle-coverage report plus a JSON summary. Only coverage metadata is uploaded; market-data ZIPs and tokens are neither uploaded nor committed. The artifact retention period is seven days.

## How to interpret the report

- Check whether the ticker is in the full catalogue, including archived instruments.
- Use venue_verification: primary_venue / alternative_venue / unverified_venue.
- For opening-day analysis, require daily_listing_day_present=true or minute_archive_status=listing_day_available, and verify the source is the issuer's primary listing venue.
- Distinguish no_candles_returned, outside_documented_lookback, archive_not_found, and request_error.
- Do not treat a broker ticker alone as proof of issuer identity. Check issuer name, ISIN, original trading venue, share class, and corporate actions.

For reproducibility, record the Actions run URL and the archived report checksum. A successful GitHub Actions job verifies that the audit ran; it does not guarantee that a given broker covers any U.S. IPO event.

## Security notes

The workflow only performs authenticated read-only market-data calls. It has contents:read permission and has no trade API operations. GitHub Actions secrets are injected into the job environment, not written to files; the Python transport does not log authorization headers. A misconfigured or expired token may cause a failed job, which must not be misinterpreted as "zero historical coverage."
