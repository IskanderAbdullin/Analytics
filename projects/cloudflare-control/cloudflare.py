"""Fixed, read-only Cloudflare Workers inventory. Public logs contain no API bodies."""
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = "https://api.cloudflare.com/client/v4/accounts"
WORKERS = ("babit-vps-bridge", "t-invest-mcp-proxy")
MAX_BYTES = 120000

class AuditError(Exception):
    pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def check_request(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise AuditError("INVALID_REQUEST") from None
    if not isinstance(data, dict) or set(data) != {"schema_version","nonce","operation"}:
        raise AuditError("INVALID_REQUEST")
    if data["schema_version"] != 1 or data["operation"] != "inventory":
        raise AuditError("INVALID_REQUEST")
    if type(data["nonce"]) is not int or not 0 <= data["nonce"] <= 2147483647:
        raise AuditError("INVALID_REQUEST")

def get(account, token, worker, endpoint, transport=None):
    if not re.fullmatch(r"[0-9a-fA-F]{32}", account):
        raise AuditError("INVALID_ACCOUNT_ID")
    if worker not in WORKERS or endpoint not in ("/settings", "/deployments"):
        raise AuditError("REFUSED_UNLISTED_ROUTE")
    url = f"{ROOT}/{account}/workers/scripts/{worker}{endpoint}"
    req = Request(url, method="GET", headers={
        "Authorization": "Bearer "+token, "Accept": "application/json"})
    try:
        opener = transport or build_opener(NoRedirect()).open
        with opener(req, timeout=10) as res:
            if res.status != 200:
                raise AuditError("HTTP_"+str(res.status))
            if "application/json" not in res.headers.get("Content-Type","").lower():
                raise AuditError("INVALID_CONTENT_TYPE")
            raw = res.read(MAX_BYTES+1)
    except HTTPError as e:
        raise AuditError("HTTP_"+str(e.code)) from None
    except (URLError, TimeoutError, OSError):
        raise AuditError("UPSTREAM_UNAVAILABLE") from None
    if len(raw) > MAX_BYTES:
        raise AuditError("RESPONSE_TOO_LARGE")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        raise AuditError("INVALID_JSON") from None
    if not isinstance(data,dict) or data.get("success") is not True:
        raise AuditError("CLOUDFLARE_REJECTED")
    return data.get("result")

def _bindings(data, expected):
    if not isinstance(data,dict) or not isinstance(data.get("bindings"),list):
        raise AuditError("INVALID_SETTINGS_SCHEMA")
    return any(isinstance(x,dict) and x.get("name")==expected for x in data["bindings"])

def _deployed(data):
    v = data.get("deployments") if isinstance(data,dict) else data
    if not isinstance(v,list):
        raise AuditError("INVALID_DEPLOYMENTS_SCHEMA")
    return len(v)>0

def audit(account, token, transport=None):
    out={"schema_version":1,"mode":"read_only","workers":[]}
    for worker in WORKERS:
        expected="SERVERSPACE_API_KEY" if worker==WORKERS[0] else "VPS_AGENT_ENABLED"
        item={"worker":worker,"settings_ok":False,"deployed":False,
              "expected_binding":expected,"binding_present":False}
        try:
            settings=get(account,token,worker,"/settings",transport)
            item["binding_present"]=_bindings(settings,expected)
            item["settings_ok"]=True
            item["deployed"]=_deployed(get(account,token,worker,"/deployments",transport))
        except AuditError as e:
            item["error"]=str(e)
        out["workers"].append(item)
    out["connected"]=all(x["settings_ok"] for x in out["workers"])
    return out

def main():
    try:
        check_request(Path(__file__).with_name("request.json"))
    except AuditError:
        print('{"status":"invalid_request"}')
        return 2
    token=os.getenv("CLOUDFLARE_API_TOKEN","")
    account=os.getenv("CLOUDFLARE_ACCOUNT_ID","")
    if not re.fullmatch(r"[0-9a-fA-F]{32}",account) or len(token)<12:
        print('{"status":"secrets_unavailable","connected":false}')
        return 3
    report=audit(account,token)
    # The API can include plaintext variables: NEVER print raw responses.
    print(json.dumps(report,sort_keys=True))
    return 0 if report["connected"] else 4

if __name__ == "__main__":
    sys.exit(main())
