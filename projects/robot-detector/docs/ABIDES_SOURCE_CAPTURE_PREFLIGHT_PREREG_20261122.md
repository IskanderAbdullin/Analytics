# Prospective source-free ABIDES original capture-profile preflight, NOT an execution authorization (2026-11-22)

**PREIMPLEMENTATION FROZEN DESIGN.** A separate typed source-file metadata preflight is scientifically necessary before any actual original matching-engine source runs: old ABIDES compact source and current toy capture flags do NOT prove actual captured event+L2 streams or date and clock alignment. This is not a new original-source allocation/protocol, does not change seed_registry or an existing frozen evaluator, does not grant source data rights, and does not run GitHub source actions. Existing generic 3-way seed allocation gate remains the canonical split check; do not duplicate or replace it.

## Source-backed concrete pinned capture requirements
From pinned upstream GabrieleDiCorato/abides-ng revision ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242: TradeAttribution.time_ns and L2Snapshots.times_ns are Unix epoch nanoseconds; source capture requires TRADE_ATTRIBUTION and L2_SERIES profiles; MarketConfig.date YYYYMMDD and start/end HH:MM:SS determine simulation Unix clock. Public book source may be sparse and one-sided; source capture semantics must remain distinct from LOBSTER message-index type4. Existing 160-source study uses an 09:30–09:38 UTC-simulation session, exact original event times in memory, but no permanent public time+BBO vectors; its already-inspected seed worlds cannot be new evaluation units.

## Frozen metadata schema and structural checks
Exact record fields only:
- original_source_run_label, source_family, pinned_revision, configured_simulation_date, simulator_clock_unit, configured_start_HHMMSS, configured_end_HHMMSS;
- requested_result_profiles (strict list of BOTH TRADE_ATTRIBUTION, L2_SERIES, and no PRIVATE AGENT_LOGS), public_l2_capture_mode (literal sparse_l2), requested_l2_depth_per_side (exact positive integer 5), original_source_role (train/calibration/evaluation), source_coverage_attestation (status UNKNOWN/EXTERNALLY_DOCUMENTED/FAILED), source_artifact_checksum_attestation (same status), external_license_rights_attestation (same status), independent_source_world_provenance_attestation (same status).
- No original trading ID/order/agent/private oracle fields, no source market rows, no vendor symbols or executable GitHub actions.
- String fields must exactly match pinned upstream revision/source_family ABIDES_SIMULATOR and time unit unix_epoch_nanoseconds; configured calendar/date must be a real YYYYMMDD date within int64-ns range and within source-free converter session; start/end exactly 09:30:00 and 09:38:00 on toy preflight for compatibility with old original source source-only scenario (not claiming future experiments must use these times).
- Return strict safe aggregate with structurally valid profile/source schema, four explicit attestation statuses, missing/failed external attestation count/keys, independent_original_source_ready=False if ANY missing. Even if all claimed EXTERNALLY_DOCUMENTED, STILL return source_execution_authorized=False, independent_original_source_ready=False, real owner/FDR unknown: self-reported evidence is NOT independently authenticated.
- Reject malformed source field count, unknown source revision, wrong clock day/timezone/unit, profile missing L2 or attribution, private result profiles, wrong L2 depth or one-sided market claim/quote flag mismatches. No fallback to pre-existing compact counts.
- This preflight does NOT allocate seeds, decide sample size or prove train/calibration/eval independence; reuse existing public_run_allocation_gate for separate split structural check when needed. One fake labelled original source only for test; no new original simulator source.

## Frozen negative tests before implementation
1. Positive STRUCTURAL toy with both public profiles, correct explicit date/session clock and all four attestations UNKNOWN returns a source execution NO-GO.
2. Even all four attestations EXTERNALLY_DOCUMENTED does not authorize actual source execution or independent release.
3. Missing public L2, missing TRADE_ATTRIBUTION, extra PRIVATE AGENT_LOGS, wrong source family/time unit/source revision, bool depth, old 20210205 date changed without explicit declared metadata -> fail closed.
4. Direct 20210205 old upstream source date is source-free config contract; no input accepts Unix epoch "us" timestamp strings or LOBSTER source clock.
5. Unexpected oracle/order/agent/vendor identifiers rejected; only aggregate allowed.
6. Show original 160 compact run cannot supply original public profile/trace attestation: old aggregate alone is NOT valid manifest and cannot authorize a new M1-v4 original-source LL.
7. No original-source engine run, new seed, private data, paid external source or market trade. Independent statistical power/cost remains NO-GO.

**NEXT_ACTION:** implement small pure metadata preflight and adversarial tests on exact public Python CI, then reconcile with existing source readiness audit; do not launch source jobs.
