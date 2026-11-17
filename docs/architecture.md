# Architecture

## Design goals

The unit of prediction is a forecast decision for one IPO, made at a defined information cut-off, for one target horizon. A single IPO can therefore have multiple forecast origins and horizons. The same IPO must never appear in more than one validation split.

The system is point-in-time: it reconstructs the information set available at the forecast timestamp rather than joining today's revised data to historical outcomes.

## Data flow

1. Source registry: publisher, source type, URL, access method, licence/terms notes, and retrieval policy.
2. Immutable raw snapshots: original filing, exchange notice, market data, news, public posts, or structured dataset.
3. Normalisation: convert timestamps to UTC, standardise issuer and IPO identifiers, currencies, units, and evidence labels.
4. Observation store: long-form rows with event time, publication time, availability time, retrieval time, and source provenance.
5. Forecast origins: the exact timestamp and task definition for each prediction.
6. Point-in-time feature builder: include only observations available at or before the forecast cut-off.
7. Outcome builder: attach realised prices only after the relevant horizon has elapsed.
8. Model training: chronological event-grouped splits, baselines, and then more complex models.
9. Evaluation and reports: metrics by horizon, forecast origin, exchange, sector, deal size, and market regime.

## Forecast origins

- preliminary_filing: after the first public filing, before final offer pricing.
- after_pricing_pre_open: after the final offer price is public, before the first exchange trade.
- post_open: after the first trade. Each post-open forecast must have its own as-of timestamp and reference market price.

These are different prediction problems. They must be trained and evaluated separately or represented explicitly as a categorical feature with strict origin-aware validation.

## Feature families

### Deal structure
Offer price/range, range revision, deal size, primary/secondary mix, shares offered, free float, greenshoe, underwriter syndicate, lock-up terms, insider sale eligibility, and allocation disclosures. Store facts from filings separately from derived estimates.

### Fundamentals
Revenue growth, gross margin, operating margin, cash burn, cash runway, customer concentration, R&D intensity, capital expenditure commitments, debt, and valuation multiples. Preserve fiscal period, currency, accounting basis, and filing availability date.

### Market regime
Broad-index returns and volatility, rates, credit spreads, sector performance, volatility index, IPO issuance pace, recent IPO returns, and liquidity conditions. All values must be timestamped and aligned to the forecast cut-off.

### Sentiment and attention
Unique authors, unique posts, message velocity, engagement, source diversity, bullish/bearish proportions, explicit buy/sell intent, and topic shares. Deduplicate syndicated news and reposts. Treat bot scores and author credibility as uncertain features, not ground truth.

### Comparable IPOs
Past IPO performance and deal characteristics calculated only from IPOs whose outcomes were known at the forecast cut-off. Use rolling cohorts and market-regime matching; avoid selecting comparables with future information.

### Market microstructure
Only for post_open forecasts: spread, depth, imbalance, auction indicators, turnover, volatility, order-book resilience, and trade intensity. Record venue, currency, timestamp, and market-data vendor.

## Modelling layers

1. Naive baselines: zero return, historical cohort median, and simple valuation/deal-size buckets.
2. Regularised models: Ridge/ElasticNet for returns and logistic regression for direction.
3. Tree ensembles: Random Forest and gradient boosting.
4. Probability calibration: Platt or isotonic calibration, fitted only on validation data.
5. Uncertainty: bootstrap or conformal intervals, with coverage tested out of sample.
6. NLP: multilingual classification/embeddings only after a reliable labelled corpus and baseline exist.

## Validation

Use chronological cut-offs and event grouping. A model may be trained on older IPOs, tuned on a later period, and tested on the newest untouched period. If multiple forecast origins/horizons exist for one IPO, all rows remain together.

All transformations that learn from data must be fit on training data only. Report the number of IPOs, not merely the number of rows. Add an embargo when overlapping outcome windows could contaminate a split.

## Initial implementation boundary

Milestone 1 provides schemas, CSV/Parquet loading, source registry validation, point-in-time feature assembly, chronological event splits, regression baselines, metrics, tests, and CI. External ingestion connectors, large-scale NLP, live feeds, and calibrated probabilistic models follow only after the historical dataset has been assembled and audited.
