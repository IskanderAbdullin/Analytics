# One-command reproducible public-only ns pipeline aggregate (preimplementation freeze, 2026-11-22)

Status: SOURCE-FREE CONSTRUCTED EXAMPLE ONLY. This is not an original-source or new-seed run; synthetic fixtures are for deterministic method verification. Separate prior code and source-study scientific NO-GO remain unchanged.

## Frozen example before execution
Use exactly 2 distinct public-only training original-run fixture labels and source rows:
1. low-world (34202,34206), message type1 at 34200 with BBO100/102, type4 34202.5 same book, type2 34203 with BBO100/104, type4 34203.5 and type4 34204.25 with same BBO100/104.
2. high-world (34212,34216), type1 34210 BBO100/104, type4 34212.5, type2 34213 BBO100/102, type4 34214.25.
All timestamp values exact Decimal exchange-local seconds to integer nanoseconds; no original source data or private field.
Three low training type4 clusters over 4s and two high type4 over 4s, trained M1-v3 median spread 2/101, rates .75/s and .5/s.

The disjoint eval-world source rows are frozen: type1 at 34220 BBO100/102, type4 at34222.5 BBO100/102, type4 same timestamp with BBO100/104, hidden type5 same timestamp BBO100/104, type2 at34223 BBO100/102. Model sources must be bound by canonical public original-run digests and distinct safe source labels; no source ID conflict. Eval visible type4=2 execution rows, exactly ONE distinct type4 nanosecond cluster; type5 hidden=1, other messages=2; M1-v3 future-only book intervals imply integrated rate 2.875 and heldout LL log(.75)-2.875. The same source projection and digest must be used for evaluation book and visible timestamp rows. Other source or mismatch must ABSTAIN.

## Output / CLI requirements
Provide one no-network Python command from project root that constructs these exact source-free training/eval rows in memory, trains only on original bound public visible type4 and scores with the already committed full ns lagged BBO LL. Output exactly one small JSON object of ALLOWLISTED aggregates: status SOURCE_FREE_NS_REPRO_NOT_MARKET_VALIDATED, original_training_source_worlds=2, training_visible_clusters=5, training_low_rate=0.75, training_high_rate=0.50, evaluation_public_messages=5, evaluation_visible_type4_executions=2, evaluation_visible_type4_clusters=1, evaluation_hidden_type5=1, integrated_intensity=2.875, heldout_log_likelihood=log(.75)-2.875, model_unit nanoseconds_since_exchange_local_midnight, source_accuracy_calibrated=false, real_market_fdr_known=false, physical_owner_identity_known=false, original_ABIDES_or_vendor_source_runs=0, raw_vendor_rows_exported=false, external_source_completeness_verified=false, source_study_execution_authorized=false.

No raw event times, price/size/book rows, private owner/agent/order IDs, source SHA, vendor records, keys or timestamps in emitted JSON. Predeclare two regression tests for exact aggregate math and no unauthorized fields. Existing project-source readiness hard-stop gate remains NO-GO for original data.

Acceptance: exact GitHub public Python CI 267 source-free tests (265 existing + 2 new), plus one cheap CLI smoke in same workflow without any source network. Do not write raw/test files or launch ABIDES/Lobster workflows. Preserve original scientifically negative source clock/power results and absence of true real market FDR.
