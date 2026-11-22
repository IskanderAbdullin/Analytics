"""Source-only provenance structural identity, identical BBO counterexample."""
from dataclasses import replace
from decimal import Decimal as D
import math
import unittest

from tools.public_intensity_rescaling import Abstain
from tools.public_lobster_ns_time import exact_decimal_to_ns, UNIT
from tools.public_ns_visible_exec_projector import project_public_ns_visible_executions
from tools.public_ns_visible_integrated_ll import score_same_source_visible_exec_ns
from tools.public_m1_v3_ns_l2 import (
    NsTrainingRun,NsEvaluationWindow,fit_ns_m1_v3_train_only,
)
from tools.public_ns_source_binding import (
    BoundPublicNsSource,BoundNsEvaluation,bind_public_ns_source,
    score_bound_public_ns_source,audit_structural_unique_bound_sources,
)


def t(s):return exact_decimal_to_ns(D(str(s)))


def row(sec,typ=1,side=-1,ask=102,**extra):
    return dict(timestamp_ns=t(sec),event_type=typ,resting_side=side,
                bid_price=100,ask_price=ask,complete=True,**extra)


def a_rows():
    return (row("34220"),row("34222.5",4),row("34222.5",4,1,104),
            row("34222.5",5,1,104),row("34223",2))


def b_rows_same_books_different_type4():
    r=list(a_rows())
    r[2]=dict(r[2],event_type=2)
    return tuple(r)


def model():
    low=NsTrainingRun("low-world",t("34202"),t("34206"),
                      (t("34202.5"),t("34203.5"),t("34204.25")),
                      ({"timestamp_ns":t("34200"),"bid_price":100,"ask_price":102,"complete":True},
                       {"timestamp_ns":t("34203"),"bid_price":100,"ask_price":104,"complete":True}))
    high=NsTrainingRun("high-world",t("34212"),t("34216"),
                       (t("34212.5"),t("34214.25")),
                       ({"timestamp_ns":t("34210"),"bid_price":100,"ask_price":104,"complete":True},
                        {"timestamp_ns":t("34213"),"bid_price":100,"ask_price":102,"complete":True}))
    return fit_ns_m1_v3_train_only([low,high])


def source(rows=None,rid="eval-A"):
    return bind_public_ns_source(a_rows() if rows is None else rows,original_run_label=rid)


def bound(source):
    return BoundNsEvaluation(source.original_run_label,source.source_public_sha256,
                             NsEvaluationWindow(source.original_run_label,t("34222"),t("34226"),
                                                source.projection.post_event_bbo_snapshots))


class PublicNsStructuralSourceBindingTests(unittest.TestCase):
    def test_same_books_but_different_public_event_types_negative(self):
        a=source()
        b=source(b_rows_same_books_different_type4(),rid="eval-B")
        self.assertEqual(a.projection.post_event_bbo_snapshots,
                         b.projection.post_event_bbo_snapshots)
        self.assertNotEqual(a.projection.safe_aggregate["visible_type4_executions"],
                            b.projection.safe_aggregate["visible_type4_executions"])
        self.assertNotEqual(a.source_public_sha256,b.source_public_sha256)
        # Earlier book-only gate permitted this ambiguous source-pair because
        # BBO snapshots match. That is a structural provenance LIMIT, not FDR.
        accepted=score_same_source_visible_exec_ns(b.projection,model(),
                                                   bound(a).evaluation_window)
        self.assertEqual(accepted["visible_type4_executions"],1)

    def test_valid_bound_source_matches_fixed_complete_ll(self):
        a=source()
        r=score_bound_public_ns_source(a,model(),bound(a))
        self.assertEqual(r["visible_type4_executions"],2)
        self.assertAlmostEqual(r["integrated_intensity"],2.875,places=12)
        self.assertAlmostEqual(r["heldout_log_likelihood"],math.log(.75)-2.875,places=12)
        self.assertFalse(r["source_globally_independent_verified"])

    def test_other_source_digest_mismatch_rejected_even_with_identical_books(self):
        a=source()
        b=source(b_rows_same_books_different_type4(),rid="eval-B")
        wrong=BoundNsEvaluation(b.original_run_label,a.source_public_sha256,
                                bound(b).evaluation_window)
        with self.assertRaisesRegex(Abstain,"DIGEST_MISMATCH"):
            score_bound_public_ns_source(b,model(),wrong)

    def test_other_original_run_id_mismatch_rejected(self):
        a=source()
        forged=replace(bound(a),original_run_label="eval-B")
        with self.assertRaises(Abstain):
            score_bound_public_ns_source(a,model(),forged)
        forged=replace(bound(a),evaluation_window=replace(bound(a).evaluation_window,run_id="eval-B"))
        with self.assertRaises(Abstain):
            score_bound_public_ns_source(a,model(),forged)

    def test_repeat_same_source_id_different_event_tape_is_rejected(self):
        a=source()
        b=source(b_rows_same_books_different_type4())
        with self.assertRaisesRegex(Abstain,"DEPENDENT_REPLAY"):
            audit_structural_unique_bound_sources((a,b))

    def test_repeat_exact_public_tape_under_different_id_is_rejected(self):
        a=source()
        replay=source(rid="different-run-label")
        with self.assertRaisesRegex(Abstain,"DEPENDENT_REPLAY"):
            audit_structural_unique_bound_sources((a,replay))

    def test_distinct_tapes_and_ids_structurally_allowed_not_proof(self):
        a=source()
        b=source(b_rows_same_books_different_type4(),rid="eval-B")
        result=audit_structural_unique_bound_sources((a,b))
        self.assertEqual(result["source_labels"],2)
        self.assertFalse(result["globally_independent_source_worlds_verified"])

    def test_source_fingerprint_deterministic_and_sensitive_to_one_ns(self):
        a=source()
        again=source()
        self.assertEqual(a.source_public_sha256,again.source_public_sha256)
        shifted=list(a_rows())
        shifted[1]=dict(shifted[1],timestamp_ns=shifted[1]["timestamp_ns"]+1)
        b=source(shifted,rid="eval-B")
        self.assertNotEqual(a.source_public_sha256,b.source_public_sha256)

    def test_public_projection_mutation_after_binding_fails_closed(self):
        a=source()
        p=replace(a.projection,safe_aggregate={**a.projection.safe_aggregate,
                                               "visible_type4_executions":555})
        tampered=replace(a,projection=p)
        with self.assertRaisesRegex(Abstain,"MUTATED"):
            score_bound_public_ns_source(tampered,model(),bound(a))

    def test_train_eval_original_run_overlap_still_rejected(self):
        a=source(rid="low-world")
        with self.assertRaises(Abstain):
            score_bound_public_ns_source(a,model(),bound(a))

    def test_invalid_original_source_label_or_oracle_fields_abstain(self):
        for label in ("secret account", "", "id/123", None,True):
            with self.subTest(label=repr(label)),self.assertRaises(Abstain):
                source(rid=label)
        with self.assertRaises(Abstain):
            source([dict(a_rows()[0],private_truth=True)])

    def test_only_aggregates_public_no_source_hash_or_raw_rows(self):
        a=source()
        r=score_bound_public_ns_source(a,model(),bound(a))
        for forbidden in ("source_public_sha256","post_event_bbo_snapshots",
                          "order_id","agent_id","timestamp_ns","bid_price"):
            self.assertNotIn(forbidden,r)
        self.assertFalse(r["physical_owner_identity_known"])
        self.assertFalse(r["real_market_fdr_known"])


if __name__=="__main__":
    unittest.main()
