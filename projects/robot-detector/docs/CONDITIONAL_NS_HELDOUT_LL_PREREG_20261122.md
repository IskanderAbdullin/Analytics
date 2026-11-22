# Prospective ns-native causal M1-v3 held-out log likelihood (2026-11-22)

**SOURCE-FREE PREIMPLEMENTATION FREEZE, no new source run or robot claim.**
Original 2012 LOBSTER AMZN public demo was previously reanalyzed: 110818 exact exchange event timestamp groups would disappear into integer-millisecond buckets. A new typed ns time adapter passed 179 source-free tests, and M1-v3 195 source-free tests after one invalid fixture was fixed, but that is NOT validation of any real feed or a new train/calibration/evaluation split.

## Frozen statistical quantity and unit

For a separately trained, fixed **piecewise public-only rate** λ_s per second on complete half-open integer-nanosecond intervals [u_s,v_s), and a strictly time-ordered *evaluation-only* sequence of public **distinct timestamp clusters** t_i, compute exact time-integrated held-out log likelihood:
LL = sum_i log λ(t_i-) - sum_s λ_s*(v_s-u_s)/1e9 .
At a lagged effective BBO boundary, the new regime is causal because source quote arrived a full 1s earlier. Same original public timestamp may have multiple split fills but contributes exactly ONCE. A raw post-event book at event t cannot affect its own pre-event λ. No in-sample KS significance or owner attribution.

Require typed NsPublicEventWindow with exact allowed fields: unit (literal nanoseconds_since_exchange_local_midnight), start_ns, end_ns, cluster_times_ns, interval_complete. Exact integer ns bounded official session and <=2^53-1, end > start, sorted, event timestamps strictly inside interval, max100000 rows, no source-oracle fields. A **zero-event** asserted complete window is a legitimate LL=-integral but NOT a robot absence prediction.

Exposure inputs EXACT frozen NsExposure dataclass from M1-v3; positive finite rates, exact bool source_complete_asserted and causal_lagged=True, fully gap-free/overlap-free chronological tiling of declared interval, <=100000 segments. Absent, missing, uncertain or malformed source quality, bad rate/NaN/10^500, uncovered end, forged ms units, incorrect source clock/interval completeness, large unsafe number -> explicit Abstain, never zero false alarm.

## Prespecified numeric and scientific falsifiers (source-free)

1. Frozen source-free M1-v3 model has low rate 0.75/sec for [34222,34224) and high 0.50/sec for [34224,34226). Evaluate exactly three clusters at 34222.5, 34224.0 and 34225.5 seconds. LL = log(0.75)+2log(0.5) -2.5 (approximately -4.173976), not a tuned classifier.
2. On exactly millisecond-aligned toy source/evaluation timestamps and same rates, compare this **separate ns implementation** to previously checked-out legacy millisecond fixed intensity scorer; LL and compensator agree within 1e-12. This is analytic interoperability, NOT license or true source continuity.
3. Add a distinct 1ns-separated cluster 34222.500000001; it increases cluster count and adds exactly log(0.75) to LL. Exact duplicate timestamp does not add anything. No collapse at 1ms.
4. Event exactly at effective change 34224.0 uses high rate; future post-event quote at t after evaluation cannot change earlier LL. No printing event rows in scientific aggregate outputs.
5. Empty asserted complete event window has valid LL=-2.5, but real source miss/coverage/owner uncertainty remain unknown.
6. All input/coverage/exposure/type/overflow negatives abort; adversarial periodic or momentum background may yield high/low LL and MUST NOT be called robot. No statistical p-values or estimated market FDR.
7. Deterministic all-case read-only constructed output only; existing untrusted historical data must NOT be used for posthoc model tuning or new holdout claim.

**Acceptance:** source-free code + negative tests exact public Python CI, record both model losses and failures. No vendor sample redownload, ABIDES new seeds, private oracle or real trading. NEXT_ACTION: if green, analyze numeric consistency and genuine source quality/power protocol; no inference on physical owners.
