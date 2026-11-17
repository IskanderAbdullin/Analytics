# Source catalogue and data acquisition strategy

Last reviewed: 2026-11-17. This is a research shortlist, not blanket approval for automated ingestion. Access, rate limits, licences, redistribution, retention, and commercial-use terms must be checked before enabling each connector.

## Key finding: there is no single free, complete, global IPO dataset

A robust universe requires a layered approach:

1. Build the U.S. issuer/deal universe from SEC filings and validate it against exchange admissions.
2. Add exchange-native cohorts where public records are comparatively structured. India is a promising first pilot.
3. Add Europe and Asia market-by-market from regulator/exchange prospectus and admission registers.
4. Use commercial global deal data as a benchmark if a licence becomes available.
5. Use aggregate statistics to reconcile coverage, not as a substitute for issuer-level outcomes.

The OECD methodology for its Asia capital-markets report describes using LSEG, FactSet, and Bloomberg transaction/firm-level data, with checks against regulators, exchanges, issuer sites, and financial statements. This is a useful benchmark for the quality and breadth of a professional global dataset.

## Tier 1 — primary and official sources

| Source | Coverage and useful fields | Best use | Limitations |
|---|---|---|---|
| SEC EDGAR submissions + XBRL | U.S. filings, filing dates, issuer identifiers, reported financial facts | Filing-derived IPO universe, S-1/F-1/424B4, financials | Requires issuer/filing classification; not a ready-made IPO returns database |
| SEC IPO statistics | U.S. aggregate counts and proceeds, quarterly and annual | Coverage checks and market-regime features | Aggregate only; SEC says statistics use third-party commercial datasets |
| NSE India IPO tracker | Indian IPOs; issue price, listing date, listing-day close and performance fields | First structured historical outcome cohort | Current-year tracker and archive are separate; verify CSV/API access and terms |
| NSE past-issues archive + SEBI directory | Historical Indian issue terms, dates, price ranges, issue sizes, lead managers | Extend India history and discover official BSE/NSE sources | HTML tables and field coverage vary by year |
| HKEX | Stock-admission statistics and prospectus/allotment announcements | Hong Kong event discovery and aggregate checks | Admission statistics are not a complete IPO-level return table |
| Euronext | Recent IPO listings across Euronext venues | European event discovery | Recent list is not a full historical deal-and-price database |
| London Stock Exchange | Primary-market new issues and issuer-list archives | UK IPO discovery and historic issuer coverage | LSE says delisting coverage is incomplete |
| ESMA prospectus register | EEA prospectuses, issuer/LEI, ISIN, approval/passporting metadata, CSV export | Prospectus discovery and document links | Includes many security offerings that are not IPOs |

### SEC implementation notes

- SEC says public data.sec.gov submissions and XBRL APIs do not require authentication or an API key.
- APIs are updated as filings are disseminated; bulk archives are rebuilt nightly and are more efficient for large historical downloads.
- SEC's Webmaster FAQ states a maximum automated access rate of 10 requests per second. The collector should use a lower configurable ceiling, a descriptive User-Agent, caching, retry/backoff, and request logging.
- SEC's Webmaster FAQ defines acceptance time as Eastern time, but explicitly says there is no timestamp indicating when filing content first becomes available on sec.gov. Do not use acceptance time as an exact public-availability timestamp. For strict intraday backtests, use an independently verified dissemination time or a conservative next-session availability boundary.
- Filing documents and XBRL facts need separate parsing. For IPO financials, preserve the filing accession number and filing date as the data vintage.

### India as a promising pilot cohort

NSE's IPO tracker exposes issue price, listing date, listing-day close, listing-day gain/loss, and latest price fields. NSE's historical past-issues archive contains older issue details including price, listing date, price range, issue size, and lead managers. SEBI curates links to NSE and BSE primary-market data.

This may be a better first historical outcome dataset than trying to reconstruct every U.S. IPO from scratch. Indian SME and mainboard issues must be tagged separately; exchange trading calendars, price bands, lot sizes, and liquidity differ materially from U.S. IPOs.

## Tier 2 — macro, news, and community context

### FRED / ALFRED

Use for Treasury yields, policy rates, credit spreads, recession indicators, and other macro series. FRED requires an API key. ALFRED vintage dates and initial-release output are important: today's revised macro history must not leak into an old forecast.

### GDELT

GDELT describes its Event Database and Global Knowledge Graph as free and open and makes data available through downloads and Google BigQuery. It can provide global news attention, event volume, source geography, and topic context. It is not a direct measure of investor demand, and syndicated stories must be deduplicated.

### Hacker News

The official public Firebase API exposes stories and comment trees in near real time and currently documents no rate limit. It is useful for technology-community reaction to an issuer, its product, and its competitors. It is not representative of the general retail-investor population and should be treated as one narrow community panel.

### Reddit — permission gate

Reddit's current Data API terms and help documentation require OAuth, impose rate limits, require deletion of removed content, and state that Reddit content may not be used as input for model training without explicit consent. Commercial use requires a separate agreement. Reddit is therefore excluded from model training by default. Do not scrape it or use third-party archives to bypass these rules.

## Tier 3 — candidate datasets and paid benchmarks

### Fliar BI global IPO dataset

A dataset advertised as 13,316 IPOs from 2019 to June 2026 across India, the U.S., the U.K., and 100+ countries is available under CC BY-NC 4.0. Its data card describes extraction from business-news reports using third-party Radar/Fliar systems. It may be useful as a discovery list, but it is not ground truth. The non-commercial restriction makes it unsuitable for a trading/commercial pipeline unless legal review confirms the intended use is permitted. Do not ingest it into the main dataset by default.

### LSEG / FactSet / Bloomberg

Commercial databases are likely the most practical route to a consistent cross-market deal-level universe, including withdrawn deals, issue terms, and vendor-normalised identifiers. OECD methodology cites these vendors and describes reconciliation against primary sources. Evaluate cost, historical coverage, survivorship handling, corporate actions, and redistribution rights before purchase.

## Recommended acquisition order

1. **U.S. filings:** build the SEC issuer/filing universe; parse S-1/F-1 and final prospectuses; record withdrawals and postponed deals.
2. **India outcome cohort:** ingest NSE tracker and historical issue archive; match official daily price data and preserve mainboard vs SME labels.
3. **U.S. price outcomes:** select a licensed market-data source for first trade, first-day OHLCV, and adjusted 5/20/60/180-session prices. Do not assume free quote APIs provide complete delisted/security history.
4. **Market regime:** add FRED/ALFRED and official index/volatility data with point-in-time vintages.
5. **News attention:** add GDELT first; add community panels only after terms review.
6. **Europe and Hong Kong:** add ESMA prospectus register, Euronext/LSE and HKEX source adapters.
7. **Global reconciliation:** compare counts and deal definitions with SEC quarterly statistics and, if feasible, a licensed LSEG/FactSet/Bloomberg sample.

## Dataset acceptance checklist

A source may enter the production pipeline only after:
- its licence, API terms, rate limits, and retention rules are recorded;
- the data owner and retrieval method are identified;
- identifiers can be matched to a stable IPO event key;
- publication/availability timestamps can be reconstructed;
- revisions and missing/deleted records can be handled;
- a sample has been checked against primary documents;
- fields, units, currency, exchange timezone, and corporate-action policy are documented.

No row should be promoted to the modelling table merely because it appears in a third-party spreadsheet or social-media post.
