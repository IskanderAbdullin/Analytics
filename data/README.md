# Data layout

The repository intentionally starts without historical observations. Do not invent or backfill values from memory or unsourced summaries.

## Folders

- raw/: immutable source snapshots, organised by source and retrieval date.
- interim/: normalised tables.
- processed/: point-in-time modelling datasets.
- templates/: empty CSV schemas committed to Git.
- source_registry.csv: catalogue of sources and their access/licensing constraints.

Local data folders are git-ignored. Commit only data that is public, redistributable, and useful as a small reproducible fixture. Large, paid, personal, or restricted datasets must stay outside Git and be referenced by a manifest/checksum.

## Tables

1. ipo_events.csv — issuer, listing, exchange, and deal metadata.
2. feature_observations.csv — long-form, source-attributed feature observations.
3. forecast_origins.csv — each prediction decision and its information cut-off.
4. outcomes.csv — realised market prices and derived targets.
5. source_registry.csv — source catalogue.

Every observation needs an observation timestamp and an availability timestamp. The latter determines whether a value could have been used by a model at a historical forecast cut-off.

## Evidence labels

- observed: directly reported or measured, with a primary/credible source.
- estimated: an estimate or derived value with its method recorded.
- analyst_opinion: a third-party forecast or opinion, not a fact.
- synthetic: generated only for tests or demonstrations.

Confidence grades are metadata, not a substitute for source verification. Never silently convert estimates or opinions into observed facts.
