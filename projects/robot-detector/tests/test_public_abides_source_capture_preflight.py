"""Predeclared source-free ABIDES original capture-profile NO-GO tests."""
from copy import deepcopy
import unittest

from tools.public_intensity_rescaling import Abstain
from tools.public_abides_epoch_ns_clock import PINNED_REVISION,SOURCE_UNIT
from tools.public_abides_source_capture_preflight import (
    PROFILE_FIELDS,ATTESTATION_FIELDS,
    audit_abides_source_capture_profile_preflight as audit,
)
from tools.public_abides_compact_160_eligibility import FIXTURE
import json


def profile(status="UNKNOWN"):
    x={
        "original_source_run_label":"fake-abides-original-no-seed",
        "source_family":"ABIDES_SIMULATOR",
        "pinned_revision":PINNED_REVISION,
        "configured_simulation_date":"20210205",
        "simulator_clock_unit":SOURCE_UNIT,
        "configured_start_HHMMSS":"09:30:00",
        "configured_end_HHMMSS":"09:38:00",
        "requested_result_profiles":["TRADE_ATTRIBUTION","L2_SERIES"],
        "public_l2_capture_mode":"sparse_l2",
        "requested_l2_depth_per_side":5,
        "original_source_role":"train",
    }
    x.update({k:status for k in ATTESTATION_FIELDS})
    return x


class ABIDESOriginalPublicCapturePreflightNegatives(unittest.TestCase):
    def test_unknown_4_external_evidence_still_blocks_original_source(self):
        r=audit(profile())
        self.assertTrue(r["metadata_profile_structurally_valid"])
        self.assertEqual(len(r["missing_or_failed_external_attestation_fields"]),4)
        self.assertFalse(r["original_source_experiment_authorized"])
        self.assertFalse(r["original_independent_source_study_ready"])
        self.assertEqual(r["original_simulator_runs_created"],0)

    def test_even_all_documented_does_not_grant_execution(self):
        r=audit(profile("EXTERNALLY_DOCUMENTED"))
        self.assertEqual(r["external_attestation_claim_count"],4)
        self.assertFalse(r["configured_UTC_day_externally_authenticated"])
        self.assertFalse(r["original_world_provenance_externally_verified_by_this_checker"])
        self.assertFalse(r["original_source_experiment_authorized"])

    def test_failed_external_evidence_not_disappeared(self):
        x=profile("EXTERNALLY_DOCUMENTED")
        x["source_coverage_attestation"]="FAILED"
        a=audit(x)
        self.assertEqual(a["explicitly_failed_external_attestation_fields"],("source_coverage_attestation",))
        self.assertFalse(a["sample_size_and_power_verified"])

    def test_both_public_attribution_and_l2_required_without_agent_logs(self):
        for val in (["L2_SERIES"],["TRADE_ATTRIBUTION"],[],
                    ["L2_SERIES","AGENT_LOGS"],
                    ["L2_SERIES","TRADE_ATTRIBUTION","AGENT_LOGS"],
                    [True,"TRADE_ATTRIBUTION"]):
            x=profile();x["requested_result_profiles"]=val
            with self.subTest(val=val),self.assertRaises(Abstain):
                audit(x)

    def test_wrong_family_unit_pinned_source_revision_rejected(self):
        for key,val in (("source_family","LOBSTER_VISIBLE_TYPE4"),
                        ("pinned_revision","latest"),
                        ("simulator_clock_unit","nanoseconds_since_exchange_local_midnight"),
                        ("simulator_clock_unit","unix_epoch_microseconds")):
            x=profile();x[key]=val
            with self.subTest(key=key),self.assertRaises(Abstain):
                audit(x)

    def test_private_agent_vendor_order_and_raw_source_rows_not_allowed(self):
        for extra in ("agent_id","source_order_id","private_oracle","trades","raw_source_event_rows"):
            x=profile();x[extra]=[1]
            with self.subTest(extra=extra),self.assertRaises(Abstain):
                audit(x)

    def test_strict_calendar_and_explicit_source_session(self):
        for key,value in (("configured_simulation_date",None),
                          ("configured_simulation_date","20210229"),
                          ("configured_simulation_date","2021-02-05"),
                          ("configured_simulation_date","19690101"),
                          ("configured_start_HHMMSS","10:00:00"),
                          ("configured_end_HHMMSS","16:00:00")):
            x=profile();x[key]=value
            with self.subTest(key=key),self.assertRaises(Abstain):
                audit(x)

    def test_exact_integer_depth_sparse_l2_and_source_role(self):
        for key,value in (("public_l2_capture_mode","off"),
                          ("public_l2_capture_mode","l1"),
                          ("requested_l2_depth_per_side",True),
                          ("requested_l2_depth_per_side",10),
                          ("original_source_role","all"),
                          ("original_source_role",None)):
            x=profile();x[key]=value
            with self.subTest(key=key),self.assertRaises(Abstain):
                audit(x)

    def test_boolean_evidence_cannot_promote_source_execution(self):
        for val in (True,False,"VERIFIED",None,1,"AUTHORISED"):
            x=profile();x["external_license_rights_attestation"]=val
            with self.subTest(v=val),self.assertRaises(Abstain):
                audit(x)

    def test_previous_compact_genuine_160_metadata_is_not_original_profile(self):
        x=json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertNotEqual(set(x),PROFILE_FIELDS)
        with self.assertRaises(Abstain):
            audit(x)

    def test_safe_result_does_not_emit_date_raw_or_agent_id(self):
        r=audit(profile())
        for forbidden in ("original_source_run_label","configured_simulation_date",
                          "agent_id","order_id","original_source_raw",
                          "source_artifact_checksum","private_truth"):
            self.assertNotIn(forbidden,r)
        self.assertFalse(r["real_market_fdr_known"])
        self.assertFalse(r["physical_owner_identity_known"])
        self.assertFalse(r["raw_source_event_or_private_ids_exported"])


if __name__=="__main__":
    unittest.main()
