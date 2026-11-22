"""Single-command source-free reproduction cannot export vendor rows or FDR."""
import json
from math import log
import unittest
from tools.public_ns_repro_demo import source_free_ns_pipeline_aggregate


class SingleCommandSourceFreeReproTests(unittest.TestCase):
    def test_exact_preregistered_one_command_reproduction(self):
        r=source_free_ns_pipeline_aggregate()
        self.assertEqual(r["status"],"SOURCE_FREE_NS_REPRO_NOT_MARKET_VALIDATED")
        self.assertEqual(r["original_training_source_worlds"],2)
        self.assertEqual(r["training_visible_clusters"],5)
        self.assertEqual((r["training_low_rate"],r["training_high_rate"]),(.75,.5))
        self.assertEqual((r["evaluation_public_messages"],r["evaluation_visible_type4_executions"],
                          r["evaluation_visible_type4_clusters"],r["evaluation_hidden_type5"]),(5,2,1,1))
        self.assertEqual(r["integrated_intensity"],2.875)
        self.assertAlmostEqual(r["heldout_log_likelihood"],log(.75)-2.875,places=12)

    def test_all_output_fields_allowlisted_no_market_source_or_owner(self):
        r=source_free_ns_pipeline_aggregate()
        self.assertEqual(set(r),{
            "status","model_unit","original_training_source_worlds","training_visible_clusters",
            "training_low_rate","training_high_rate","evaluation_public_messages",
            "evaluation_visible_type4_executions","evaluation_visible_type4_clusters",
            "evaluation_hidden_type5","integrated_intensity","heldout_log_likelihood",
            "source_accuracy_calibrated","real_market_fdr_known","physical_owner_identity_known",
            "original_ABIDES_or_vendor_source_runs","raw_vendor_rows_exported",
            "external_source_completeness_verified","source_study_execution_authorized",
        })
        self.assertFalse(r["source_study_execution_authorized"])
        self.assertFalse(r["real_market_fdr_known"])
        for forbidden in ("source_public_sha256","timestamp_ns","bid_price","ask_price",
                          "owner_id","agent_id","order_id","book_rows","source_event_rows"):
            self.assertNotIn(forbidden,r)


if __name__=="__main__":
    unittest.main()
