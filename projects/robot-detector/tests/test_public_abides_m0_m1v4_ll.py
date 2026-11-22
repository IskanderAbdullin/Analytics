"""Precommitted source-free ABIDES M0/M1-v4 comparison with adverse LL."""
from dataclasses import replace
from datetime import date
from math import log
import unittest

from tools.public_intensity_rescaling import Abstain
from tools.public_abides_epoch_ns_clock import NS,ORIGIN,UNIT
from tools.public_abides_sparse_l2_screen import screen_abides_public_execution_sparse_l2 as screen
from tools.public_abides_full_window_exposure import qualify_abides_full_window_l2_exposure as expose
from tools.public_abides_m0_m1v4_ll import (
    ABIDESPublicOriginalCase,fit_abides_public_m0_m1v4_train_only as fit,
    evaluate_abides_public_fixed_m0_m1v4 as evaluate,
)

BASE=(date(2021,2,5)-ORIGIN).days*86400*NS

def tick(t):return BASE+int(t*NS)

def trade(t):
    return {"epoch_ns":tick(t),"price_cents":101,"quantity":1,"aggressor_side":"BUY"}

def book(t,ask=102):
    return {"epoch_ns":tick(t),"bid_cents":100,"ask_cents":ask,"depth_complete":True}

def build(label,start,end,trades,books):
    x=screen(trades,books,source_run_id=label,simulation_date="20210205",
             window_start_ns=int(start*NS),window_end_ns=int(end*NS))
    y=expose(x,start_ns=int(start*NS),end_ns=int(end*NS))
    return ABIDESPublicOriginalCase(label,int(start*NS),int(end*NS),x,y)

def low():
    return build("toy-abides-low",34202,34206,
                 (trade(34202.5),trade(34203.5),trade(34204.25)),
                 (book(34200),book(34203,104)))

def high():
    return build("toy-abides-high",34212,34216,
                 (trade(34212.5),trade(34214.25)),
                 (book(34210,104),book(34213)))

def ev(rows=None):
    return build("toy-abides-eval",34222,34226,
                 (trade(34222.5),trade(34222.5)) if rows is None else rows,
                 (book(34220),book(34222.5,104),book(34223)))


class ABIDESM0M1V4NegativeSourceFreeTests(unittest.TestCase):
    def test_precommitted_train_regimes_rates_and_median(self):
        m=fit((low(),high()))
        self.assertEqual(m.unit,UNIT)
        self.assertEqual((m.train_low_unique_clusters,m.train_high_unique_clusters),(3,2))
        self.assertEqual((m.train_low_exposure_ns,m.train_high_exposure_ns),(4*NS,4*NS))
        self.assertEqual((m.m0_rate_per_second,m.m1_low_rate_per_second,m.m1_high_rate_per_second),
                         (.625,.75,.5))
        self.assertEqual((m.median_spread_numerator,m.median_spread_denominator),(1,101))

    def test_negative_frozen_heldout_m1_worse_than_m0(self):
        r=evaluate(fit((low(),high())),ev())
        self.assertEqual(r["heldout_unique_exact_ns_exec_clusters"],1)
        self.assertEqual((r["m0_full_window_integral"],r["m1_full_window_integral"]),(2.5,2.875))
        self.assertAlmostEqual(r["m0_full_window_LL"],log(.625)-2.5,places=12)
        self.assertAlmostEqual(r["m1_full_window_LL"],log(.75)-2.875,places=12)
        self.assertAlmostEqual(r["m1_minus_m0_LL"],-0.1926784432060451,places=12)
        self.assertLess(r["m1_minus_m0_LL"],0)
        self.assertFalse(r["real_market_fdr_known"])

    def test_same_ns_split_fills_do_not_create_independent_clusters(self):
        a=evaluate(fit((low(),high())),ev())
        b=evaluate(fit((low(),high())),ev((trade(34222.5),trade(34222.5),trade(34222.5))))
        self.assertEqual(a,b)

    def test_one_ns_extra_exec_is_not_silently_rounded(self):
        originals=list((trade(34222.5),trade(34222.5)))
        later=dict(originals[1],epoch_ns=originals[1]["epoch_ns"]+1)
        result=evaluate(fit((low(),high())),ev((originals[0],later)))
        assert result["heldout_unique_exact_ns_exec_clusters"]==2
        self.assertAlmostEqual(result["m1_full_window_LL"]-
                               evaluate(fit((low(),high())),ev())["m1_full_window_LL"],
                               log(.75),places=12)

    def test_training_same_original_label_or_public_replay_rejected(self):
        with self.assertRaises(Abstain):
            fit((low(),low()))
        alias=replace(low(),source_run_label="different-id")
        with self.assertRaises(Abstain):
            fit((low(),alias))

    def test_training_replay_under_evaluation_alias_rejected(self):
        m=fit((low(),high()))
        alias=replace(low(),source_run_label="eval-new-id")
        with self.assertRaises(Abstain):
            evaluate(m,alias)

    def test_training_original_run_id_used_as_eval_rejected(self):
        m=fit((low(),high()))
        e=replace(ev(),source_run_label="toy-abides-low")
        with self.assertRaises(Abstain):
            evaluate(m,e)

    def test_inconsistent_public_exposure_payload_abstains(self):
        e=ev()
        truncated=replace(e,full_window_exposure=replace(
            e.full_window_exposure,segments=e.full_window_exposure.segments[:-1]))
        with self.assertRaises(Abstain):
            evaluate(fit((low(),high())),truncated)

    def test_single_spread_training_stratum_is_not_a_two_rate_model(self):
        all_low=build("all-low",34202,34206,
                      (trade(34202.5),trade(34203.5)),
                      (book(34200),book(34203)))
        with self.assertRaises(Abstain):
            fit((all_low,))

    def test_wrong_source_clock_or_model_unit_is_never_cast(self):
        m=fit((low(),high()))
        with self.assertRaises(Abstain):
            evaluate(replace(m,unit="nanoseconds_since_exchange_local_midnight"),ev())
        with self.assertRaises(Abstain):
            evaluate(m,replace(ev(),start_ns=True))

    def test_noncausal_sparse_quote_exposure_fail_closed(self):
        with self.assertRaises(Abstain):
            build("stale",34222,34232,(trade(34222.5),),(book(34220),))

    def test_no_private_owner_or_fdr_statistics_leaked(self):
        a=evaluate(fit((low(),high())),ev())
        for key in ("agent_id","passive_agent_id","source_sha256","order_id",
                    "original_source_rows","timestamp_ns","private_oracle"):
            self.assertNotIn(key,a)
        self.assertFalse(a["independent_original_source_worlds_verified"])
        self.assertFalse(a["source_event_and_book_completeness_verified"])
        self.assertFalse(a["real_trades_or_order_placement_enabled"])


if __name__=="__main__":
    unittest.main()
