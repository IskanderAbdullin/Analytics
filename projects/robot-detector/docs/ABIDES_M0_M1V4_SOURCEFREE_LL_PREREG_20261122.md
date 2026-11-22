# Prospective source-free ABIDES M0 vs conditional M1-v4 held-out LL (2026-11-22)

**PREIMPLEMENTATION DESCRIPTIVE FREEZE.** No new ABIDES engine seeds, original matching-engine source runs, vendor market data, calibrated robot alarms, physical owner labels or real FDR. This is a model-specific technical transfer design for the separate **simulated ABIDES public EXEC** process and its **sparse delayed L2**, NOT the LOBSTER type4-visible M1-v3 model. Previous full-window source-free exposure quality CI #45060740356 passed 305/305. Source-family and clock tags must remain distinct.

## Fixed scientific question
On explicitly constructed, previously described public-only toy worlds, compare the **full-window held-out log likelihood** of:
- M0 constant public EXEC timestamp-cluster rate: all unique source train timestamps / all eligible training seconds.
- ABIDES M1-v4: fixed causal +1-second-lagged sparse L2 relative-spread-conditioned rate. Train-only exposure-time weighted median of public best-relative-spread = (ask-bid)/(ask+bid); <=median class LOW, >median HIGH; train rates unique public execution timestamp clusters per second of exposure in each stratum. Exact rational spread ordering (Python Fraction) and exact integer ns exposure durations; floating rates only after normalization. Both strata require positive duration and cluster count or ABSTAIN. Do not reuse LOBSTER M1-v3 input class (different epoch and event semantics).
- Both models must be fitted ONLY on source-free original training cases with distinct run IDs and structurally unique public tape fingerprints; no fit on evaluation print times. Independent real/simulator source worlds are NOT established by these toy IDs/hash comparisons.
- Heldout LL for complete [start,end) on a fixed separately named evaluation toy = sum over DISTINCT exact-ns public EXEC cluster timestamps log of trained rate before each event minus exact sum_s rate_s * (end_s-start_s)/1e9. Quote at raw time u affects M1 only for times>=u+1e9; no event at original same u uses its own quote. At boundary exactly effective u+1s uses updated quote, not original same-time lookahead.
- Input exact validated PublicABIDESSparseL2Eligibility + ABIDESPublicFullWindowExposure with matching unit and exactly recomputed full-time quote tiling (fail on mismatch), stable safe original run labels. Type-safe ABIDES source only, no oracle/private fields, no physical owner attribution.

## Frozen source-free toy worlds (already inspired by earlier LOBSTER toy, NOT independent holdout)
Each fake source has explicitly declared synthetic simulation UTC date 20210205, Unix epoch integer ns; all public source-only values, no private agent IDs.
TRAIN low-world [34202,34206), public sparse quotes: at34200 ask102/bid100, at34203 ask104/bid100; public EXEC exact cluster timestamps34202.5,34203.5 (LOW),34204.25 (HIGH).
TRAIN high-world [34212,34216), sparse quotes at34210 ask104/bid100, at34213 ask102/bid100; public EXEC34212.5 (HIGH),34214.25 (LOW).
Both have full 4-second complete *asserted* time exposure and lagged quote eligibility.
Full training LOW exposure4s, 3 unique clusters, rate=.75/s; HIGH exposure4s,2 unique clusters,rate=.50/s; exact time-weighted median relative spread=2/202 = 1/101; M0 5/8=.625/s.
EVAL [34222,34226), sparse quotes at34220 low; at34222.5 high; at34223 low. Two public EXEC fills at exactly34222.5, one timestamp cluster. Expected quote-delayed intervals [34222,34223.5) LOW (1.5s), [34223.5,34224) HIGH (.5s), [34224,34226) LOW (2s); M1 integral2.875, heldout LL=ln(.75)-2.875=-3.162682072451781, M0 integral2.5, LL=ln(.625)-2.5=-2.970003629245736, difference M1-M0=about -0.1926784432060451 (M1 **WORSE** on this toy). This is a predeclared cross-source synthetic mathematical sanity and NEGATIVE predictive gain; do not describe as new independent evidence of real-market inference, no posthoc retuning.

## Frozen hard-negative tests
1. Exact predeclared rate/median/durations, fixed negative ΔLL; all non-target background rates and possible owner stories are unknown.
2. Duplicate exact ns public execution fills collapse to one cluster, adding distinct +1ns event DOES increase count; same-time owner/parent cannot be inferred.
3. Time-complete quote exposure required in every train/eval case. A single source with valid per-event prior book but stale book by observation END must ABSTAIN for BOTH models rather than claim M0 is an independently calibrated null on unverified coverage.
4. Train/eval original run ID overlap; duplicate training ID/fingerprint/replayed synthetic source; mismatched precomputed exposure vs its public quote source; missing high/low rates, arbitrary private/order IDs, invalid clock/unit/future L2; no source automatically proves genuine original-world independence.
5. Outcome output contains ONLY safe counts and model rates/LL, no raw event times, prices, book rows, agent/physical owner IDs or source digests. Real-market owner/FDR source completeness remain UNKNOWN.

Acceptance: new source-free ABIDES-specific M0/M1-v4 analytic code and adversarial tests with exact cheap public Python CI, not real-market classifier release. If toy negative demonstrates M1 worse, retain. No new original ABIDES worlds or data jobs.

NEXT_ACTION after green CI: publish a minimal ABIDES-vs-LOBSTER source-family boundary comparison and external original-source readiness checklist; stop before expensive simulations while source rights, complete L2, calibration split and power remain unverified.
