"""No original ABIDES M1v4 reanalysis on old 160-case compact metadata."""
from copy import deepcopy
import json
import unittest

from tools.public_intensity_rescaling import Abstain
from tools.public_abides_compact_160_eligibility import (
    FIXTURE,read_existing_compact_160_source_only,
    audit_compact_160_source_reanalysis_possible as audit,
)
from tools.public_abides_m1v4_nontarget_panel import fixed_nontarget_public_panel_aggregate


def original():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class CompactABIDES160ReanalysisNegativeTests(unittest.TestCase):
    def test_real_existing_aggregate_only_not_reconstructable(self):
        x=read_existing_compact_160_source_only()
        self.assertEqual(x["status"],"ORIGINAL_ABIDES_160_COMPACT_NOT_REANALYZABLE_FOR_M1V4")
        self.assertEqual((x["original_synthetic_matching_engine_case_count"],
                          x["original_seed_world_count"],
                          x["independent_worlds_added_by_repeat"]),(160,40,0))
        self.assertFalse(x["new_M1v4_original_source_LL_reconstructable"])

    def test_original_old_false_positives_and_TWAP_misses_retained(self):
        x=read_existing_compact_160_source_only()
        self.assertEqual((x["previous_grouped_poisson_false_alarms_of_40"],
                          x["previous_grouped_momentum_false_alarms_of_40"],
                          x["previous_grouped_fixed_false_alarms_of_40"]),(6,7,0))
        self.assertEqual((x["previous_grouped_TWAP_positive_of_40"],
                          x["previous_grouped_TWAP_missed_cases"],
                          x["previous_grouped_TWAP_abstentions"]),(32,7,1))

    def test_duplicate_source_run_provenance_does_not_add_160_independent_cases(self):
        x=original()
        self.assertEqual(x["original_uncompressed_full_source_json_sha256"],
                         x["repeat_uncompressed_full_source_json_sha256"])
        r=audit(x)
        self.assertFalse(r["source_original_case_replay_is_independent"])
        self.assertEqual(r["independent_worlds_added_by_repeat"],0)

    def test_corrupt_source_hash_seed_range_or_case_count_fail_closed(self):
        for field,value in (("original_uncompressed_full_source_json_sha256","0"*64),
                            ("seeds",list(range(3301,3340))),
                            ("source_full_case_count",320)):
            x=original()
            x[field]=value
            with self.subTest(field=field),self.assertRaises(Abstain):
                audit(x)

    def test_missing_trade_quotes_or_fabricated_raw_agent_fields_rejected(self):
        for name in ("trade_time_ns","agent_id","book_snapshot_event_time","raw_private_truth"):
            x=original();x[name]=[1,2,3]
            with self.subTest(field=name),self.assertRaises(Abstain):
                audit(x)

    def test_cohort_raw_L2_series_not_stored_in_compact_original(self):
        x=original()
        self.assertTrue(all(x["source_cohorts"][k]["l2_snapshots"] is None
                            for k in x["source_cohorts"]))
        x["source_cohorts"]["poisson_noise_null"]["l2_snapshots"]=[1,2]
        with self.assertRaises(Abstain):
            audit(x)

    def test_prior_negative_case_labels_cannot_be_suppressed(self):
        for case in ("poisson_noise_null","momentum_noise_hard_negative","twap_45s_positive"):
            x=original()
            x["source_cohorts"][case]["grouped_positive_seeds"]=[]
            with self.subTest(case=case),self.assertRaises(Abstain):
                audit(x)

    def test_equal_toy_event_counts_and_books_do_not_identify_conditional_LL(self):
        a=fixed_nontarget_public_panel_aggregate()["cases"]
        regular,burst=a[1],a[2]
        self.assertEqual(regular["public_unique_execution_timestamp_clusters"],3)
        self.assertEqual(burst["public_unique_execution_timestamp_clusters"],3)
        self.assertNotEqual(regular["M1v4_full_window_LL"],burst["M1v4_full_window_LL"])
        self.assertGreater(regular["M1v4_minus_M0_LL"],0)
        self.assertLess(burst["M1v4_minus_M0_LL"],0)
        self.assertFalse(read_existing_compact_160_source_only()["source_aligned_L2_quote_timestamp_and_price_vectors_stored"])

    def test_missing_fixture_abstains_not_empty_source(self):
        with self.assertRaises(Abstain):
            read_existing_compact_160_source_only("/definitely/not/here/compact.json")

    def test_safe_aggregate_never_exports_public_event_rows_or_owner_ids(self):
        a=read_existing_compact_160_source_only()
        for key in ("time_ns","source_event_rows","raw_book","agent_id","order_id",
                    "private_truth","event_tape"):
            self.assertNotIn(key,a)
        self.assertFalse(a["physical_owner_identity_known"])
        self.assertFalse(a["real_market_fdr_known"])
        self.assertEqual(a["new_original_engine_source_cases_executed"],0)


if __name__=="__main__":
    unittest.main()
