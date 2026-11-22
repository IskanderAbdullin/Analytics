# Prospective typed type4-visible original-source training for M1-v3 (2026-11-22)

**SOURCE-FREE PREIMPLEMENTATION AND PRETEST FREEZE.** The ns M1-v3 engineering model and integrated heldout scorer passed 243 tests. However older training fixtures provided manually selected untyped public cluster timestamps, while evaluation now explicitly uses LOBSTER-like **visible type4** execution clusters. A train/evaluation event-definition mismatch would make likelihood comparisons meaningless, even with correct arithmetic and source hashes. Resolve this *before* any independent source seeds/data, without rewriting frozen M1-v3 estimation or timestamps.

## Frozen training projection contract

- Each original TRAIN source has validated public-only bound paired messages/post-event BBO, an internal SHA256 public source digest and a safe ASCII local original run label (not a private actor/order ID). A separate typed TRAIN window declares exact ns exchange-local [start,end), matching run label, literal ns unit and source-asserted interval_complete True.
- Build a new NsTrainingRun strictly from **that bound original source**: cluster_times_ns = unique visible event_type4 timestamp clusters from projection, and post_event_bbo = the *same source's* last post-event BBO snapshots from ALL public message types. No caller-supplied arbitrary event list in the new training API. Reject visible type4 outside the declared training window rather than silently crop, and reject run ID/unit/continuity mismatches.
- Run existing frozen fit_ns_m1_v3_train_only on the derived typed training runs, preserving model regime weighted median, frozen +1sec post-event quote lag and 10sec max staleness. Source-only provenance structural registry must check duplicate IDs and replays across the proposed training worlds. No global seed novelty certification or original market source authentication from a SHA.
- Return model for independent evaluation and ONLY safe aggregate counts of training original source worlds, type4 visible execs/clusters and type5 hidden omitted, no market owner/p-value/FDR. Evaluation source/ID must remain disjoint via existing bound scorer, never train on evaluation prints.

## Freeze TWO synthetic original training public tapes before model fitting

Training low-world [34202s,34206s]:
  type1 t34200 bid100 ask102 (initial lag-eligible BBO);
  type4 t34202.5 bid100 ask102;
  type2 t34203 bid100 ask104;
  type4 t34203.5 bid100 ask104;
  type4 t34204.25 bid100 ask104.
Visible TYPE4 event times exactly 34202.5,34203.5,34204.25. Book change only after t34203+1sec =34204; one additional same-regime quote update at34203.5 is allowed, not a rate change. Training exposure low 2sec, high 2sec; cluster counts low2/high1.

Training high-world [34212s,34216s]:
  type1 t34210 bid100 ask104;
  type4 t34212.5 bid100 ask104;
  type2 t34213 bid100 ask102;
  type4 t34214.25 bid100 ask102.
Visible TYPE4 event times exactly34212.5(high),34214.25(low). Training exposure high2sec/low2sec; count high1/low1.
Thus *joint train-only* LOW total=4sec, HIGH=4sec; LOW has3 unique type4 clusters rate 0.75/sec; HIGH has2 unique type4 clusters rate 0.50/sec; weighted-median relative spread exactly2/101.

## Negative controls/falsifiers
1. Exact expected rates/counts/exposures and post-event lag without using private oracle or evaluation prints. Type2 book update influences following rate after +1sec but does NOT count as trade.
2. Appending type1/type2/type5 public messages without new type4 executions does not increase TRAIN event count, though a changed BBO can alter future exposure; type5 excluded from signed visible-process rate and recorded separately.
3. Duplicate same-timestamp type4 split fill remains one source timestamp cluster, while 1ns-apart visible type4 executions remain two; no millisecond coarsening.
4. Source duplicate fingerprint under different ID, repeated source label with conflicting tape, train/eval overlap, unmatched training-window labels/units, incompleteness, no initial prior BBO, stale/unsorted/crossed book, out-of-window type4, forbidden order/agent fields reject without silent fallback.
5. A posterior source label/paired digest is structural only, not original market independence/owner truth or legal permission.
6. No vendor sample download, no ABIDES seeds, no private source joins; exact committed Python source-free tests and journal all failure/negative cases.

**NEXT_ACTION:** implement source-free bound visible-type4-only training adapter and adversarial CI; then independently audit source completeness and prospective train/calibration/evaluation status. Historical real type4-specific ms collision rate still not measured.
