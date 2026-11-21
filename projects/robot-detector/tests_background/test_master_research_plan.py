"""Regression checks for the living scientific plan and agent adaptation contract.

A plan is NOT evidence of executing any proposed experiment. These
tests protect against losing the master goal, negative results, dynamic
checkpoint, evidence links or the ability to change the roadmap.
"""
from pathlib import Path
import json
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/"docs"/"MASTER_RESEARCH_PLAN.md"
AGENT=ROOT/"AGENTS.md"
CHECKPOINT=ROOT/"research"/"autonomy_state.json"
REQUIRED_REPORTS=(
    "BCH_FOUR_DAY_OCCUPANCY_PANEL_20261121.md",
    "LOBSTER_AMZN_PUBLIC_SAMPLE_FORMAT_AUDIT_20261121.md",
    "LOBSTER_EVENT_TIME_FEATURES_20261121.md",
    "LOBSTER_CLOCK_VS_EVENT_WEIGHTING_20261121.md",
    "SYNTHETIC_L2_OWNER_NONIDENTIFIABILITY_20261121.md",
    "EXCHANGE_L2_COVERAGE_ABSTENTION_20261121.md",
    "OFFLINE_REPRODUCIBILITY_20261121.md",
    "TOY_PUBLIC_EXECUTION_RHYTHM_HARD_NEGATIVE_20261121.md",
    "GENUINE_ABIDES_FIXED_CLOCK_TRANSFER_20261121.md",
)


class LivingResearchPlanContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=PLAN.read_text(encoding="utf-8")
        cls.agent=AGENT.read_text(encoding="utf-8")
        cls.state=json.loads(CHECKPOINT.read_text(encoding="utf-8"))

    def test_agent_must_read_and_update_living_master_plan(self):
        self.assertIn("docs/MASTER_RESEARCH_PLAN.md",self.agent)
        self.assertIn("автоном",self.agent.lower())
        self.assertIn("самостоятельно",self.agent.lower())
        self.assertIn("план",self.agent.lower())
        self.assertIn("отрицатель",self.agent.lower())
        self.assertIn("commit",self.agent.lower())
        self.assertIn("checkpoint",self.agent.lower())
        self.assertIn("без force",self.agent.lower())
        self.assertIn("научн",self.agent.lower())
        self.assertIn("не переписывать",self.agent.lower())
        self.assertIn("decision",self.agent.lower())

    def test_stage_checkpoint_is_grounded_in_live_plan_not_stale_readme(self):
        self.assertEqual(self.state["master_research_plan"],
                         "docs/MASTER_RESEARCH_PLAN.md")
        stage=self.state["current_stage"]
        self.assertRegex(stage["id"],r"^RD-[A-Z0-9-]+$")
        self.assertIn(stage["id"],self.plan)
        self.assertIn(self.state["master_issue"],self.plan)
        self.assertIn("ACTIVE_RESEARCH_NOT_RELEASED",self.state["status"])
        self.assertIn("MASTER_RESEARCH_PLAN.md",(ROOT/"README.md").read_text(encoding="utf-8"))

    def test_verified_research_and_hard_negative_are_not_erased(self):
        for name in REQUIRED_REPORTS:
            with self.subTest(document=name):
                self.assertTrue((ROOT/"docs"/name).is_file(),name)
                self.assertIn(name,self.plan)
        for finding in (
            "776 007","269 748","1 против 3",
            "2/2 ложных", "2/2 пропущены","29",
            "113 тестов", "ABIDES-NG"
        ):
            self.assertIn(finding,self.plan)
        self.assertIn("отрицательные",self.plan.lower())

    def test_governed_adaptation_and_reality_gates_are_preserved(self):
        for clause in (
            "Как самостоятельно пересматривать",
            "Триггеры пересмотра",
            "Протокол законного пересмотра",
            "freeze", "GitHub Actions",
            "checkpoint", "force", "owner",
            "UNKNOWN", "ABSTAIN",
            "MASTER_RESEARCH_PLAN.md",
            "Итоговый независимый release gate",
            "Журнал решений",
            "Не публиковать vendor",
            "2901/2902/2903"
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause.lower(),self.plan.lower())
        self.assertRegex(self.plan,r"\[ \] .+")
        self.assertIn("зарезервированные в локальном seed registry",self.plan.lower())
        self.assertIn("исходные прогоны для него ещё не подтверждены",self.plan)

    def test_evidence_not_reported_as_true_physical_owner_detection(self):
        self.assertIn("real-market",self.plan)
        self.assertIn("false",self.plan.lower())
        self.assertIn("приватной oracle",self.plan)
        self.assertIn("неидентифицируем",self.plan.lower())
        self.assertIn("real-market FDR",self.plan)


if __name__=="__main__":
    unittest.main(verbosity=2)
