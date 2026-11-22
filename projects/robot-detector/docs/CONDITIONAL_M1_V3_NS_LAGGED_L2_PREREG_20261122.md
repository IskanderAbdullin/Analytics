# Prospective M1-v3 exact nanosecond causal public BBO (2026-11-22)

**DESIGN FROZEN BEFORE IMPLEMENTATION.** Separate new source-free M1-v3, not an alteration of previous frozen M1, M1-v2 or M2. The negative historical AMZN 2012 source audit found 110818 exact source-time groups merged by naive integer-millisecond flooring. This is no fresh empirical model test, independent holdout, owner validation, vendor download or seed allocation.

## Fixed unit and causal contract
- Nanosecond ticks are exact Python int (not bool), **nanoseconds since exchange-local midnight**, tagged with literal unit nanoseconds_since_exchange_local_midnight; bounded to the official historical session [34200*10^9, 57600*10^9] and no greater than 2^53-1. Unlabeled ms or float times reject. Source-clock independent fidelity is not asserted by a toy adapter.
- Public BBO rows are POST-event after corresponding message. Strict exact allowed fields timestamp_ns, bid_price, ask_price, complete, strictly increasing timestamp after separately validated tie collapse. Finite positive bid<=ask, complete exactly True. Hidden agent/order IDs, source metadata and extra fields reject.
- Effective BBO time = source timestamp + **1000000000 ns** lag. A same-time raw post-event book cannot influence its own event rate. At exactly effective boundary, new regime applies only because raw quote was known a full second earlier. Lag is conservative toy engineering assumption, NOT measured exchange latency.
- Quote age <= **10000000000 ns** at the END of each exposure segment, otherwise ABSTAIN. Require prior lag-eligible BBO at start; asserted 1ns source precision and complete continuity strictly True. Assertions do not prove real exchange source completeness.
- Exact nanosecond exposure durations and sorted integer public event times, <=100000 samples per run, no float or ms coercion. Identical timestamp split fills collapse to one public cluster. No one cluster equals one parent/owner assumption.

## Frozen train-only M1-v3 algorithm
Inputs NsTrainingRun(run_id,start_ns,end_ns,cluster_times_ns,post_event_bbo,unit,declared_precision_ns,interval_complete), NsEvaluationWindow(run_id,start_ns,end_ns,post_event_bbo,unit,declared_precision_ns,interval_complete). Evaluation object has **NO event times**; disjoint train/eval IDs.
- Train exposure-duration weighted median of relative spread (ask-bid)/((ask+bid)/2) across all source-free original training runs. Ties low if spread <= median; high only greater. Rates events/sec = counts of **unique** public timestamp clusters divided by nanosecond-exposure duration in seconds. Both strata must have positive counts and duration and finite rate; otherwise ABSTAIN. No trained hyperparameter retuning on old real source.
- Prediction takes frozen model and eval window only and returns NsExposure(start_ns,end_ns,rate_per_second), gap-free, no eval event list. Cross-platform source quality and rights must be verified separately before any actual source experiment.
- Clock arithmetic: calculate duration ratios from bounded exact integer nanoseconds; do not cast absolute ns timestamps to float. Rate float can be used for descriptive predicted intensity only, not for timestamp rounding or calibrated inference.

## Frozen constructed positive math fixture, NOT real robot positive
Two unrelated source-free training worlds:
- low-world window [34202s,34206s]; post-event BBO (34200s, bid100 ask102) then (34203s,bid100 ask104), effective spread-regime transition 34204s; unique print clusters 34202.5, 34203.5 (low) and 34204.25 (high).
- high-world window [34212s,34216s]; post-event BBO (34210s,bid100 ask104) then (34213s,bid100 ask102), effective transition 34214s; unique print clusters 34212.5 (high) and 34214.25 (low).
- Total low 4s, high 4s; 3 low clusters and 2 high clusters yield LOW=0.75/s, HIGH=0.50/s, weighted-median spread=2/101. Evaluation window [34222s,34226s] has public BBO low from 34220s, high from 34223s, effective switch 34224s; expected two exact 2s prediction segments low then high.

## Frozen negative and falsification tests
1. Exact 4s/4s durations and 0.75/0.5 rates, predicted boundaries; 1ns distinct public events remain distinct, no millisecond truncation.
2. Raw same-time post-event quote and future in-window quote cannot affect earlier rates; exact lag boundary uses pre-existing book.
3. Duplicate timestamps counted once; periodic background, momentum burst remain non-target, no actors inferred.
4. Missing prior/stale/unsorted/tied/future L2; bad/NaN/crossed/huge price; mixed units; interval incomplete, unverified precision; missing exposure/zero training stratum; train/eval ID overlap, private fields -> explicit ABSTAIN. No silent carry forward or fake negative.
5. 179+ exact committed cheap public Python tests, no vendor source download/new ABIDES worlds/market p-value.
6. Explicit M1-v2 unit-mismatch rejection; old frozen M1-v2 remains intact.

NEXT_ACTION: source-free M1-v3 implementation and adversarial Python tests; later separately preregister exact ns held-out LL and millisecond-aligned equivalence, plus 1ns-not-rounded contradiction. No actual historical sample validation by this prereg.
