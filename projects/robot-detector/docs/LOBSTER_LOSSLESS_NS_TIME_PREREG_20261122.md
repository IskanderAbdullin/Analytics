# Prospective lossless LOBSTER source-Decimal → integer-nanosecond time contract (2026-11-22)

**PRETEST / PREIMPLEMENTATION FREEZE.** This design is a direct response to the independent source-quality failure measured by [historical source-only audit #45040590585](https://github.com/IskanderAbdullin/Analytics/actions/runs/45040590585): 269,747/269,748 raw timestamps with sub-ms Decimal components; coarsening to integer ms would merge 110,818 distinct exact source times. Those observed aggregate findings are already inspected. This new code-only stage is **not** a fresh independent source validation, a retrofit of frozen M0/M1/M1-v2/M2 or permission to acquire more vendor data.

## Frozen proposed contract

- Source event time is exact Python `Decimal` seconds **after NASDAQ exchange-local midnight**, not Unix UTC epoch, with official demo session bounds `34200 <= t <= 57600` seconds. Never use intermediate binary float or integer millisecond rounding.
- Encode `ticks = t * 1_000_000_000` **only if result is exactly an integral integer**. Any finer-than-nanosecond fraction (e.g. `34200.0000000001`), nonfinite, bool/float/string, out-of-session, negative, out-of-order or unsafe integer beyond `2^53-1` causes explicit `ABSTAIN` (not truncation). This is a conservative source clock representability gate; the public source audit has NOT proved that every actual vendor time is exactly nanosecond representable.
- Allow exact tied original timestamps, preserve one normalized tick per original event row and one distinct tick per original distinct timestamp. No grouping at millisecond granularity. Fixed synthetic cases that differ by 0.0001 second / 0.0009 second **MUST remain distinct**, while repeated exact source timestamp must remain tied.
- Keep source time unit as explicit typed return `SourceNanosecondTimeTape` with `unit="nanoseconds_since_exchange_local_midnight"`; **never** expose its tick tuple as a compatible M1-v2 millisecond input. Existing M1-v2's 1000ms lag/10s stale gate is **not updated** by this stage. A later separately preregistered *new M1-v3* time-aware implementation must convert physical seconds to nanoseconds and preserve the original L2 post-event causal guard. A nanosecond timestamp with no unit must not be confused with milliseconds.
- Return strict safe aggregate only: input row count, number of exact timestamps, exact ties, number of source rows with sub-ms component, number of would-be ms floor collisions, nanosecond encoding result and status; no raw event timestamps, market prices, order references or actor labels in user-visible report.
- Bound input 1..100000 **synthetic** source-free event rows; actual 269,748-row sample requires a separately reviewed stream/chunk path rather than allocating huge fixture arrays. The historical ZIP has already been processed; do **not** download it again just to validate this new converter.
- Source rights, incomplete L2 coverage and absence of independent actor labels remain constraints. Matching a source's byte precision is only a **necessary technical condition**, not proof of correct event causality, full capture or model transfer.

## Predeclared source-free negative controls

1. `Decimal('34200.000000001')` encodes exactly 34200000000001 ns (1ns beyond whole second); `34200.0001` and `34200.0009` remain distinct with floor-ms collision, no loss.
2. Exact duplicate decimal timestamps stay equal ns ticks; no fictitious independent event count.
3. Explicit sub-nanosecond `34200.0000000001`, float, bool, string, NaN, infinity, out-of-bounds and unsorted timestamps ABSTAIN, with no silent fallback.
4. Number of distinct converted ns ticks equals distinct original Decimal stamps, and all source timestamps preserve order and physical differences exactly.
5. A tape explicitly tagged as `ns_since_exchange_local_midnight` must NOT be accepted by existing millisecond M1-v2 training/prediction functions as if it were `timestamp_ms`.
6. Safe summary must exclude raw timestamps, original quote rows, vendor order IDs, private oracle labels; no release FDR or owners.

**NEXT_ACTION:** implement this pure lossless source-free adapter and negative tests, exact cheap GitHub Python CI. No original LOBSTER download, no new ABIDES seed or real-market accuracy claim. If green, preregister separate nanosecond-aware M1-v3 feature contract with original-run data coverage and fit/eval independence, rather than modifying frozen M1-v2.
