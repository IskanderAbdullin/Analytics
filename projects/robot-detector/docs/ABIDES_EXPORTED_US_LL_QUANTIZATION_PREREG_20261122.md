# ABIDES source-free exported-microsecond clock versus exact-ns LL sensitivity — preimplementation 2026-11-22

**SOURCE-FREE PROSPECTIVE FALSIFIER.** The old ABIDES CSV serializer retained only six fractional microsecond digits and can map two distinct integer-nanosecond source events to the same ISO string. This study quantifies how that loss of source identity would affect an already-trained exact-ns M0/M1-v4 held-out LL, NOT the actual old 160-case original matching-engine source study (which used in-memory exact ns), and NOT any real source coarsening estimate. All source-free background tapes and model rates have already been inspected; this is an adversarial math regression, not a blinded holdout.

## Frozen original public source-free train model and eval window
Reuse only earlier constructed ABIDES public matched EXEC train cases low-world [34202,34206) and high-world [34212,34216), source-free Unix epoch ns declared UTC date 20210205, sparse L2 post-event BBO and +1s causal lag. Frozen rates from prior exact test: M0 constant 0.625/s, M1-v4 low 0.75/s, high 0.5/s. Eval source-free [34222,34226), BBO at34220 low, at34222.5 high, at34223 low. All heldout compared public EXEC events lie LOW before book effective time 34223.5, and the complete-window compensator stays M0 2.5 / M1-v4 2.875.

Compare THREE deterministic public source-free tapes:
(A) truly ONE public original execution at exact 34222.500000000 seconds;
(B) truly TWO public executions both at EXACT 34222.500000000 seconds (split fills; one source-time cluster);
(C) truly TWO public executions at exact 34222.500000000 and 34222.500000001 seconds, 1ns apart, **distinct source-time clusters**, but old _date_utc emits IDENTICAL microsecond ISO text for the two original source times.
A and B have identical *cluster-intensity LL* but different raw execution multiplicity. C yields one additional exact public event cluster, so vs B its M0 LL difference is log(.625)=-0.470003629245736, M1-v4 LL difference log(.75)=-0.287682072451781; hence difference of conditional model relative to baseline gains log(.75/.625)=+0.1823215567939546 strictly due to time representation. If C is rounded through CSV timestamps before inference, its distinct source-time count collapses and the spurious apparent model ratio shift is LOST. This is a source-free technical warning, not evidence of an actual original source rate.

## Frozen hard negatives and output boundaries
- Verify _date_utc(Unix epoch t) identical for 1ns different timestamps, while exact source-free model scores correctly show C has two clusters and A/B one. Never change old exporter, frozen source data or model.
- Additional +1000ns case is a different microsecond ISO string, and full-clock native lossless adapter preserves its distinction.
- If timestamp comes as ISO microsecond string instead of exact int64 Unix epoch ns, source-free ABIDES clock and sparse quote source gate ABSTAIN; do NOT silently infer missing source nanosecond suffix.
- Check that quote exposure and integrated compensators are unchanged across A/B/C; physical owner count not inferred even from A vs B.
- Output allowlisted compact all-three-case LL/integral/counts and exact first/second differences, no source full timestamps or private/oracle IDs, no p-values/real market FDR or owner accuracy. No original ABIDES source new seeds/runs, vendor data, real trading or Computer Use.
- All outcomes including negative for M1-v4 relative to M0 on A/B and shifted difference for C must be reported. A positive change in model comparative LL is not proof of bot ownership or a calibrated classifier.

NEXT_ACTION: implement source-free three-tape exact-ns vs old CSV microsecond collision panel and tests, run checked-out cheap public Python CI. Then update separate pinned ABIDES source science NO-GO report and project checkpoint, preserve not-a-market result.
