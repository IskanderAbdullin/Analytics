# Prospective integrated ns public source → M1-v3 → held-out score (2026-11-22)

**PROSPECTIVE SOURCE-FREE DESIGN BEFORE IMPLEMENTATION.** All supplied tapes are newly constructed synthetic unit fixtures, NOT independently generated genuine ABIDES worlds, original vendor archive, model holdout, calibration, or physical owner evidence. No fresh seeds nor vendor download. The strict prior methods for source-Decimal→ns, LOBSTER type4 projection, M1-v3 training and ns heldout likelihood are immutable in this stage.

## Frozen integration question
Can an explicitly public-only paired **message + POST-event BBO** tape, with executions from visible type4 only, be scored using a separately frozen trained ns M1-v3 without accidentally (a) treating cancels/submissions as trades, (b) using a current event's own book as a pre-event feature, (c) interpreting 1ns-separated print timestamps as duplicate 1ms clusters, or (d) combining event counts from one source with unrelated books?

Data flow:
1. Source-free input is the exact public ns type4 projection, with fixed 1ns source precision and caller-asserted full event continuity; no private or vendor raw fields. Type4 visible execution clusters, type5 hidden and other message counts are distinct. No owner IDs.
2. Freeze model training on prior two fixed toy worlds low-world and high-world: M1-v3 training-only median spread 2/101, rates low .75/s high .50/s. No re-fit on scoring tape.
3. New integration requires the **same exact snapshot tuple** be supplied to M1-v3 evaluation and taken from source projection; mismatched source books or unit/run ID contamination ABSTAINS. Eval window is [34222s,34226s) in integer-ns since exchange-local midnight. No type4 visible event may lie outside that window (fail, do not silently drop), but source pre-window nontrade BBO context is allowed.
4. Predictions are fixed causal 1s-delayed exposure segments; score only the type4 visible execution clusters using separately frozen ns full-window likelihood (LL=sum log rate−full-window compensator). The integrated helper must not accept any private story, nonpublic oracle truth or physical owner ID.
5. Aggregate only: visible executions/clusters, hidden type5 count, other message count, exposure segments and LL, source quality asserted-vs-verified distinctions, identity/FDR UNKNOWN. No book prices, raw source timestamp rows or order IDs exposed.

## Freeze complete source-free constructed fixture BEFORE scoring
Timestamps below are decimal exchange-local seconds, converted losslessly to nanoseconds:
- t34220.0: event type1, post-event BBO bid100 ask102
- t34222.5: type4 side=-1 (aggressive BUY), post-event bid100 ask102
- SAME t34222.5: type4 side=+1 (aggressive SELL), post-event bid100 ask104
- SAME t34222.5: type5 hidden, post-event bid100 ask104
- t34223.0: type2 delete, post-event bid100 ask102
Thus **5 messages**, **2 visible type4 executions** but **1 unique type4 timestamp cluster**, **1 type5 hidden**, **2 non-type4/type5**, 3 exact post-event BBO snapshots. Source BBO changes become effective at 34221 (initial low), 34223.5 (high), 34224 (low). In [34222,34226), exposure: LOW 1.5s, HIGH .5s, LOW 2s. Full expected integral=1.5×.75 +.5×.50 +2×.75 = **2.875**, and one visible trade at34222.5 has LL=log(.75)−2.875. This is descriptive, NOT any bot detector positive.
- Distinct 1ns event type4 at34222.500000001 must increase visible timestamp clusters to 2, whereas second type4 at exactly34222.5 must not. No source price/id export.
- Make a type5-only constructed tape: visible type4 count=0, valid no-event LL=-integral; this is NOT proof of no bot or complete market capture.

## Hard negatives / acceptance
- A projected input from one source with a different evaluation book tuple, wrong ns unit, missing/truncated source continuity, bad train/eval run ID or out-of-window type4 trade must ABSTAIN. Do not silently select favorable source windows or events.
- Same source public tape with different invented private actor stories yields identical public-only outputs (no private story parameter). No source provenance proof or FDR from synthetics.
- Future book after visible trade only changes intensity after 1 full second, never retroactively.
- Invalid input types/forged oracle/order field/unsafe timestamp/nonfinite rates reject by previously frozen upstream validators; integration must never bypass them.
- Run exact public Python CI on committed code, preserve any failure; output-only safe aggregate and no source job or new market seed.
- The historical real LOBSTER 110818 ms collisions apply to **all original message events**, not measured type4-only; that empirical trade-only loss fraction remains UNKNOWN.

NEXT_ACTION after integration: harden original-run provenance and independent source train/calibration/evaluation guard, review actual LOBSTER timestamp representability and data rights without re-downloading original ZIP.
