# IPO Analytics & Forecasting Engine

A reproducible research and machine-learning platform for forecasting IPO price behaviour across markets and time horizons.

The first research case is the Anthropic IPO, but the system is designed to generalise to other issuers, exchanges, and market regimes. It combines point-in-time fundamentals, deal structure, market conditions, comparable IPOs, news and community sentiment, and post-listing market microstructure.

> **Research integrity:** no observation is considered factual without a source, timestamp, and provenance. Estimates, analyst opinions, synthetic test fixtures, and verified observations must remain distinguishable. Historical features must reflect only information available at the forecast cut-off. The project does not contain a pre-filled Anthropic dataset; facts discussed in external research must be independently verified before ingestion.

## Objectives

1. Build a versioned, source-attributed IPO event database.
2. Reconstruct what was knowable at each forecast origin (point-in-time data).
3. Forecast offer-to-market and post-listing returns at multiple horizons.
4. Estimate calibrated probabilities and uncertainty, not just point predictions.
5. Benchmark against simple baselines and historical IPO cohorts.
6. Evaluate with chronological, event-grouped splits and leakage checks.
7. Keep the workflow reproducible: raw data, transformations, model config, metrics, and forecasts are traceable.

## Forecast tasks

Forecast origins are separate tasks and must not be mixed:

- `preliminary_filing`: after an initial registration statement, before final pricing.
- `after_pricing_pre_open`: after the offer price is announced, before the first exchange trade.
- `post_open`: after the first trade / during the first session. This task may use live market microstructure features.

Initial target horizons (trading sessions): first trade, day 1 close, day 5, day 20, day 60, and day 180. Targets are defined in [the data dictionary](docs/data_dictionary.md). Each task/horizon is evaluated separately.

## Repository layout

```text
config/                 Model and project configuration
data/
  templates/            Empty CSV templates; no fabricated observations
  raw/                  Immutable source snapshots (local, git-ignored)
  interim/              Normalised intermediate data (git-ignored)
  processed/             Model-ready datasets (git-ignored)
  source_registry.csv   Source and provenance catalogue
docs/                   Architecture, methodology, and data dictionary
reports/                Generated evaluation reports (git-ignored)
src/ipo_forecast/
  data/                 Loading and validation
  features/             Point-in-time feature construction
  models/               Baselines and model interfaces
  validation/            Leakage-safe chronological splits
  evaluation/            Metrics and calibration
tests/                  Unit and regression tests
```

## Quick start

Python 3.11 or newer is required.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest
```

The initial milestone establishes schemas, validation, point-in-time feature rules, chronological splits, metrics, and a baseline training interface. A real model is not trainable until verified historical IPO observations and outcome labels have been collected.

## Data policy

- Keep source payloads immutable under `data/raw/<source>/<YYYY-MM-DD>/`.
- Store source URL, publisher, publication time, retrieval time, licence/access notes, and a confidence grade.
- Record both event time and knowledge/availability time. A later correction must not silently rewrite what was knowable historically.
- Never use a value published after the forecast cut-off as a feature.
- Do not treat forum post counts as independent investor demand; deduplicate, identify bots where feasible, and separate authors, posts, engagement, and stated intent.
- Do not scrape private communities or bypass access controls. Respect platform terms, robots policies, rate limits, and applicable law.
- Do not commit credentials, paid datasets, personal data, or raw data whose licence does not permit redistribution.

See [research protocol](docs/research_protocol.md) and [data dictionary](docs/data_dictionary.md).

## Initial model strategy

Start with:
1. Naive cohort / median-return baselines.
2. Regularised linear and logistic models.
3. Tree-based tabular models (for example, HistGradientBoosting / Random Forest).
4. Probability calibration and prediction intervals.
5. Ablation tests for fundamentals, deal structure, sentiment, and market-regime features.

Complex NLP and deep learning are later additions. They must demonstrate out-of-sample improvement over transparent baselines.

## Validation principles

- Split by IPO event, never by individual rows from the same IPO.
- Use chronological train/validation/test periods.
- Fit imputation, scaling, feature selection, text encoders, and calibration on training data only.
- Use nested or rolling-origin validation when the sample size permits.
- Report uncertainty and cohort sample sizes. Do not imply precision unsupported by the number of comparable IPOs.
- Keep a final untouched test period.

## Status

**Milestone 0 — project foundation:** in progress.

No forecasts should be interpreted as investment advice. The system is a research and decision-support tool; model outputs are uncertain and can fail under regime changes.
