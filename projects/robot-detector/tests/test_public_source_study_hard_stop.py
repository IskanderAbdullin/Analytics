"""Fixed source-free planning hard stops; no genuine source workflows."""
import unittest
from tools.public_intensity_rescaling import Abstain
from tools.public_source_study_hard_stop import (
    EVIDENCE_FIELDS, SOURCE_FAMILIES, source_study_planning_hard_stop,
    current_project_ns_study_no_go,
)


def manifest(source="ABIDES_SIMULATOR",phase="INDEPENDENT_SOURCE_STUDY",state="UNKNOWN"):
    return {"source_family":source,"study_phase":phase,
            "evidence":{k:state for k in EVIDENCE_FIELDS}}


class SourceFreeOriginalSourceNoGoTests(unittest.TestCase):
    def test_default_current_project_study_is_blocked_and_never_authorized(self):
        a=current_project_ns_study_no_go()
        self.assertEqual(a["status"],"BLOCKED_EVIDENCE")
        self.assertEqual(a["execution_authorization"],"NOT_AUTHORIZED_FOR_SOURCE_EXECUTION")
        self.assertEqual(len(a["missing_or_failed_evidence_fields"]),9)
        self.assertEqual(a["original_source_worlds_generated"],0)
        self.assertFalse(a["provider_data_rights_granted_by_tool"])

    def test_any_one_failed_external_dimension_stops_evaluation(self):
        m=manifest(state="DOCUMENTED_EXTERNAL")
        m["evidence"]["exchange_event_completeness"]="FAILED"
        a=source_study_planning_hard_stop(m)
        self.assertEqual(a["status"],"BLOCKED_EVIDENCE")
        self.assertEqual(a["explicitly_failed_evidence_fields"],("exchange_event_completeness",))
        self.assertFalse(a["real_market_fdr_known"])

    def test_all_documented_is_still_not_execution_permission(self):
        a=source_study_planning_hard_stop(manifest(state="DOCUMENTED_EXTERNAL"))
        self.assertEqual(a["status"],"STRUCTURAL_EVIDENCE_DOCUMENTED_EXTERNAL_REVIEW_STILL_REQUIRED")
        self.assertEqual(a["execution_authorization"],"NOT_AUTHORIZED_FOR_SOURCE_EXECUTION")
        self.assertFalse(a["all_documentation_claims_source_authenticated_by_tool"])
        self.assertFalse(a["physical_owner_identity_known"])

    def test_coinbase_and_other_source_rights_block_even_when_claimed(self):
        for source in ("COINBASE_MARKET_DATA","MOEX_ISS_HISTORY","LOBSTER_PUBLIC_DEMO",
                       "BINANCE_TRADE_ONLY"):
            with self.subTest(source=source):
                a=source_study_planning_hard_stop(manifest(source=source,state="DOCUMENTED_EXTERNAL"))
                self.assertEqual(a["status"],"BLOCKED_EVIDENCE")
                self.assertIsNotNone(a["source_or_release_specific_blocker"])

    def test_real_market_release_never_authorized_even_from_abides(self):
        for family in SOURCE_FAMILIES:
            with self.subTest(family=family):
                a=source_study_planning_hard_stop(manifest(source=family,
                           phase="REAL_MARKET_RELEASE",state="DOCUMENTED_EXTERNAL"))
                self.assertEqual(a["status"],"BLOCKED_EVIDENCE")
                self.assertFalse(a["real_market_fdr_known"])
                self.assertIn("NO_INDEPENDENT",a["source_or_release_specific_blocker"])

    def test_strict_types_no_private_oracle_source_metadata(self):
        for bad in (
            dict(manifest(),agent_id=1),
            {**manifest(),"evidence":{**manifest()["evidence"],"order_id":"123"}},
            {**manifest(),"source_family":"some_vendor"},
            {**manifest(),"study_phase":"LIVE_TRADE"},
        ):
            with self.subTest(bad=str(bad)[:55]), self.assertRaises(Abstain):
                source_study_planning_hard_stop(bad)

    def test_invalid_or_boolean_status_cannot_grant_permission(self):
        for status in (True,False,None,1,"AUTHORIZED","passed","YES"):
            m=manifest()
            m["evidence"]["provider_research_rights"]=status
            with self.subTest(status=repr(status)),self.assertRaises(Abstain):
                source_study_planning_hard_stop(m)

    def test_all_nine_evidence_values_preserved_not_short_circuited(self):
        m=manifest()
        m["evidence"]["unit_safe_source_clock"]="FAILED"
        m["evidence"]["provider_research_rights"]="DOCUMENTED_EXTERNAL"
        r=source_study_planning_hard_stop(m)
        self.assertEqual(r["prerequisite_count"],9)
        self.assertEqual(r["externally_documented_claim_count"],1)
        self.assertEqual(len(r["missing_or_failed_evidence_fields"]),8)
        self.assertEqual(r["explicitly_failed_evidence_fields"],("unit_safe_source_clock",))
        self.assertNotIn("agent_id",r)
        self.assertNotIn("order_id",r)


if __name__=="__main__":
    unittest.main()
