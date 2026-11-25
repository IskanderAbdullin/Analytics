import unittest
from unittest.mock import patch
import pc_tunnel_readiness as m


class TestReadiness(unittest.TestCase):
    def test_no_origin(self):
        self.assertEqual(m.config_summary({"config":{"ingress":[{"service":"http_status:404"}]}}),
                         {"result":"ok","hostname_rule_present":False,"origin_rule_present":False,"private_routing_enabled":False})

    def test_flags_only(self):
        got = m.config_summary({"config":{"ingress":[{"hostname":"private.invalid","service":"ssh://127.0.0.1:22"}],"warp-routing":{"enabled":True}}})
        self.assertTrue(got["hostname_rule_present"] and got["origin_rule_present"] and got["private_routing_enabled"])
        self.assertNotIn("private.invalid", str(got))
        self.assertNotIn("127.0.0.1", str(got))

    def test_invalid_config(self):
        self.assertEqual(m.config_summary({"config":{"ingress":[None]}}), {"result":"invalid_schema"})

    @patch.object(m, "response")
    def test_exact_named_tunnel(self, response):
        response.side_effect = [
            ({"result":"ok"},[{"name":m.NAME,"id":"12345678-1234-1234-1234-123456789abc","status":"inactive","config_src":"cloudflare"}]),
            ({"result":"ok"},[]),
            ({"result":"ok"},{"config":{}})]
        out=m.audit("a"*32,"t"*24)
        self.assertEqual(out["status"],"inactive")
        self.assertFalse(out["connections"]["connection_present"])
        self.assertEqual(len(response.call_args_list),3)
        self.assertTrue(response.call_args_list[1].args[0].endswith("/connections"))
        self.assertTrue(response.call_args_list[2].args[0].endswith("/configurations"))
        self.assertNotIn("12345678",str(out))

    @patch.object(m,"response")
    def test_no_match_no_extra_calls(self,response):
        response.return_value=({"result":"ok"},[])
        self.assertEqual(m.audit("a"*32,"t"*24)["result"],"not_found_or_ambiguous")
        self.assertEqual(response.call_count,1)


if __name__ == "__main__":
    unittest.main()
