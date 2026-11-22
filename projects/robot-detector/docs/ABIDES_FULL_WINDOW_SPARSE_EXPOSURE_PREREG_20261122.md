# Prospective ABIDES source-free full-window sparse L2 exposure quality (2026-11-22)

**PREIMPLEMENTATION FROZEN** after source-free exact CI #45060553826 293/293. This evaluates the technical gap between event-level eligibility and full duration coverage. No original ABIDES source, seeds, LOBSTER vendor files, release FDR or physical owner inference.

## Source-backed scientific limitation
A sparse L2 quote may be lag-eligible for every public execution in a window while the **last observed L2 quote is stale by the observation-window END**. A point-process likelihood integrates intensity over the WHOLE observation interval even when no trades occur, not just at observed trade times. Therefore the previous screen's all-trades-eligible flag CANNOT be promoted to full-window exposure validity. A separate complete observation-time quality gate is necessary; it still cannot prove that the original source feed is truly complete.

## Frozen ABIDES-only contract

- Input exactly previously validated internal PublicABIDESSparseL2Eligibility typed object, explicit source family ABIDES_SIMULATOR, unit ns_since_simulated_utc_midnight, explicit [start,end) integer ns (within [34200e9,57600e9]), source trade and quote continuity caller assertions exactly True. The screen holds INTERNAL original public quote timestamps/grouped final bid and ask, but this proof does NOT export quotes, source raw times or trader identifiers.
- Do not pass through LOBSTER M1-v3 classes or incorrectly identify ABIDES EXEC as visible type4. The frozen toy ABIDES quote lag is exactly 1e9 ns and max quote age at every SEGMENT RIGHT END exactly 10e9 ns. The quote at original time u becomes effective at u+1e9; same-time and future books cannot determine current execution's preevent intensity.
- Construct ordered, gapless, half-open exposure segments over [start,end), splitting at each effective lagged quote time within. At every segment's left, choose the most recent quote with effective<=left; reject missing prior; at segment right, source quote age must be <=10sec or **ABSTAIN ENTIRE WINDOW**, irrespective of earlier trades. Do not silently drop stale intervals or treat an empty segment as no bot.
- Preserve exact nanosecond boundaries (integers, never float times), bounded <=100000 L2 rows and exposure segments, strict source tags. Internally return rational spread numerator=ask-bid and denominator=ask+bid from public top prices, not actual physical owner labels, no training/model rates. Safe aggregate only count/length of segments, full-window exposure duration ns, source asserted-vs-attested difference (original feed independently proven=False), all run market truth/real FDR unknown.
- All original source run/date/rights/profiles and attribution must be externally checked by independent provenance before ANY actual experiment. Current toy screen source quote chronology and caller assertion do not establish venue completeness, actual published feed or model transfer.

## Frozen numeric fixture and negative controls
1. Prior source-free ABIDES sparse public toy: last quote at34220 low bid100 ask102, quote at34222.5 high bid100 ask104, quote at34223 low bid100 ask102; evaluation [34222,34226). Expected segments [34222,34223.5) low relative spread 2/202, [34223.5,34224) high 4/204, [34224,34226) low 2/202. Total 4sec exact, +1s lag strict.
2. **Negative**: a single prior book at34220 and a 10-second observation window [34222,34232). A public EXEC at34222.5 is event-level eligible, but the same book at window end is age12s >10sec, so full-window MUST ABSTAIN. This is a construction proving event-only checks insufficient.
3. Exactly +1ns near a quote effective boundary remains correctly on its side; future raw quote never retroactively changes prior exposure.
4. Source quote tied group must use the last observed BBO only after full 1s lag. Incomplete, stale, no prior, unsorted, wrong exact time-unit, malformed bool/float/extra fields, source rights not attested -> ABSTAIN or explicitly remain NOT_INDEPENDENTLY_VERIFIED, never fake certified source.
5. Do not emit raw quote prices/timestamps or agent/order IDs in public result; no actual ABIDES/LOBSTER source jobs or new seeds. A passed synthetic invariant check is NOT market-FDR calibration.

NEXT_ACTION: code this pure source-free whole-time exposure quality gate with adversarial tests; exact cheap GitHub Python CI, retain all negative outcomes. Then design source-family-specific M0 baseline and preregistered comparison only if warranted, never current original-source execution.
