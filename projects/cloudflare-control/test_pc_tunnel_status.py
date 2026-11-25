import io
import json
import unittest
from urllib.error import HTTPError
from pc_tunnel_status import audit, summarize, NAME, LIMIT


class Fake(io.BytesIO):
    status = 200
    headers = {"Content-Type": "application/json"}


class TunnelAuditTests(unittest.TestCase):
    def test_whitelist(self):
        row = {"name": NAME, "status": "inactive", "id": "private-id",
               "connections": [{"origin_ip": "private-ip"}], "account_tag": "secret"}
        self.assertEqual(summarize({"success": True, "result": [row]}),
                         {"result": "ok", "tunnel_status": "inactive", "edge_connected": False})

    def test_connected(self):
        for status in ("healthy", "degraded"):
            self.assertTrue(summarize({"success": True, "result":
                                        [{"name": NAME, "status": status}]})["edge_connected"])

    def test_ambiguous_deleted_unknown(self):
        row = {"name": NAME, "status": "down"}
        for rows, expected in [([], "not_found"), ([row, row], "ambiguous"),
                                ([dict(row, deleted_at="x")], "not_found"),
                                ([dict(row, status="sensitive")], "unknown_status")]:
            self.assertEqual(summarize({"success": True, "result": rows}), {"result": expected})

    def test_bad_schema(self):
        self.assertEqual(summarize({"success": True, "result": [1]}),
                         {"result": "invalid_schema"})

    def test_fixed_request(self):
        def fake(req, timeout):
            self.assertEqual(req.get_method(), "GET")
            self.assertTrue(req.full_url.endswith("/cfd_tunnel?name=pc-agent-private&is_deleted=false&per_page=10"))
            self.assertEqual(timeout, 10)
            return Fake(json.dumps({"success": True, "result": [{"name": NAME, "status": "down"}]}).encode())
        self.assertEqual(audit("a" * 32, "t" * 24, fake)["tunnel_status"], "down")

    def test_denied(self):
        def fake(req, timeout):
            raise HTTPError(req.full_url, 403, "do not print", {}, None)
        self.assertEqual(audit("a" * 32, "t" * 24, fake), {"result": "http_error", "http_status": 403})

    def test_size(self):
        self.assertEqual(audit("a" * 32, "t" * 24, lambda *_args, **_kwargs: Fake(b"x" * (LIMIT + 1))),
                         {"result": "response_too_large"})

    def test_missing_auth(self):
        self.assertEqual(audit("", ""), {"result": "secrets_unavailable"})


if __name__ == "__main__":
    unittest.main()
