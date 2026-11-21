"""Negative tests for the permanent autonomous research handoff contract."""
import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from autonomy_checkpoint import (
    ROOT, STATE, TZ, load_checkpoint, validate_state, unique_object
)

class AutonomyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=load_checkpoint(STATE)

    def test_actual_checked_in_project_has_resume_evidence_and_next_action(self):
        result=validate_state(self.source)
        self.assertEqual(result["current_stage_id"],"RD-L2-RESEARCH-01")
        self.assertEqual(result["status"],"ACTIVE_RESEARCH_NOT_RELEASED")
        self.assertTrue(result["can_resume_from_checkpoint"])
        self.assertFalse(result["scientific_final_goal_already_verified"])
        self.assertFalse(result["is_background_daemon_running"])
        self.assertGreaterEqual(result["available_queued_followups"],3)
        self.assertIn("issues/72",result["master_issue"])
        self.assertTrue(TZ.is_file())
        self.assertIn("автоном",TZ.read_text(encoding="utf-8").lower())

    def test_guardrails_cannot_be_silently_removed(self):
        guard=list(self.source["operational_constraints"].keys())
        self.assertGreaterEqual(len(guard),8)
        for key in guard:
            broken=copy.deepcopy(self.source)
            broken["operational_constraints"][key]=False
            with self.subTest(guard=key),self.assertRaises(ValueError):
                validate_state(broken)

    def test_project_identity_and_sha_must_match(self):
        for key,value in (
            ("repository","another/repo"),
            ("branch","main"),
            ("master_issue",""),
            ("schema_version","future-unknown"),
            ("last_verified_base_commit","unknown"),
            ("research_contract","some-other-doc.md"),
            ("status","ALREADY_DONE"),
        ):
            broken=copy.deepcopy(self.source)
            broken[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_state(broken)

    def test_must_have_actionable_stage_and_real_more_to_do(self):
        mutations=(
            ("current_stage","status","UNKNOWN"),
            ("current_stage","title",""),
            ("current_stage","deliverables",[]),
            ("current_stage","acceptance",[]),
        )
        for area,key,value in mutations:
            broken=copy.deepcopy(self.source)
            broken[area][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_state(broken)
        broken=copy.deepcopy(self.source)
        broken["backlog"].append(copy.deepcopy(broken["backlog"][0]))
        with self.assertRaises(ValueError):
            validate_state(broken)
        broken=copy.deepcopy(self.source)
        broken["backlog"]=[]
        with self.assertRaises(ValueError):
            validate_state(broken)

    def test_no_fabricated_evidence_or_unexplained_blocker(self):
        bad=copy.deepcopy(self.source)
        bad["last_known_verified_results"][0]["evidence_url"]="none"
        with self.assertRaises(ValueError):
            validate_state(bad)
        bad=copy.deepcopy(self.source)
        bad["blockers"][0]["safe_workaround"]=""
        with self.assertRaises(ValueError):
            validate_state(bad)
        bad=copy.deepcopy(self.source)
        bad["resume_instruction"]=""
        with self.assertRaises(ValueError):
            validate_state(bad)

    def test_duplicate_checkpoint_fields_must_fail(self):
        with self.assertRaises(ValueError):
            unique_object([("status","ACTIVE"),("status","ALREADY_DONE")])

if __name__ == "__main__":
    unittest.main(verbosity=2)
