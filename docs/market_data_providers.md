# Finam and T-Invest market-data adapters

## Purpose

The adapters are designed to answer a narrow question before model training: can each broker supply the actual post-listing price history needed to label an IPO event, including its first trading day?

They do not assume that a ticker in a current instrument list proves historical data availability. The audit separately records:
- whether the instrument is present in the provider catalogue;
- whether it is archived or currently API-tradable, when the provider exposes that field;
- the first daily/minute candle dates, when exposed;
- whether daily candles cover the IPO listing window;
- whether minute candles or an annual minute archive (when explicitly enabled) contain the listing day.

## Credentials

Set credentials in the local shell. Do not commit them, place them in command-line arguments, or paste them into chat.

Windows PowerShell:

    $env:FINAM_API_SECRET = "your Finam Trade API secret"
    $env:TINVEST_TOKEN = "your T-Invest API token"

Finam's API secret is exchanged through POST /v1/sessions for a JWT. The JWT is then sent in the Authorization header. If your Finam account requires a source application ID, set FINAM_SOURCE_APP_ID.

T-Invest uses a Bearer token. TINVEST_TOKEN is preferred; TINKOFF_INVEST_TOKEN is also accepted.

## Run the pilot coverage audit

From the repository root:

    python -m pip install -e ".[dev]"
    ipo-forecast market-data-audit

The default audit excludes annual ZIP downloads. Add --minute-archives to opt into potentially large annual downloads. The default universe is data/templates/us_ipo_coverage_sample.csv. It contains a mixture of older and recent IPOs, a delisted/acquired control, and Anthropic as a pending case. The sample is for coverage testing only; its rows are not automatically accepted as training labels.

Output:
- data/interim/market_data_coverage.csv — one row per ticker/provider, with instrument and event-window coverage fields.
- data/interim/market_data_coverage.summary.json — counts of instruments found and event windows with daily/minute data.

Useful options:

    ipo-forecast market-data-audit --providers tinvest
    ipo-forecast market-data-audit --providers finam tinvest --daily-window-days 180
    ipo-forecast market-data-audit --minute-archives
    ipo-forecast market-data-audit --refresh

Raw API responses are cached under data/raw/market_data/cache and ignored by Git. Use --refresh to bypass the cache.

## Finam

Official REST API: https://api.finam.ru/docs/rest/

- Authentication: POST /v1/sessions with the API secret; subsequent requests use the returned JWT in Authorization.
- Instrument catalogue: GET /v1/assets/all, paginated by next_cursor. The endpoint includes active and archived instruments.
- Bars: GET /v1/instruments/{ticker@mic}/bars.
- Documented lookback: M1 7 days; M5/M15/M30/H1/H2/H4/H8 30 days; D 365 days; W/MN/QR five years.
- The adapter defaults to 0.31 seconds between requests (about 194 requests/minute), below the documented 200 requests/minute limit.

Finam's current Trade API bars endpoint is not a substitute for a long-term daily/minute archive. Older IPO event windows are deliberately marked outside the documented lookback rather than reported as a provider outage.

## T-Invest

Official documentation:
- GetCandles: https://developer.tbank.ru/invest/api/market-data-service-get-candles
- Historical candle windows: https://developer.tbank.ru/invest/intro/intro/load_history
- Annual minute archives: https://developer.tbank.ru/invest/services/quotes/get_history
- Shares and instrument status: https://developer.tbank.ru/invest/services/instruments/methods

The adapter:
- calls InstrumentsService/Shares with instrumentStatus=INSTRUMENT_STATUS_ALL, rather than the currently tradable base list;
- uses uid as the preferred instrument identifier;
- reads first1minCandleDate and first1dayCandleDate when present;
- uses MarketDataService/GetCandles for daily and one-day minute windows;
- downloads the annual /history-data ZIP archive and parses its headerless semicolon-separated CSV files.

Documented GetCandles request windows vary by interval: 1-minute requests are limited to one day, daily history to approximately six years, weekly to five years, and monthly to ten years. The actual start date can vary by instrument. Annual minute archives are not guaranteed for every instrument and may not cover its full exchange history.

## Interpretation and limitations

- A missing ticker from a broker catalogue does not prove that the broker never carried it; symbol changes, share classes, mergers, and delistings need issuer/ISIN-level reconciliation.
- A found instrument does not prove that its IPO-day candles are available.
- A returned empty event window is recorded separately from an API error.
- An archived instrument can still have useful historical candles. Do not filter it out before the audit.
- Volume units differ: Finam bars report shares; T-Invest minute archive data report lots. The normalised Candle model preserves volume_unit and does not silently convert lots into shares.
- Daily bars are not sufficient to reconstruct the exact first trade or intraday opening auction. Use minute bars where available and preserve the vendor's session/time conventions.
- The coverage audit is an empirical broker test, not a licence to redistribute raw data. Check each provider's terms before using or publishing collected records.
- Do not treat the sample universe's dates as final training labels. Verify IPO type, exchange, listing date, and any direct-listing/SPAC classification against primary sources before promoting records to the canonical dataset.
