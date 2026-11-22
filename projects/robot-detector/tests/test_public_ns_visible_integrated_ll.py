"""Frozen five-message visible type4 ns public-only integration negatives."""
from dataclasses import replace
from decimal import Decimal as D
import math
import unittest

from tools.public_intensity_rescaling import Abstain
from tools.public_lobster_ns_time import exact_decimal_to_ns,UNIT
from tools.public_ns_visible_exec_projector import project_public_ns_visible_executions
from tools.public_m1_v3_ns_l2 import (
    NsTrainingRun,NsEvaluationWindow,fit_ns_m1_v3_train_only,
)
from tools.public_ns_visible_integrated_ll import score_same_source_visible_exec_ns as score


def t(value): return exact_decimal_to_ns(D(str(value)))


def row(sec,typ=1,side=-1,ask=102):
    return {"timestamp_ns":t(sec),"event_type":typ,"resting_side":side,
            "bid_price":100,"ask_price":ask,"complete":True}


def project(rows):
    return project_public_ns_visible_executions(
        rows,source_time_unit=UNIT,source_precision_ns=1,interval_complete=True)


def original_five():
    return [row("34220",1),row("34222.5",4,-1),row("34222.5",4,1,104),
            row("34222.5",5,1,104),row("34223",2)]


def trained():
    return fit_ns_m1_v3_train_only([
        NsTrainingRun("low-world",t("34202"),t("34206"),
                      (t("34202.5"),t("34203.5"),t("34204.25")),
                      ({"timestamp_ns":t("34200"),"bid_price":100,"ask_price":102,"complete":True},
                       {"timestamp_ns":t("34203"),"bid_price":100,"ask_price":104,"complete":True})),
        NsTrainingRun("high-world",t("34212"),t("34216"),
                      (t("34212.5"),t("34214.25")),
                      ({"timestamp_ns":t("34210"),"bid_price":100,"ask_price":104,"complete":True},
                       {"timestamp_ns":t("34213"),"bid_price":100,"ask_price":102,"complete":True})),
    ])


def window(p):
    return NsEvaluationWindow("eval",t("34222"),t("34226"),p.post_event_bbo_snapshots)


class IntegratedSourceFreeBookAndTradeTests(unittest.TestCase):
    def test_exact_five_message_paired_source_mathematical_score(self):
        p=project(original_five())
        r=score(p,trained(),window(p))
        self.assertEqual((r["source_message_rows"],r["visible_type4_executions"],
                          r["visible_type4_distinct_ns_clusters"],
                          r["hidden_type5_executions_excluded"],
                          r["nonexecution_messages_excluded"]),(5,2,1,1,2))
        self.assertEqual(r["causal_bbo_exposure_segments"],3)
        self.assertAlmostEqual(r["integrated_intensity"],2.875,places=12)
        self.assertAlmostEqual(r["heldout_log_likelihood"],math.log(.75)-2.875,places=12)

    def test_one_ns_apart_trades_are_distinct_not_rounded_to_ms(self):
        p=project([row("34220"),row("34222.5",4),row("34222.500000001",4),
                   row("34223",2)])
        result=score(p,trained(),window(p))
        self.assertEqual(result["visible_type4_distinct_ns_clusters"],2)
        self.assertFalse(result["real_trade_only_ms_coarsening_rate_measured"])

    def test_hidden_type5_only_is_not_bot_absence(self):
        p=project([row("34220"),row("34222.5",5),row("34223",2)])
        r=score(p,trained(),window(p))
        self.assertEqual(r["visible_type4_distinct_ns_clusters"],0)
        self.assertEqual(r["hidden_type5_executions_excluded"],1)
        self.assertEqual(r["heldout_log_likelihood"],-3.)
        self.assertFalse(r["physical_owner_identity_known"])

    def test_mismatched_book_from_other_source_abstains(self):
        p=project(original_five())
        books=list(p.post_event_bbo_snapshots)
        books[-1]=dict(books[-1],ask_price=104)
        with self.assertRaisesRegex(Abstain,"SOURCE_MISMATCH"):
            score(p,trained(),replace(window(p),post_event_bbo=tuple(books)))

    def test_missing_initial_book_abstains(self):
        p=project(original_five()[1:])
        with self.assertRaises(Abstain):
            score(p,trained(),window(p))

    def test_train_eval_source_run_overlap_abstains(self):
        p=project(original_five())
        with self.assertRaises(Abstain):
            score(p,trained(),replace(window(p),run_id="low-world"))

    def test_out_of_window_visible_trade_rejected_not_clipped(self):
        p=project([row("34220",1),row("34221.5",4),row("34222.5",4),row("34223",2)])
        with self.assertRaisesRegex(Abstain,"VISIBLE_TRADE_OUTSIDE"):
            score(p,trained(),window(p))

    def test_unverified_source_continuity_is_abstention(self):
        with self.assertRaises(Abstain):
            project_public_ns_visible_executions(
                original_five(),source_time_unit=UNIT,
                source_precision_ns=1,interval_complete=False)
        p=project(original_five())
        with self.assertRaises(Abstain):
            score(p,trained(),replace(window(p),interval_complete=False))

    def test_forged_source_metadata_fails_closed(self):
        p=project(original_five())
        broken=replace(p,safe_aggregate={**p.safe_aggregate,
                                        "visible_type4_exact_trade_timestamp_clusters":9})
        with self.assertRaisesRegex(Abstain,"INCONSISTENT"):
            score(broken,trained(),window(p))
        claimed=replace(p,safe_aggregate={**p.safe_aggregate,
                                         "source_completeness_independently_verified":True})
        with self.assertRaises(Abstain):
            score(claimed,trained(),window(p))

    def test_same_public_tape_private_story_is_not_an_input(self):
        story1="unknown resting queue, periodic background"
        story2="invented controlled schedule"
        self.assertNotEqual(story1,story2)
        a=project(original_five())
        self.assertEqual(score(a,trained(),window(a)),score(project(original_five()),trained(),window(a)))

    def test_payload_aggregates_only_with_no_actor_or_raw_quotes(self):
        p=project(original_five())
        r=score(p,trained(),window(p))
        for field in ("timestamp_ns","bid_price","ask_price","agent_id","order_id","private_truth"):
            self.assertNotIn(field,r)
        self.assertFalse(r["vendor_raw_source_rows_exported"])
        self.assertFalse(r["real_market_fdr_known"])


if __name__=="__main__":
    unittest.main()
