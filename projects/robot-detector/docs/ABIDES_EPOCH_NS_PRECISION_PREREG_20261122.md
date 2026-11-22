# ABIDES pinned Unix-ns vs simulated-session-ns qualification (2026-11-22)

**SOURCE-FREE PREIMPLEMENTATION PREREGISTRATION.** No original market/source data, new ABIDES seed, vendor ZIP, source-run CI, calibration or physical bot claims. Does NOT modify previously frozen ABIDES 160-source study, prior M1-v3 source family or old CSV exporter.

## Source pin and actual pre-existing engineering negative
- Pinned ABIDES-NG revision: ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242.
- Its pinned simulation/result.py defines TradeAttribution.time_ns and L2Snapshots.times_ns as integer **nanoseconds since Unix epoch**, while prior LOBSTER M1-v3 clock unit is **nanoseconds since exchange-local midnight**. These are incompatible physical origins despite same integer unit.
- Pinned config compiler computes date_ns = pd.to_datetime(config.market.date).value and then mkt_open = date_ns + str_to_ns(start_time); MarketConfig default date 20210205. Our toy must explicitly declare that date, not assume actual upstream runtime honored a default.
- Existing older project tools/abides_export.py::_date_utc serializes with replace(microsecond=nanosecond // 1000), **drops 0..999 ns** within a microsecond. A microsecond string is NOT equivalent to the original int64 ns event tape. The old original ABIDES 160-source study used in-memory public_projection of raw time_ns and MUST NOT be falsely described as corrupted by the unrelated CSV path.
- A source clock precision test is NOT an independent synthetic/world experiment. No observed original-source submicrosecond collision statistics are available, and 110818 LOBSTER floor-to-ms collisions are on ALL LOBSTER source messages, not ABIDES executions.

## Frozen pure source-free interface
- Input exact type int Unix epoch nanosecond tick within [0, 2^63-1], explicit simulation_date YYYYMMDD, explicit source unit literal unix_epoch_nanoseconds, exact pinned_revision string equal to the above SHA. Do not accept bool, floats, strings, timezone abbreviations, arbitrary date or private/order fields.
- Compute UTC simulated midnight = calendar day delta from UTC date(1970,1,1) * 86400*1e9 using ONLY integer arithmetic. No floating-point conversion, pytz/DST shift, LOBSTER local-session interpretation or implicit timezone.
- Subtract midnight to get integer nanoseconds tagged ns_since_simulated_utc_midnight, session bounds [34200e9, 57600e9], safe result <= 2^53-1. The date must be 1970..2262 and a real Gregorian date.
- Accept 1..100000 synthetic source timestamps as chronological nondecreasing list/tuple, preserve original exact duplicates and differences down to 1 ns. Return an INTERNAL typed tape with ns ticks and a SAFE aggregate: source row count, exact distinct timestamps, exact ties, submicrosecond source event rows, distinct original timestamps coalesced by microsecond flooring, and external authenticity false.
- The old native LOBSTER M1-v3 source family must **reject** this differently tagged tape; do not pass numeric ticks without explicit type check and separate preregistration.
- Observe that future actual ABIDES original source might use a DIFFERENT configured date/start/end or capture profile; no source data are certified by passing this toy conversion.

## Predeclared synthetic negative cases
1. Date=20210205, raw Unix ns = UTC origin + 34200e9 +1 maps to EXACT simulated clock 34200000000001; +2ns stays distinct. Both share one floored microsecond.
2. Exact duplicates remain one source clock group, two distinct nanoseconds in the same microsecond remain distinct before output.
3. Compare old CSV serialization on a separately frozen constructed pair to show loss of submicrosecond clock bits, but do not run exporter or change frozen original source.
4. Wrong/absent revision or source unit, invalid date 20210229 or bad year, wrong simulation day, outside session, bool/float/NaN, giant/negative/sorted inversion/too many rows, extra source ids reject with Abstain.
5. No automatic cross-family casting: integer ticks from simulated UTC midnight must not be treated as original LOBSTER local midnight. All aggregate outputs forbid raw times, owner IDs and original full source rows.
6. No old source seeds or real vendor data, no p-values, real-market FDR or owner labels.

NEXT_ACTION after this source-free converter passes cheap checked-out Python CI: preregister separate ABIDES market-trades + sparse L2 same-clock causality gate at pinned source revision, with explicit no external completeness proof.
