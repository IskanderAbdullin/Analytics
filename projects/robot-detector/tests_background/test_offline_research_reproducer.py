#!/usr/bin/env python3
"""Strict one-command reproducibility gate without external market downloads."""
from pathlib import Path
from subprocess import CompletedProcess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import offline_research_reproducer as r


def good_runner(args):
    return CompletedProcess(args,0,stdout="",stderr="Ran 3 tests in 0.004s\n\nOK\n")


class OfflineScienceReproducerTests(unittest.TestCase):
    def test_all_sources_are_summaries_and_all_suites_run_without_network(self):
        report=r.reproduce(runner=good_runner)
        self.assertEqual(report["schema_version"],
                         "robot-detector-offline-scientific-evidence-repro-v1")
        self.assertEqual(report["suite_count"],len(r.SUITES))
        self.assertEqual(report["tests_passed_total"],3*len(r.SUITES))
        self.assertEqual([x["suite"] for x in report["source_free_offline_suites"]],
                         list(r.SUITES))
        self.assertTrue(report["all_required_negative_suites_passed"])
        self.assertEqual(report["next_action_from_checkpoint"],
                         r.validate_state(r.load_checkpoint())["current_stage_id"])
        for evidence in report["original_aggregate_evidence"]:
            self.assertEqual(len(evidence["checked_in_sha256"]),64)
            self.assertGreater(evidence["checked_in_aggregate_bytes"],50)
            self.assertFalse(evidence["raw_exchange_archive_in_fixture"])
        for no_claim in ("scientific_goal_completed",
                         "original_source_network_download_or_subscription_performed",
                         "independent_reverification_of_vendor_original_zip_bytes_performed",
                         "actual_physical_robot_owner_truth_available",
                         "real_market_classifier_FDR_calibrated",
                         "complete_exchange_L2_feed_proven",
                         "raw_source_event_book_rows_exported"):
            self.assertFalse(report[no_claim],no_claim)

    def test_missing_test_suites_and_fixtures_fail_closed(self):
        with patch.object(r,"TEST_ROOT",Path("/file_does_not_exist_4321")):
            with self.assertRaises(ValueError):
                r.reproduce(runner=good_runner)
        with patch.object(r,"FIXTURES",r.FIXTURES+("fixtures/no_such_original.json",)):
            with self.assertRaises(ValueError):
                r.reproduce(runner=good_runner)
        with patch.object(r,"SUITES",r.SUITES+(r.SUITES[0],)):
            with self.assertRaises(ValueError):
                r.reproduce(runner=good_runner)

    def test_failure_zero_tests_missing_final_ok_and_nonzero_status_abort(self):
        for retval,log in (
            (1,"Ran 2 tests in 0.002s\n\nFAILED\n"),
            (0,"Ran 0 tests in 0.002s\n\nOK\n"),
            (0,"Ran 4 tests in 0.002s\n\nFAILED\n"),
            (0,"Ran 4 tests in 0.002s\n"),
            (0,"Not a test output"),
        ):
            def broken(args):
                return CompletedProcess(args,retval,stdout="",stderr=log)
            with self.subTest(returncode=retval,log=log),self.assertRaises(ValueError):
                r.reproduce(runner=broken)

    def test_only_registered_test_filename_accepted(self):
        with self.assertRaises(ValueError):
            r._run_source_free_suite("test_do_not_exist.py",runner=good_runner)
        with self.assertRaises(ValueError):
            r._run_source_free_suite("../relative_privileged.py",runner=good_runner)

    def test_offline_reproducer_does_not_run_any_original_source_commands(self):
        calls=[]
        def trace(args):
            calls.append(tuple(args))
            return good_runner(args)
        result=r.reproduce(runner=trace)
        self.assertEqual(len(calls),len(r.SUITES))
        for argv in calls:
            self.assertEqual(argv[1:6],("-m","unittest","discover","-s","tests_background"))
            self.assertEqual(argv[6],"-p")
            self.assertIn(argv[7],r.SUITES)
            self.assertNotIn("curl",argv)
            self.assertNotIn("wget",argv)
        self.assertTrue(result["source_public_demo_research_scope_only"])
        self.assertTrue(result["no_background_execution_promised"])
        self.assertFalse(result["commercial_trade_or_signal_authorized"]
                         if "commercial_trade_or_signal_authorized" in result else
                         result["real_market_classifier_FDR_calibrated"])

if __name__=="__main__":
    unittest.main(verbosity=2)
