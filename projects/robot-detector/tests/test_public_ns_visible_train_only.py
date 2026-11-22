"""Same public type4-only training estimand vs evaluation source-free cases."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from tools.public_intensity_rescaling import Abstain
from tools.public_lobster_ns_time import UNIT,exact_decimal_to_ns
from tools.public_ns_source_binding import bind_public_ns_source,BoundNsEvaluation,score_bound_public_ns_source
from tools.public_m1_v3_ns_l2 import NsEvaluationWindow
from tools.public_ns_visible_train_only import NsBoundVisibleTrainingSpec, fit_ns_m1v3_from_visible_bound_sources


def t(x):return exact_decimal_to_ns(D(str(x)))


def row(time,typ=1,side=-1,ask=102,**extra):
    return dict(timestamp_ns=t(time),event_type=typ,resting_side=side,
                bid_price=100,ask_price=ask,complete=True,**extra)


def low_rows():
    return (row("34200",1),row("34202.5",4),row("34203",2,ask=104),
            row("34203.5",4,ask=104),row("34204.25",4,ask=104))


def high_rows():
    return (row("34210",1,ask=104),row("34212.5",4,ask=104),
            row("34213",2,ask=102),row("34214.25",4,ask=102))


def low(rows=None,rid="low-world"):
    bound=bind_public_ns_source(low_rows() if rows is None else rows,original_run_label=rid)
    return NsBoundVisibleTrainingSpec(rid,t("34202"),t("34206"),bound)


def high(rows=None,rid="high-world"):
    bound=bind_public_ns_source(high_rows() if rows is None else rows,original_run_label=rid)
    return NsBoundVisibleTrainingSpec(rid,t("34212"),t("34216"),bound)


def train(specs=None):
    return fit_ns_m1v3_from_visible_bound_sources([low(),high()] if specs is None else specs)


def eval_source(rid="evaluation-world"):
    rows=(row("34220",1),row("34222.5",4),row("34222.5",4,1,ask=104),
          row("34222.5",5,1,ask=104),row("34223",2))
    b=bind_public_ns_source(rows,original_run_label=rid)
    w=NsEvaluationWindow(rid,t("34222"),t("34226"),b.projection.post_event_bbo_snapshots)
    return b,BoundNsEvaluation(rid,b.source_public_sha256,w)


class BoundVisibleOnlyTrainingFalsifiers(unittest.TestCase):
    def test_two_original_public_training_worlds_exact_regimes(self):
        a=train()
        m=a.model
        self.assertEqual((m.low_cluster_count,m.high_cluster_count),(3,2))
        self.assertEqual((m.low_exposure_ns,m.high_exposure_ns),(4*10**9,4*10**9))
        self.assertEqual((m.low_rate_per_second,m.high_rate_per_second),(.75,.5))
        self.assertEqual(a.safe_aggregate["training_visible_type4_execution_rows"],5)
        self.assertEqual(a.safe_aggregate["training_unique_type4_ns_timestamp_clusters"],5)
        self.assertEqual(a.safe_aggregate["structural_original_training_sources"],2)

    def test_type2_quote_change_is_not_trade_event_and_is_causally_lagged(self):
        a=train()
        self.assertEqual(a.model.low_cluster_count,3)
        self.assertEqual(a.model.high_cluster_count,2)
        self.assertEqual(a.model.training_weighted_median_relative_spread,2/101)

    def test_append_nonexecution_l2_book_state_no_extra_type4_count(self):
        rows=low_rows()+(row("34205.5",2,ask=104),)
        result=train([low(rows),high()])
        self.assertEqual((result.model.low_cluster_count,result.model.high_cluster_count),(3,2))

    def test_hidden_type5_does_not_become_visible_train_cluster(self):
        rows=low_rows()+(row("34205.5",5,ask=104),)
        result=train([low(rows),high()])
        self.assertEqual(result.safe_aggregate["training_hidden_type5_executions_not_modelled"],1)
        self.assertEqual(result.safe_aggregate["training_unique_type4_ns_timestamp_clusters"],5)

    def test_split_visible_type4_fill_same_time_not_double_counted(self):
        rows=list(low_rows())
        rows.insert(2,row("34202.5",4))
        result=train([low(rows),high()])
        self.assertEqual(result.safe_aggregate["training_visible_type4_execution_rows"],6)
        self.assertEqual(result.safe_aggregate["training_unique_type4_ns_timestamp_clusters"],5)
        self.assertEqual(result.model.low_cluster_count,3)

    def test_one_ns_new_visible_type4_is_distinct_and_train_rate_changes(self):
        rows=list(low_rows())
        rows.insert(4,row("34203.500000001",4,ask=104))
        result=train([low(rows),high()])
        self.assertEqual(result.safe_aggregate["training_unique_type4_ns_timestamp_clusters"],6)
        self.assertEqual((result.model.low_cluster_count,result.model.high_cluster_count),(4,2))

    def test_type4_outside_declared_training_window_not_clipped(self):
        rows=(row("34200"),row("34201.5",4))+low_rows()[1:]
        with self.assertRaisesRegex(Abstain,"VISIBLE_TRAINING_TRADE_OUTSIDE"):
            train([low(rows),high()])

    def test_incomplete_or_unmatched_training_window_id_rejected(self):
        for spec in (replace(low(),interval_complete=False),
                     replace(low(),unit="milliseconds"),
                     replace(low(),original_run_label="not-low-world"),
                     replace(low(),start_ns=t("34206"),end_ns=t("34202"))):
            with self.subTest(spec=spec.original_run_label),self.assertRaises(Abstain):
                train([spec,high()])

    def test_duplicate_same_original_run_id_or_source_replay_rejected(self):
        with self.assertRaises(Abstain):
            train([low(),low()])
        other=low(rid="different-run")
        with self.assertRaises(Abstain):
            train([low(),other])

    def test_missing_prior_post_event_book_is_abstention(self):
        with self.assertRaises(Abstain):
            train([low(low_rows()[1:]),high()])

    def test_invalid_oracle_field_rejected_before_fit(self):
        with self.assertRaises(Abstain):
            bind_public_ns_source([dict(low_rows()[0],agent_id=7)],original_run_label="private")

    def test_new_visible_train_model_can_score_disjoint_eval_public_source(self):
        result=train()
        b,e=eval_source()
        scored=score_bound_public_ns_source(b,result.model,e)
        self.assertEqual(scored["visible_type4_distinct_ns_clusters"],1)
        self.assertAlmostEqual(scored["integrated_intensity"],2.875,places=12)
        self.assertFalse(scored["real_market_fdr_known"])

    def test_training_source_reused_as_evaluation_abstains(self):
        result=train()
        b,e=eval_source(rid="low-world")
        with self.assertRaises(Abstain):
            score_bound_public_ns_source(b,result.model,e)

    def test_aggregate_does_not_expose_source_rows_or_claim_independence(self):
        out=train().safe_aggregate
        for key in ("timestamp_ns","source_public_sha256","order_id","agent_id","book_rows"):
            self.assertNotIn(key,out)
        self.assertFalse(out["raw_source_event_order_or_book_rows_exported"])
        self.assertFalse(out["source_globally_independent_verified"])
        self.assertFalse(out["real_market_fdr_known"])


if __name__=="__main__":
    unittest.main()
