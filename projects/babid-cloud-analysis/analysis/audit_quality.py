"""Conservative quality gate for an offline Babid Cloud forensic report.

A locally consistent archive is NOT a broker reconciliation or a license to
automatically tune trading parameters. Never convert synthetic tests or a
green process exit into a claim about real-world profitability.
"""
from __future__ import annotations


def evaluate(manifest: dict) -> dict:
    reports = manifest.get("reports") or {}
    critical, warnings = [], []

    def critical_if(test, code):
        if test:
            critical.append(code)

    def warn_if(test, code):
        if test:
            warnings.append(code)

    critical_if(manifest.get("unstable_input_files", 0) > 0, "source_modified_during_hash")
    critical_if(bool(manifest.get("changed_inputs_across_scan")), "source_modified_during_audit")
    failed = sorted(name for name in reports if name.endswith("_error"))
    critical_if(bool(failed), "analysis_subtasks_failed")
    for name in ("history", "reconciliation", "configs", "config_epochs"):
        critical_if(name not in reports, "missing_required_" + name)

    reconciliation = reports.get("reconciliation") or {}
    critical_if(reconciliation.get("incomplete_or_unverified", 0) > 0,
                "incomplete_or_unstable_fill_history")
    warn_if(reconciliation.get("needs_review", 0) > 0,
            "journal_and_fill_disagreement")
    warn_if(reconciliation.get("states", 0) == 0, "no_reconciled_states")
    history = reports.get("history") or {}
    warn_if(history.get("problems", 0) > 0, "missing_or_unreadable_history")
    warn_if(history.get("incident_events_omitted", 0) > 0, "incident_timeline_truncated")
    warn_if(history.get("position_mismatch_events", 0) > 0,
            "broker_journal_position_mismatch_logged")
    warn_if(history.get("accounting_alignment_notices", 0) > 0,
            "income_accounting_alignment_logged")
    warn_if(history.get("accounting_alignment_rows_omitted", 0) > 0,
            "accounting_alignment_report_truncated")
    warn_if((reports.get("position_evidence") or {}).get(
        "reported_external_transitions", 0) > 0, "external_position_transitions_reported")
    warn_if((reports.get("position_evidence") or {}).get(
        "same_timestamp_unordered_intervals", 0) > 0,
        "position_observations_same_timestamp_unordered")
    warn_if((reports.get("config_epochs") or {}).get("observed_epochs", 0) == 0,
            "no_historical_config_events")
    tape = reports.get("tape_integrity") or {}
    warn_if(tape.get("malformed_books", 0) > 0, "invalid_order_books")
    warn_if(tape.get("unreadable_rows", 0) > 0, "unreadable_market_tape")
    warn_if(tape.get("negative_exchange_age", 0) > 0, "exchange_clock_skew")
    geometry = reports.get("geometry_validation") or {}
    warn_if(geometry.get("invalid_source_rows", 0) > 0, "geometry_input_rows_invalid")
    warn_if(geometry.get("possible_overlapping_groups", 0) > 0, "market_hour_overlap_suspected")
    opp = reports.get("opportunity_validation") or {}
    warn_if(opp.get("warnings_total", 0) > 0,
            "opportunity_validation_input_corrupt_or_duplicated")
    market = reports.get("market") or {}
    critical_if(market.get("rejected_recordings", 0) > 0,
                "ambiguous_market_study_recordings")
    warn_if(market.get("quality_warning_files", 0) > 0,
            "market_study_contains_unverified_books")
    weighted = reports.get("time_weighted") or {}
    critical_if(weighted.get("rejected_recordings", 0) > 0, "market_recorder_rejected_files")

    status = "incomplete" if critical else "review_required" if warnings else "locally_consistent"
    return {
        "status": status,
        "blocking_issues": critical,
        "review_issues": warnings,
        "failed_subtasks": failed,
        "independent_broker_reconciliation": False,
        "verified_historical_strategy_epochs": False,
        "safe_for_automatic_live_tuning": False,
        "disclosure": [
            "locally_consistent means only that observed local inputs did not trigger quality gates.",
            "Broker fills, funding, commissions and full historical settings remain unverified.",
            "Do not change live risk limits, trading parameters or real positions from this report.",
        ],
    }
