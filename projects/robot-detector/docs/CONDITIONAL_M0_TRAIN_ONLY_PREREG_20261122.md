# M0 causal cluster-rate baseline — prospective engineering protocol (2026-11-22)

Status: PRE-IMPLEMENTATION, source-free. This is an M0 diagnostic only, not a detector, hypothesis test, p-value, or calibrated model comparison. No new seeds, vendor data, ABIDES source runs or holdouts are used.

## Frozen before implementation

Input is an ordered sequence of public unique-timestamp clusters, plus explicit observation start/end times in integer milliseconds. All timestamps must be nonnegative integers (not bool); at least two unique clusters; start < first event and last event < end. Count each simultaneous split-fill cluster exactly once. Reject missing/invalid observation denominator, duplicate/unsorted events, nonpositive rates and any unsupported fields. Training and prediction are disjoint *run-level* partitions; no events from the evaluation run may influence fitted rate. The baseline constant hazard is count(unique clusters)/((end-start)/1000), fitted ONLY on declared training runs. Require >=1 training run and positive observed event count. No prior on rates, no parameter selection, no new seed allocation. Predict a fixed rate for a declared evaluation window, returning only an Exposure segment compatible with public_intensity_rescaling.Exposure. No evaluation-time counts enter the fit.

## Adversarial negative tests (predeclared)

1. Simultaneous split fills must not inflate rate; 2. absent or zero-duration observation window abstains; 3. unsorted or out-of-window events abstain; 4. boolean/fractional times abstain; 5. zero-event training abstains; 6. no train runs abstains; 7. evaluation window cannot alter fitted rate; 8. future-data leakage cannot occur through the API (only fixed training counts and exposure). This does not prove that caller-selected runs are truly independent: run-level allocation must be audited separately.

## Next scientific gate

Implement M0, verify exact-source unit tests, then specify M1 strictly prior L2 features and M2 predictable history effects with run-disjoint training/calibration/evaluation. Compare hard-negative momentum, unrelated periodic background, split fills and missing L2 before independent source allocation. Existing 3301–3340 remain spent. Real-market FDR and physical owners remain unknown.
