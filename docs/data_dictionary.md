# Data dictionary and target definitions

## Core identifiers

- ipo_id: stable internal identifier for one issuer's IPO event. Re-listings and separate share classes need explicit rules.
- forecast_id: unique identifier for one prediction decision and one target horizon.
- observation_id: unique identifier for one source observation.
- source_id: key into source_registry.csv.

## Time fields

All timestamps should be stored in UTC with an explicit timezone.

- event_at: when the measured event occurred (for example, a trade or economic period end).
- published_at: when the source published the information.
- available_at: when the information became publicly or operationally available to the model. This is the key point-in-time eligibility timestamp.
- availability_precision: how precisely the availability time is known. Allowed values: exact_timestamp, date_only, conservative_next_session, estimated.
- retrieved_at: when our pipeline collected the record.
- as_of_timestamp: the forecast cut-off. No feature with available_at later than this timestamp may be used.
- listing_date: local exchange listing date, stored as an ISO date. Keep the exchange timezone separately when deriving intraday timestamps.
- target_timestamp: timestamp at which the target price was observed.

Do not automatically equate a filing's acceptance timestamp with the moment its contents became publicly available. The SEC says it does not provide a timestamp for when filing content first becomes available on sec.gov. Preserve acceptance metadata separately. If no exact dissemination timestamp can be established, choose a conservative availability boundary (normally the next exchange session) and mark availability_precision as conservative_next_session.

If a source is revised, preserve the original vintage and record the revision as a new observation. Do not overwrite the historical vintage.

## Forecast origin values

- preliminary_filing
- after_pricing_pre_open
- post_open

## Target horizons

- first_trade
- day1_close
- day5_close
- day20_close
- day60_close
- day180_close

Horizon definitions use exchange trading sessions, not calendar days. Trading calendars and suspensions must be respected.

## Return target

The generic target is:

    target_return = target_price / reference_price - 1

reference_price must be defined for each forecast task and must be knowable at the forecast cut-off.

Suggested reference-price policy:
- preliminary_filing: target is return from the final offer price to the selected post-listing price. The final offer price is part of label construction, not a feature if it was unknown at the cut-off.
- after_pricing_pre_open: reference_price is the announced offer price.
- post_open: reference_price is the last valid traded price at or before as_of_timestamp.

Store target_price, reference_price, target_timestamp, target_return, and reference_price_type. Do not compare forecasts with different reference-price policies without an explicit adjustment.

Useful derived targets:
- first_trade_pop = first_trade_price / offer_price - 1.
- day1_close_vs_offer = day1_close / offer_price - 1.
- day1_close_vs_first_trade = day1_close / first_trade_price - 1.
- post_open_forward_return = future_price / last_price_at_cutoff - 1.

Use adjusted prices for long horizons where corporate actions require it, and retain the adjustment methodology and data vendor.

## Evidence type

- observed: source directly reports or measures the value.
- estimated: modelled, interpolated, or otherwise derived estimate.
- analyst_opinion: external forecast or subjective interpretation.
- synthetic: generated test/demo value only.

## Confidence grade

Use a documented scale such as A (primary source / directly observed), B (reputable secondary source), C (derived or incomplete), D (unverified). Confidence must not replace the evidence type.

## Example feature names

Deal: offer_price, midpoint_of_initial_range, range_revision_pct, primary_share_fraction, secondary_share_fraction, greenshoe_fraction, free_float_pct, lockup_days, insider_sale_eligible_shares.

Fundamentals: revenue_ttm_usd, revenue_growth_yoy, gross_margin, operating_margin, free_cash_flow_ttm_usd, cash_balance_usd, cash_runway_months, r_and_d_to_revenue.

Market: sp500_return_20d, nasdaq_return_20d, sector_return_20d, realized_volatility_20d, treasury_10y_yield, high_yield_spread, ipo_index_return_20d.

Attention: unique_authors_24h, unique_posts_24h, post_velocity_1h, bullish_share, bearish_share, explicit_buy_intent_share, source_entropy, bot_likelihood_mean.

Microstructure: quoted_spread_bps, depth_10bps_usd, order_imbalance, turnover_pct_float, auction_imbalance, trade_count_5m.

All feature names require a written definition, units, calculation window, source, and availability-time policy before entering production.
