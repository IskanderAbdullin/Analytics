"""Public ABIDES trade marks are deliberately excluded from timing-only LL."""
import unittest
from tools.public_intensity_rescaling import Abstain
from tools.public_abides_m1v4_nontarget_panel import _ns,_frozen_train
from tools.public_abides_sparse_l2_screen import screen_abides_public_execution_sparse_l2 as screen
from tools.public_abides_full_window_exposure import qualify_abides_full_window_l2_exposure
from tools.public_abides_m0_m1v4_ll import (
    ABIDESPublicOriginalCase,_source_fingerprint,
    evaluate_abides_public_fixed_m0_m1v4 as score,
)


def public_marked_source(aggressor_side,price,qty):
    row={"epoch_ns":_ns("34222.5"),"price_cents":price,
         "quantity":qty,"aggressor_side":aggressor_side}
    return screen((dict(row),dict(row)),
                  (
                   {"epoch_ns":_ns("34220"),"bid_cents":100,"ask_cents":102,"depth_complete":True},
                   {"epoch_ns":_ns("34222.5"),"bid_cents":100,"ask_cents":104,"depth_complete":True},
                   {"epoch_ns":_ns("34223"),"bid_cents":100,"ask_cents":102,"depth_complete":True},
                  ),
                  source_run_id="synthetic-mark-projection",
                  simulation_date="20210205",
                  window_start_ns=34222*1000000000,
                  window_end_ns=34226*1000000000)


def orig(screened):
    exposure=qualify_abides_full_window_l2_exposure(
        screened,start_ns=34222*1000000000,end_ns=34226*1000000000)
    return ABIDESPublicOriginalCase(
        "synthetic-mark-projection",34222*1000000000,
        34226*1000000000,screened,exposure)


class ABIDESPublicMarkFeatureProjectionLimits(unittest.TestCase):
    def test_different_observed_trade_marks_same_timing_feature_fingerprint_LL(self):
        a=orig(public_marked_source("BUY",101,1))
        b=orig(public_marked_source("SELL",103,9))
        self.assertEqual(a.public_execution_quote_screen,b.public_execution_quote_screen)
        self.assertEqual(_source_fingerprint(a),_source_fingerprint(b))
        self.assertEqual(score(_frozen_train(),a),score(_frozen_train(),b))
        self.assertFalse(score(_frozen_train(),a)["physical_owner_identity_known"])

    def test_private_actor_field_rejected_before_lossy_public_projection(self):
        bad={"epoch_ns":_ns("34222.5"),"price_cents":101,
             "quantity":1,"aggressor_side":"BUY","passive_agent_id":999}
        with self.assertRaisesRegex(Abstain,"PRIVATE_OR_MISSING"):
            screen((bad,),
                   ({"epoch_ns":_ns("34220"),"bid_cents":100,
                     "ask_cents":102,"depth_complete":True},),
                   source_run_id="source-free-private-forbidden",
                   simulation_date="20210205",window_start_ns=34222*1000000000,
                   window_end_ns=34226*1000000000)


if __name__=="__main__":
    unittest.main()
