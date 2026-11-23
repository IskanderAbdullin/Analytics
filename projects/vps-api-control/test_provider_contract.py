"""Offline contract tests: never reach Serverspace or control VPS power."""
import unittest
from provider_contract import (ContractError, plan_sole_server_power,
                               sole_server, task_status, validate_task_id)

S=[{"id":"l9s1367628","is_power_on":True,"name":"PRIVATE","password":"SECRET"}]
class TestProviderContract(unittest.TestCase):
    def test_only_one_well_formed_target(self):
        for inventory in ([],S+S,[{"id":"../../x","is_power_on":True}],
                          [{"id":"l9s1","is_power_on":None}]):
            with self.assertRaises(ContractError):
                sole_server(inventory)
    def test_readonly_planning_cannot_execute_or_disclose(self):
        p=plan_sole_server_power("reboot",S)
        self.assertEqual(p.method,"POST")
        self.assertEqual(p.endpoint,"/api/v1/servers/l9s1367628/power/reboot")
        self.assertEqual(p.public_summary(),{"decision":"ready","action":"reboot"})
        self.assertNotIn("1367628",str(p.public_summary()))
        self.assertNotIn("PRIVATE",str(p.public_summary()))
    def test_hard_power_closed_unless_flag(self):
        for action in ("off","reset"):
            with self.assertRaisesRegex(ContractError,"HARD_POWER_NOT_AUTHORIZED"):
                plan_sole_server_power(action,S)
        self.assertEqual(plan_sole_server_power("off",S,force_allowed=True).decision,"ready")
    def test_state_aware_idempotence(self):
        self.assertEqual(plan_sole_server_power("on",S).decision,"no_change")
        down=[{"id":"l9s1367628","is_power_on":False}]
        self.assertEqual(plan_sole_server_power("shutdown",down).decision,"no_change")
        with self.assertRaisesRegex(ContractError,"SERVER_NOT_POWERED_ON"):
            plan_sole_server_power("reboot",down)
    def test_actions_are_closed_enum(self):
        for action in ("../reset","delete","shell","PowerOn",""):
            with self.assertRaisesRegex(ContractError,"OPERATION_REFUSED"):
                plan_sole_server_power(action,S)
    def test_task_redaction(self):
        result=task_status({"task":{"id":"lt123","is_completed":"InProgress",
               "progress_percent":42,"resources":[{"id":"HIDDEN"}],"token":"SECRET"}})
        self.assertEqual(result,{"state":"InProgress","progress_percent":42,"terminal":False})
        for raw in ({"task":{"is_completed":"unknown"}},
                    {"task":{"is_completed":"Completed","progress_percent":"99"}}):
            with self.assertRaises(ContractError):task_status(raw)
        self.assertEqual(validate_task_id("lt123"),"lt123")
        with self.assertRaises(ContractError):validate_task_id("../../../")
if __name__=="__main__":unittest.main()
