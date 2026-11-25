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
            ({"result":"ok"},{"config":{}}),
            ({"result":"ok"},[])]
        out=m.audit("a"*32,"t"*24)
        self.assertEqual(out["status"],"inactive")
        self.assertFalse(out["connections"]["connection_present"])
        self.assertEqual(len(response.call_args_list),4)
        self.assertTrue(response.call_args_list[1].args[0].endswith("/connections"))
        self.assertTrue(response.call_args_list[2].args[0].endswith("/configurations"))
        self.assertNotIn("12345678",str(out))

    def test_optional_config(self):
        self.assertEqual(m.config_summary(None), {"result":"configuration_not_returned"})
        self.assertEqual(m.config_summary({}), {"result":"configuration_not_returned"})

    def test_existing_service_exact_flags(self):
        row={"name":"pc-agent-loopback","type":"http","http_port":8765,"host":{"ipv4":"127.0.0.1","network":{"tunnel_id":"private-id"}}}
        out=m.service_summary([row],"private-id")
        self.assertTrue(all(out[k] for k in ("type_http","loopback","port_8765","same_tunnel")))
        self.assertNotIn("private-id",str(out))

    @patch.object(m,"response")
    def test_no_match_no_extra_calls(self,response):
        response.return_value=({"result":"ok"},[])
        self.assertEqual(m.audit("a"*32,"t"*24)["result"],"not_found_or_ambiguous")
        self.assertEqual(response.call_count,1)


if __name__ == "__main__":
    unittest.main()
