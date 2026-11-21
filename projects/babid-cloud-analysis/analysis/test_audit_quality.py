"""Quality gate prevents treating partial offline scans as validated backtests."""
import unittest

from audit_quality import evaluate


class QualityGateTests(unittest.TestCase):
    def template(self):
        return dict(
            unstable_input_files=0, changed_inputs_across_scan=[],
            reports={
                "history": {"problems": 0},
                "reconciliation": {"states": 1, "local_journal_matches": 1,
                                   "incomplete_or_unverified": 0, "needs_review": 0},
                "configs": {"configs": 1},
                "config_epochs": {"observed_epochs": 2},
                "tape_integrity": {"malformed_books": 0, "unreadable_rows": 0},
                "time_weighted": {"rejected_recordings": 0},
            })

    def test_local_consistency_is_not_approval_for_live(self):
        result = evaluate(self.template())
        self.assertEqual(result["status"], "locally_consistent")
        self.assertFalse(result["independent_broker_reconciliation"])
        self.assertFalse(result["safe_for_automatic_live_tuning"])

    def test_source_modified_during_scan_is_incomplete(self):
        manifest = self.template()
        manifest["changed_inputs_across_scan"] = [{"path": "state-fake/fills.csv"}]
        result = evaluate(manifest)
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("source_modified_during_audit", result["blocking_issues"])

    def test_failed_subtask_cannot_be_green(self):
        manifest = self.template()
        manifest["reports"]["reconciliation_error"] = "synthetic unreadable file"
        result = evaluate(manifest)
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("reconciliation_error", result["failed_subtasks"])

    def test_mismatch_and_unknown_config_issues_are_review(self):
        manifest = self.template()
        manifest["reports"]["reconciliation"]["needs_review"] = 2
        manifest["reports"]["config_epochs"]["observed_epochs"] = 0
        result = evaluate(manifest)
        self.assertEqual(result["status"], "review_required")
        self.assertIn("journal_and_fill_disagreement", result["review_issues"])
        self.assertIn("no_historical_config_events", result["review_issues"])

    def test_corrupt_market_file_blocks_complete_archive(self):
        manifest = self.template()
        manifest["reports"]["time_weighted"]["rejected_recordings"] = 1
        result = evaluate(manifest)
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("market_recorder_rejected_files", result["blocking_issues"])

    def test_missing_studies_are_incomplete(self):
        manifest = self.template()
        del manifest["reports"]["history"]
        result = evaluate(manifest)
        self.assertIn("missing_required_history", result["blocking_issues"])

    def test_truncated_timeline_cannot_be_locally_consistent(self):
        manifest = self.template()
        manifest["reports"]["history"].update(
            incident_events_total=100, incident_events=2, incident_events_omitted=98)
        result = evaluate(manifest)
        self.assertEqual(result["status"], "review_required")
        self.assertIn("incident_timeline_truncated", result["review_issues"])

    def test_geometry_invalid_rows_and_overlap_are_review_issues(self):
        manifest = self.template()
        manifest["reports"]["geometry_validation"] = {
            "invalid_source_rows": 2, "possible_overlapping_groups": 1,
        }
        result = evaluate(manifest)
        self.assertEqual(result["status"], "review_required")
        self.assertIn("geometry_input_rows_invalid", result["review_issues"])
        self.assertIn("market_hour_overlap_suspected", result["review_issues"])


    def test_logged_position_mismatch_never_gets_clean_status(self):
        report = self.template()
        report["reports"]["history"]["position_mismatch_events"] = 1
        result = evaluate(report)
        self.assertEqual(result["status"], "review_required")
        self.assertIn("broker_journal_position_mismatch_logged", result["review_issues"])

    def test_first_position_transition_opt_in_requires_review(self):
        report = self.template()
        report["reports"]["position_evidence"] = {"reported_external_transitions": 1}
        result = evaluate(report)
        self.assertEqual(result["status"], "review_required")
        self.assertIn("external_position_transitions_reported", result["review_issues"])

    def test_ambiguous_market_sessions_block_full_audit(self):
        manifest = self.template()
        manifest["reports"]["market"] = {
            "rejected_recordings": 2, "quality_warning_files": 0,
        }
        result = evaluate(manifest)
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("ambiguous_market_study_recordings", result["blocking_issues"])

    def test_corrupt_opportunity_rows_require_review(self):
        manifest = self.template()
        manifest["reports"]["opportunity_validation"] = {"warnings_total": 2}
        result = evaluate(manifest)
        self.assertEqual(result["status"], "review_required")
        self.assertIn("opportunity_validation_input_corrupt_or_duplicated",
                      result["review_issues"])


if __name__ == "__main__":
    unittest.main()
