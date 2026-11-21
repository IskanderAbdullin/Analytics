# RD-PUBLIC-CONDITIONAL-NULL-16 — measurement-identifiability gate (2026-11-21)

## Pre-analysis statement (source-free; no new holdout)
The original 160 ABIDES cases (seeds 3301–3340) are already inspected. No retuning of the frozen 0.60 ratio, 20/45-second periods, phases, or positive labels is permitted. This document defines a **separate exploratory method**, not a replacement of that protocol.

**Hypothesis H0-occupancy:** a null that preserves the exact multiset of observed timestamp clusters and their positions cannot measure evidence for timing cadence. Under any permutation of cluster multiplicities among fixed timestamps, the unique-timestamp interarrival vector is exactly invariant. Therefore any cadence score based only on those intervals is identical in every null replicate, making its permutation distribution degenerate. A nominal p-value from such a control would be scientifically invalid.

**Public-only contract:** use timestamp (with declared resolution), public print direction, public multiplicity, and strictly prior L2 snapshot only. Reject private agent IDs, owner labels, future/simultaneous L2, hidden source identifiers, and unregistered metadata. Exact-timestamp clusters are observations, not identified parent orders.

**Candidate descriptive period scan:** before seeing new data, enumerate periods P = {5000, 10000, 15000, 20000, 30000, 45000, 60000} milliseconds and tolerances ±50 ms, with every P reported, never best-only. Sort unique public timestamps t_i; for each P report number of consecutive gaps whose distance to nearest integer multiple of P is <=50ms, divided by number of gaps. Zero gaps → ABSTAIN. Also report timestamp precision, number of distinct timestamps, fill multiplicity histogram, UTC-minute occupancy, and prior-L2 coverage. This is descriptive, not an algorithmic-actor probability. Report ALL periods and do not silently select phase.

**Control A (multiplicity only):** permute WHOLE cluster multiplicities among existing timestamps within the same UTC minute. Preserve timestamp positions, minute occupancy, number of fills and multiplicity multiset; explicitly flag timing significance as UNIDENTIFIABLE_UNDER_FIXED_TIMESTAMPS. This control can probe sensitivity to split fills, not clock regularity.

**Control B (future candidate timing null):** conditional resampling of whole cluster timestamp positions inside prespecified minute strata, with exclusion of tied timestamps and collisions, preservation of cluster sizes and exact minute counts. It does NOT preserve local microstructure or burst autocorrelation, so it is a weak timing null unless compared with an additional burst/renewal-preserving control. No inferential p-values until a rigorous conditional exchangeability argument and separate source-free adversarial tests are supplied.

**Hard negatives:** unrelated fixed-cadence public streams are observationally indistinguishable from a target cadence with the same tape; Poisson and momentum backgrounds from the 160 original cases remain false-alarm counterexamples; split fills can inflate print-weighted scores; sparse/unknown timestamp resolution or absent strictly-prior L2 must trigger coverage caveats/ABSTAIN.

## Decision and next action
Reject occupancy-preserving cluster-permutation as a *cadence significance* null (mathematical invariance). Keep it only as a split-fill sensitivity control. Implement and test explicit descriptive period enumeration, source-free burst-preserving and occupancy-conditioned timing controls, and strict previous-only L2 gating before preregistering any new genuine source run. No real owner count, market FDR, or fresh-holdout claims. Preserve issue #72 open.
