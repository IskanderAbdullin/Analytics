"""Mocked offline validation: makes no HTTP requests."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from cloudflare import AuditError, WORKERS, audit, check_request, get

class Reply:
    status=200
    def __init__(self,data):
        self.data=json.dumps({"success":True,"result":data}).encode()
        self.headers={"Content-Type":"application/json"}
    def read(self,n): return self.data[:n]
    def __enter__(self): return self
    def __exit__(self,*_): return False

class Tests(unittest.TestCase):
    def test_only_allowlisted_get(self):
        calls=[]
        def fake(req,timeout):
            calls.append((req.get_method(),req.full_url))
            return Reply({"bindings":[]})
        get("a"*32,"fake",WORKERS[0],"/settings",fake)
        self.assertEqual(calls,[("GET","https://api.cloudflare.com/client/v4/accounts/"+"a"*32+
                                 "/workers/scripts/babit-vps-bridge/settings")])
        for worker,path in (("evil","/settings"),(WORKERS[0],"/delete"),
                            (WORKERS[0],"/settings?url=evil")):
            with self.assertRaises(AuditError):
                get("a"*32,"fake",worker,path,fake)
        self.assertEqual(len(calls),1)

    def test_secret_fields_not_reported(self):
        calls=[]
        def fake(req,timeout):
            calls.append(req.full_url)
            if req.full_url.endswith("/settings"):
                return Reply({"bindings":[
                    {"name":"SERVERSPACE_API_KEY","value":"SECRET1"},
                    {"name":"VPS_AGENT_ENABLED","text":"SECRET2"},
                    {"name":"TINVEST_TOKEN","value":"SECRET3"}]})
            return Reply({"deployments":[{"id":"SECRET4","password":"SECRET5"}]})
        result=audit("a"*32,"fake",fake)
        self.assertTrue(result["connected"])
        self.assertEqual(len(calls),4)
        raw=json.dumps(result)
        for s in ("SECRET1","SECRET2","SECRET3","SECRET4","SECRET5"):
            self.assertNotIn(s,raw)

    def test_auth_error_never_exposes_response(self):
        def fake(req,timeout):
            raise HTTPError(req.full_url,403,"SECRET",None,io.BytesIO(b"SECRET"))
        with self.assertRaisesRegex(AuditError,"^HTTP_403$"):
            get("a"*32,"fake",WORKERS[0],"/settings",fake)

    def test_request_cannot_set_url_or_operation(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"request.json"
            path.write_text(json.dumps({"schema_version":1,"nonce":0,"operation":"inventory"}))
            check_request(path)
            for obj in (
                {"schema_version":1,"nonce":1,"operation":"delete"},
                {"schema_version":1,"nonce":True,"operation":"inventory"},
                {"schema_version":1,"nonce":1,"operation":"inventory","url":"https://evil"},
            ):
                path.write_text(json.dumps(obj))
                with self.assertRaises(AuditError):
                    check_request(path)

    def test_invalid_account_and_shape(self):
        with self.assertRaisesRegex(AuditError,"INVALID_ACCOUNT_ID"):
            get("evil","fake",WORKERS[0],"/settings",lambda *_: Reply([]))
        result=audit("a"*32,"fake",lambda req, timeout: Reply({"unexpected":"X"}))
        self.assertFalse(result["connected"])
        self.assertEqual(result["workers"][0]["error"],"INVALID_SETTINGS_SCHEMA")

if __name__=="__main__":
    unittest.main()
