"""Fixed, read-only Cloudflare Workers inventory. Public logs contain no API bodies."""
import hashlib
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


# PC-Agent release D143: fixed read-only baseline comparison. Public output
# contains only booleans and counts, not version IDs, raw bindings or values.
PC_BASELINE_VERSION_DIGEST = "e0a22ff28dcc4d8f769dbe71b95135a25170b1a8e4d063b1d2031bfd2d1ff2dd"
PC_BASELINE_BINDINGS_DIGEST = "bd832cdf22f62e24fc67732e2ba519fd31b8dcc3c8f9dca6ee33f81c1e53c3ec"

def pc_baseline(settings, deployments):
    bindings = settings.get("bindings") if isinstance(settings, dict) else None
    deployments = deployments.get("deployments") if isinstance(deployments, dict) else deployments
    rows = bindings if isinstance(bindings, list) else []
    well_formed = all(isinstance(b, dict) and isinstance(b.get("name"), str)
                      and isinstance(b.get("type"), str) for b in rows)
    by_name = {b["name"]: b for b in rows} if well_formed else {}
    digest = hashlib.sha256("\n".join(sorted(
        b["type"] + ":" + b["name"] for b in rows
    )).encode()).hexdigest() if well_formed else ""
    binding_match = (len(rows) == len(by_name) == 27
                     and digest == PC_BASELINE_BINDINGS_DIGEST)
    versions = deployments[0].get("versions", []) if (
        isinstance(deployments, list) and deployments and isinstance(deployments[0], dict)
    ) else []
    active = versions[0] if isinstance(versions, list) and len(versions) == 1 and isinstance(versions[0], dict) else {}
    vid = active.get("version_id")
    version_match = bool(active.get("percentage") == 100 and isinstance(vid, str)
                         and hashlib.sha256(vid.encode()).hexdigest() == PC_BASELINE_VERSION_DIGEST)
    def var(name, expected):
        b = by_name.get(name, {})
        return b.get("type") == "plain_text" and b.get("text", b.get("value")) == expected
    def service(name, entrypoint):
        b = by_name.get(name, {})
        return (b.get("type") == "service" and b.get("service") == "babit-vps-bridge"
                and b.get("entrypoint") == entrypoint)
    routes = (var("PC_AGENT_ENABLED", "true") and var("PC_AGENT_TRANSPORT", "wss")
              and var("VPS_AGENT_ENABLED", "true") and var("VPS_AGENT_ROUTE", "dedicated")
              and var("SERVERSPACE_ENABLED", "true"))
    services = (service("VPS_AGENT_SERVICE", "VpsAdminEntrypoint")
                and service("SERVERSPACE_SERVICE", "ServerspaceReadOnlyEntrypoint"))
    return {"binding_count": len(rows), "binding_set_matches": binding_match,
            "active_version_matches": version_match, "route_flags_match": routes,
            "service_entrypoints_match": services,
            "baseline_matches": binding_match and version_match and routes and services}

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
            deployments=get(account,token,worker,"/deployments",transport)
            item["deployed"]=_deployed(deployments)
            if worker=="t-invest-mcp-proxy":
                item["pc_baseline"]=pc_baseline(settings,deployments)
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
