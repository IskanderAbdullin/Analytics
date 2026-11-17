# SEC EDGAR connector

## Setup

Set SEC_USER_AGENT to a descriptive application name and a real contact email. For example:

    SEC_USER_AGENT=IPOAnalytics analyst@example.com

Do not commit a real email if it is private; provide it in the local environment instead. The repository's .env.example contains only a placeholder.

## Supported operations

- Resolve ticker/company-name candidates using SEC's company ticker mapping.
- Fetch a company's submissions history.
- Fetch XBRL company facts.
- Extract S-1, S-1/A, F-1, F-1/A, 424B4, 424B3, and 424B5 filing candidates.
- Follow SEC historical submissions shards for older filings.
- Build the canonical primary-document URL for each accession.

Example from Python:

    from ipo_forecast.data.sources.sec_edgar import SecEdgarClient

    client = SecEdgarClient()
    matches = client.resolve_company("Example issuer")
    submissions = client.list_ipo_filings(matches[0]["cik_str"])

The collector caches raw JSON under data/raw/sec_edgar/cache. That folder is git-ignored. Cached responses should be retained as source snapshots and accompanied by retrieval metadata in the production ingestion pipeline.

## Fair-access rules

SEC's developer information says the submissions and XBRL APIs on data.sec.gov do not require an API key. SEC's Webmaster FAQ states a maximum automated access rate of 10 requests per second. This client defaults to five requests per second, uses an identified User-Agent, caches responses, and retries transient 429/5xx/network failures with backoff.

Use one shared client per process. Do not run multiple collectors in parallel against SEC without a shared rate limiter. Do not remove throttling to accelerate bulk downloads.

## Important limitations

- The S-1/F-1 and 424B4 forms identify filing candidates, not necessarily completed IPOs. Some are withdrawn, postponed, amended, or are not conventional operating-company IPOs.
- A final prospectus is not a substitute for the first filing. Preserve each filing accession and availability timestamp to reconstruct what was known at each forecast origin.
- The submissions endpoint has a recent-filings block and references to historical JSON shards. The connector can follow those shards, but large-scale market-wide history should use SEC bulk archives or daily indexes rather than one request per company.
- XBRL company facts are not a complete replacement for parsing prospectus financial statements. Keep units, fiscal periods, tags, filing dates, and source accessions.
