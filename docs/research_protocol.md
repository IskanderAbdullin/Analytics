# Research protocol

## 1. Evidence hierarchy

Prefer, in order:
1. Regulatory filings and official exchange / regulator disclosures.
2. Issuer investor-relations releases and audited financial statements.
3. Official market-data and macroeconomic sources.
4. Reputable newswires and established financial publications.
5. Broker research and named analyst commentary.
6. Public forums and social media as measures of attention or expressed opinion, not as verified facts.

For every datum record the source URL, publisher, publication/availability/retrieval timestamps, evidence type, confidence grade, and any licence or access limitations.

## 2. Anthropic as the first case study

Anthropic is the first event to investigate, not a source of assumed labels or a reason to tune the model. The earlier conversational research is a lead list only. Each material claim must be checked against the actual filing, exchange notices, official statements, or a traceable market-data source before it is entered.

Keep separate:
- verified filing facts;
- third-party estimates;
- analyst opinions;
- forum anecdotes;
- synthetic examples.

Do not treat an announced or forecast index-flow estimate as an executed purchase. Do not treat shares becoming eligible for sale as actual selling. Distinguish registered shares, restricted securities, lock-up releases, and freely tradable float.

## 3. Sentiment collection

Use public and permitted sources only. Respect API terms, rate limits, robots policies, copyright, privacy, and data-retention rules. Do not bypass login walls, paywalls, or technical restrictions.

Store individual message identifiers only where permitted. Prefer aggregate, privacy-preserving features. Deduplicate cross-posts and syndicated stories. Distinguish message volume, unique authors, engagement, sentiment, stated trading intention, argument/topic, and author history.

A positive mention is not equivalent to an order or a funded intention to buy. Report sampling bias and coverage gaps.

## 4. Historical reconstruction

For each forecast origin, freeze an information cut-off. Features must be available by that timestamp. Record source vintages and revisions. If an archive cannot establish when a fact became available, mark it as uncertain or exclude it from strict point-in-time backtests.

Never use final prospectus facts in a preliminary-filing forecast if those facts were not public at that time. Never use first-day volume, closing price, or post-open order-book data in a pre-open forecast.

## 5. Labels and market data

Specify exchange timezone, session calendar, currency, price source, adjustment policy, treatment of halts, and definition of first trade. Do not mix delayed quotes with official auction/opening prices without a flag.

For long horizons, account for splits, distributions, delistings, and corporate actions. Record missing outcomes and delisted issuers; do not silently drop failed IPOs.

## 6. Modelling and reporting

Start with transparent baselines. Evaluate by event and by calendar period. Report MAE/RMSE for returns, directional accuracy, Brier score/log loss for probabilities, calibration, interval coverage, and cohort size.

Compare model output with zero-return, historical median, recent IPO cohort, and sector / market benchmark baselines.

Use walk-forward evaluation and preserve an untouched final test period. Document every experiment and configuration. Avoid claiming causal effects from feature importance or observational sentiment.

## 7. Decision-support boundaries

Forecasts are uncertain, especially for IPOs with sparse comparable history and rapidly changing market regimes. Show ranges and uncertainty. Do not present a single point estimate as certainty or as personal financial advice.
