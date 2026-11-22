# M1-v2 dynamically lagged public L2 exposure — prospective source-free prereg (2026-11-22)

**DESIGN FROZEN BEFORE IMPLEMENTATION.** This is **NEW M1-v2**, not a rewrite or replacement of existing frozen M1 stable-BBO [M1 design](CONDITIONAL_M1_LAGGED_L2_PREREG_20261122.md). Stage RD-PUBLIC-CONDITIONAL-NULL-16, source-free only. It addresses a measurement limitation in M1: one stable book over the entire window is not representative of changing L2. There is no new ABIDES seed, source download, p-value or real-market owner claim.

## Causal feature and time resolution

Use last complete **public** BBO snapshot, strictly delayed by a precommitted **1000ms lag**. Each snapshot timestamp u becomes effective for the model at u+1000ms, and only then changes the predicted rate. Quote prices observed at time >=event time are never used. The 1000ms lag is an intentionally conservative toy engineering gap, NOT measured exchange latency. Exact source timestamp precision **1ms**, strictly increasing unique L2 snapshot timestamps, exact integers in [0, 2^53-1] ms. A public event at a segment transition u+1000 can use snapshot at u because quote existed one full second before; no same-time lookahead. No event is permitted to change its own conditional rate.

Run-level input: `run_id` (ASCII safe nonempty, max 128), `[start_ms,end_ms)`, sorted public cluster timestamps in training-only object, tuple of allowlisted snapshot records exactly `{"timestamp_ms","bid_price","ask_price","complete"}`, declared **source_precision_ms==1**, declared `interval_complete is True`. Evaluation has the same window/books **without any print or oracle fields**. Both source and run quality assertions are external: a locally complete-looking snapshot list does **not** prove exchange-event completeness.

Public quotes require finite positive bid <= ask and `complete is True`; private agent IDs, hidden truths and arbitrary metadata fail closed. Need an initial BBO snapshot satisfying u+1000 <= start; otherwise ABSTAIN. Transitions occur at each later u+1000 strictly within the window, partitioning exposure into nonoverlapping complete half-open intervals. Each segment's source quote must not be older than **10,000ms measured at the segment end**, else entire run ABSTAINS rather than carrying stale book indefinitely. No missing, tied, unsorted or future-book records. Limit 100,000 clusters/snapshots per run to bound resource usage; a larger source needs separate reviewed implementation.

## Train-only M1-v2 rates (never fitted on evaluation)

For each training run compute lagged relative spread `r=(ask-bid)/mid`, `mid=(ask+bid)/2` on **duration-weighted** exposure segments. Fit one deterministic *exposure-duration weighted median* over **training segments from all training original-run IDs**: sort by spread then take the first spread where cumulative training exposure >=50% of total. Tie rule `spread <= median` -> low, `spread > median` -> high. This differs intentionally and prospectively from the original M1 single-BBO/run median; do not compare calibration without independent evaluation.

Count each public timestamp cluster ONCE in its segment (split fills do not increase counts). Assign events occurring exactly on a lagged transition to the **new** regime. Pool cluster count/exposure-ms in low/high, `rate=count*1000/exposure_ms`. Missing eligible exposure, zero clusters in either regime, zero/infinite rate, duplicate source run IDs or insufficient coverage -> ABSTAIN. Predict evaluation exposure ONLY using trained median/rates, independently declared evaluation window and L2; no evaluation print counts in the prediction interface. Reject any evaluation run ID present in training.

## Prespecified falsification and acceptance

- A known complete two-run toy with BBO changes delayed exactly 1000ms gives two rates and correctly tiled prediction segments; compare to a manually integrated known scalar gap.
- A future raw L2 update after an event can only influence **later** model time, never its earlier segment. A raw snapshot exactly at an event must not affect its intensity until 1000ms later.
- Two original BBO histories with different update multiplicities but identical effective spread/time intervals yield the same trained threshold/rates.
- Split fills invariant; training-rate invariance to any evaluation event list (evaluation API must not accept one), strictly disjoint original run IDs.
- Invalid/tied/unsorted/future/absent/incomplete/precision-coarse/stale L2, crossed/NaN book, missing prior BBO, unknown source coverage, malformed timestamps, zero-stratum exposure/cluster counts, private labels all ABSTAIN.
- Non-target fixed20 and momentum-cluster tapes remain **non-target hard negatives** irrespective of apparently predictable L2; no owner or FDR claims. No original source simulations until independent license/revision/split and fit/calibration protocol is frozen.

**Reproducibility requirement:** one short source-free Python CI with all new negative tests and exact SHA, plus preserved 160-original-source negatives. No tuning of L2 lag/age cutoff/median on previously viewed 3301–3340.

**NEXT_ACTION:** implementation and source-free hard negatives, then an independent source-quality and methodological comparison gate.