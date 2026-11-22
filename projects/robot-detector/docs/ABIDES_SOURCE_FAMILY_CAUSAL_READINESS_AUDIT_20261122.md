# ABIDES causal-clock, sparse-source and old-160 readiness audit — 2026-11-22

**Scientific verdict: NO-GO on original-source reanalysis or real-market robot release.** This report reconciles previously pinned upstream source semantics, precommitted constructed source-free tests and original compact metadata. It is NOT an independently sourced evaluation, owner identification, real-market FDR estimate, regulatory permission or new source run.

## Pinned source capabilities and limitations

Pinned upstream revision ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242:
- In abides-markets/abides_markets/simulation/result.py, TradeAttribution.time_ns and L2Snapshots.times_ns are Unix epoch INT64 nanoseconds. TradeAttribution is matched EXEC with maker/taker PRIVATE agent IDs, which must be stripped before any public analysis; a public matched ABIDES EXEC is NOT a historical LOBSTER visible type4.
- Sparse L2 snapshots have variable depth, can be one-sided and may share timestamps with fills. These are separate arrays, unlike the LOBSTER paired message_i / post-event book_i sequence. The source-free model conservatively uses 1-second delayed public quotes and a maximum 10-second age, not verified dissemination latency or exchange capture completeness.
- Pinned compiler sets date_ns from pandas date of market.date and then adds market start/end times; source ModelConfig date default is 20210205, but actual external original run date MUST be verified from pinned runtime config. Pure source-free conversion tags ns_since_simulated_utc_midnight, never the separate LOBSTER exchange-local unit.
- The separate old project abides_export.py CSV string serializer truncates submicrosecond bits (nanosecond // 1000 to microseconds). Constructed two source ticks 1ns apart can produce the SAME CSV timestamp. The earlier genuine 160-case ABIDES workflow used full-ns in-memory public_projection, so it is inaccurate to claim the old frozen results used coarsened CSV. Real original source submicrosecond collision count was NOT measured.

## Source-free engineering evidence

[Exact source-free public Python CI 335/335](https://github.com/IskanderAbdullin/Analytics/actions/runs/45061407632) and its two safe aggregate-only CLIs at code SHA 500aa043 verify:
1. Explicit typed ABIDES Unix-ns to simulated UTC-day nanoseconds, no float/time-zone guesses, no LOBSTER family coercion.
2. Strict public ABIDES EXEC plus sparse BBO lagged causality, exact repeated ticks/one-nanosecond-distinct events, private agent ID exclusion.
3. Full observation-time quote coverage, including no-trade intervals. Source-free counterexample: quote 34220s and event 34222.5s, evaluation [34222s,34232s) makes event-level BBO eligible but full-window END quote age 12sec fails required max 10sec. Thus event-only eligible rate != valid point-process compensator.
4. Separate ABIDES-only constant M0 and conditional M1-v4 fitted train-only on original-labelled *constructed* public data; they are NOT synthetic matching engine worlds.
5. Complete non-target hard-negative panel: one low timestamp cluster M1-minus-M0 LL -0.1926784432; unrelated regular 3-low cluster background **+0.1719646704** even though no target is asserted; unrelated momentum-like 3-high cluster burst -1.0444306539. Hence better conditional predictive LL on unrelated background is NOT proof of robot, owner or calibrated target alarm; different hypothetical private owner stories on identical public tape do not alter public score.
6. Read-only original 160-case compact metadata shows why no new M1-v4 genuine-source LL can be calculated from counts alone.

## Prior original ABIDES source is genuine but SPENT and insufficient for M1-v4 reconstruction

One prior pinned genuine synthetic matching-engine 160-case experiment used local seeds 3301–3340 across four backgrounds, 156234 prints, 144908 distinct print timestamps, 253386 total L2 snapshot events, and 617 posthoc controlled TWAP fills. Original run #44944144915 and repeat #44944168231 have identical digest 55394e5dfda274613cb081ee4ad44e9b2b8e051eb2e0f0c361e4ee8016431d62; replay does NOT double independent cases. Four background cases of one seed are also paired/dependent. Original grouped Poisson false alarms 6/40, momentum 7/40, fixed 0/40 plus one abstain, controlled TWAP 32/40 detected with seven misses and one abstain. These belong to older frozen periodic-threshold method, not the new M1-v4.

The permanent compact fixture contains source-case aggregate counts/decision masks, **NO exact event-time vectors and NO aligned quote time/price vectors**. Exact M1-v4 full-window LL requires both. Constructed regular/momentum tapes with same three event counts and the same quote history nevertheless have opposite conditional LL deltas because event times fall in different spread regimes. Consequently M1-v4 original-source scores are NOT reconstructable from compact 160-case aggregate, and cannot be invented. Neither old source replay nor already-inspected seeds constitute a new independent holdout.

## Future source-study prerequisites and NO-GO

Before original-data access or new ABIDES source worlds, freeze/verify source research rights and pinned ABIDES revision/dependencies, source simulation date/UTC clock/session, genuine original public capture profiles (TRADE_ATTRIBUTION and L2_SERIES) and full source event-book capture, source provenance hash and original run IDs, side/time order, lag/age and no-event coverage, aggregate-only publication rights, original-world disjoint train/calibration/evaluation cohort allocation with spent-seed exclusion, frozen classifier threshold separate from predictive LL, conservative ABSTAIN criteria and achievable power/resource costs.

Precommitted hypothetical four-way Bonferroni power audit already found that 100 evaluation seed-worlds are not adequate for strict simultaneous target sensitivity/specificity objectives under optimistic p_neg 1..2%; old source Poisson 6/40 and momentum 7/40 false alarms are much worse than those assumed low false-positive rates. Merely expanding sample size does not cure method specificity.

**Decision:** continue only bounded source-free methodological falsifiers and independently documented source-quality/license work until feasible separate original-source protocol exists. No new original source, simulator seeds, vendor ZIP, real trades, Computer Use, physical owner claims or real-market FDR. Master scientific issue #72 remains open.

Source references: https://github.com/GabrieleDiCorato/abides-ng/blob/ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242/abides-markets/abides_markets/simulation/result.py ;
https://github.com/GabrieleDiCorato/abides-ng/blob/ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242/abides-markets/abides_markets/config_system/compiler.py ;
[original full science plan](MASTER_RESEARCH_PLAN.md), [license gates](REAL_SOURCE_LICENSE_GATES.md), [negative power feasibility](INDEPENDENT_POWER_FEASIBILITY_AUDIT_20261122.md).
