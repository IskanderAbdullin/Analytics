# SEC EDGAR connector

## Setup

Set SEC_USER_AGENT to a descriptive application name and a real contact email. For example:

    SEC_USER_AGENT=IPOAnalytics analyst@example.com

Do not commit a real email if it is private; provide it in the local environment instead. The repository's .env.example contains only a placeholder.

## Supported operations

- Resolve ticker/company-name candidates using SEC's public ticker mapping.
- Fetch a company's submissions history and XBRL company facts.
- Extract S-1, S-1/A, F-1, F-1/A, 424B4, 424B3, and 424B5 filing candidates.
- Follow SEC historical submissions shards for older filings.
- Scan quarterly master.idx files to discover filing candidates across many issuers.
- Build canonical URLs for filing documents.

Examples:

    ipo-forecast sec-search --query "Example issuer"
    ipo-forecast sec-filings --cik 1234567 --start-date 2018-01-01
    ipo-forecast sec-index --start-year 2000 --end-year 2026

The broad index scan downloads four quarterly indexes per year and filters them locally. It is much more efficient for discovering an issuer universe than making one submissions request per company. The output is a candidate list, not a confirmed IPO dataset.

## Cache and fair access

The collector caches raw responses under data/raw/sec_edgar/cache. That folder is git-ignored. SEC's developer information says the public submissions and XBRL APIs on data.sec.gov do not require an API key. SEC's Webmaster FAQ states a maximum automated access rate of 10 requests per second. This client defaults to five requests per second, uses an identified User-Agent, caches responses, and retries transient 429/5xx/network failures with backoff.

Use one shared client per process. Do not run multiple collectors in parallel against SEC without a shared rate limiter. Do not remove throttling to accelerate bulk downloads.

## Important limitations

- S-1/F-1 and 424B4 forms identify filing candidates, not necessarily completed IPOs. Some are withdrawn, postponed, amended, or are not conventional operating-company IPOs.
- A final prospectus is not a substitute for the first filing. Preserve each filing accession and availability timestamp to reconstruct what was known at each forecast origin.
- SEC master indexes identify filing documents, but the project still needs to group filings into issuer/deal events, classify IPO vs follow-on/SPAC/other offerings, and identify withdrawals and completed listings.
- A filing date is not necessarily the exact public-availability timestamp. Use acceptance/dissemination timestamps where available.
- XBRL company facts are not a complete replacement for parsing prospectus financial statements. Keep units, fiscal periods, tags, filing dates, and source accessions.
