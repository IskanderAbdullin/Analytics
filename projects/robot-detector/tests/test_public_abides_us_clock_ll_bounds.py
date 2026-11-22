"""One-microsecond bucket exact-ns partial-identification falsifiers."""
from math import log
import unittest

from tools.public_intensity_rescaling import Abstain
from tools.public_abides_us_clock_ll_bounds import (
    COARSE_PRECISION,microsecond_bucket_LL_gain_identification_set as bound,
)
from tools.public_abides_export_precision_ll import abides_lossy_us_clock_LL_falsifier as panel


def example(k=2,**kw):
    return bound(k,conditional_rate_per_second=kw.pop("conditional_rate_per_second",.75),
                 constant_rate_per_second=kw.pop("constant_rate_per_second",.625),
                 fixed_integrated_M0_minus_M1=kw.pop("fixed_integrated_M0_minus_M1",-.375),
                 **kw)


class SourceFreeMicrosecondBucketLLIdentificationTests(unittest.TestCase):
    def test_two_identical_microsecond_fills_identification_set_not_point(self):
        r=example()
        self.assertEqual((r["possible_distinct_original_ns_clusters_min"],
                          r["possible_distinct_original_ns_clusters_max"]),(1,2))
        self.assertAlmostEqual(r["lower_bound_conditional_minus_constant_LL"],log(.75/.625)-.375,places=12)
        self.assertAlmostEqual(r["upper_bound_conditional_minus_constant_LL"],2*log(.75/.625)-.375,places=12)
        self.assertAlmostEqual(r["identification_width_LL"],log(1.2),places=12)
        self.assertTrue(r["NOT_a_statistical_confidence_interval"])

    def test_exact_previous_source_free_clock_panel_attains_both_endpoints(self):
        p=panel()["cases"]
        r=example()
        self.assertAlmostEqual(p[1]["M1v4_minus_M0_LL"],r["lower_bound_conditional_minus_constant_LL"],places=12)
        self.assertAlmostEqual(p[2]["M1v4_minus_M0_LL"],r["upper_bound_conditional_minus_constant_LL"],places=12)

    def test_one_coarse_bucket_single_execution_identification_collapses(self):
        r=example(1)
        self.assertEqual(r["possible_distinct_original_ns_clusters_max"],1)
        self.assertEqual(r["identification_width_LL"],0)

    def test_microsecond_has_at_most_1000_original_ns_ticks_even_many_fills(self):
        r=example(1001)
        self.assertEqual(r["possible_distinct_original_ns_clusters_max"],1000)
        self.assertEqual(r["coarse_bucket_public_execution_rows"],1001)

    def test_high_rate_below_null_rate_reverses_endpoint_order(self):
        r=example(2,conditional_rate_per_second=.5)
        self.assertAlmostEqual(r["lower_bound_conditional_minus_constant_LL"],2*log(.5/.625)-.375,places=12)
        self.assertAlmostEqual(r["upper_bound_conditional_minus_constant_LL"],log(.5/.625)-.375,places=12)

    def test_same_rates_exact_identification_no_guessing(self):
        r=example(9,conditional_rate_per_second=.625)
        self.assertEqual(r["identification_width_LL"],0)
        self.assertEqual(r["lower_bound_conditional_minus_constant_LL"],-.375)

    def test_invalid_counts_boolean_zero_negative_and_excessive_abstain(self):
        for k in (0,-1,True,2.3,"2",None,100001):
            with self.subTest(k=repr(k)),self.assertRaises(Abstain):
                example(k)

    def test_invalid_rate_and_fixed_full_window_integral_reject(self):
        for kw in ({"conditional_rate_per_second":float("nan")},
                   {"conditional_rate_per_second":0},
                   {"conditional_rate_per_second":True},
                   {"conditional_rate_per_second":10**500},
                   {"constant_rate_per_second":0},
                   {"fixed_integrated_M0_minus_M1":float("inf")},
                   {"fixed_integrated_M0_minus_M1":None}):
            with self.subTest(kw=str(kw)[:45]),self.assertRaises(Abstain):
                example(**kw)

    def test_unknown_clock_or_rate_change_inside_bucket_abstain(self):
        for opts in ({"source_clock_precision":"nanoseconds_since_exchange_local_midnight"},
                     {"source_clock_precision":None},
                     {"source_clock_precision":"unverified"},
                     {"whole_bucket_rate_constant":False},
                     {"whole_bucket_rate_constant":1}):
            with self.subTest(opts=opts),self.assertRaises(Abstain):
                example(**opts)

    def test_no_private_owner_model_labels_or_real_market_fdr_claim(self):
        r=example()
        for k in ("agent_id","order_id","timestamp_ns","source_times","true_owner_count",
                  "p_value","confidence_level","source_public_tape"):
            self.assertNotIn(k,r)
        self.assertFalse(r["physical_owner_identity_known"])
        self.assertFalse(r["real_market_fdr_known"])
        self.assertFalse(r["original_nanosecond_timestamp_sequence_known"])
        self.assertEqual(r["original_source_runs_generated"],0)


if __name__=="__main__":
    unittest.main()
