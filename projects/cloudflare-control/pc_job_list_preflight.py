"""Read-only compatibility probe for the existing PC job-status MCP registration.
Production bundle and configuration stay in runner memory. Logs contain only
counts, version IDs, digests and fixed booleans; no source or credential values.
"""
import hashlib
import json
import os
import re
import sys
from email.parser import BytesParser
from email.policy import default
from urllib.request import Request, build_opener, HTTPRedirectHandler

TARGET = "/workers/scripts/t-invest-mcp-proxy"
EXPECTED = "46cff029-e225-46a8-bc4a-4d3efbb48914"
REG = re.compile(r'(?P<server>[A-Za-z_$][\w$]*)\.registerTool\("pc_script_status",\s*\{\s*description:\s*"[^"]*",\s*inputSchema:\s*(?P<z>[A-Za-z_$][\w$]*)\.object\(\{\s*jobId:\s*(?P=z)\.string\(\)\.regex\(/\^\[0-9a-fA-F\]\{32\}\$/\)\s*\}\)\s*\},\s*async\s*\(\{\s*jobId\s*\}\)\s*=>\s*(?P<invoke>[A-Za-z_$][\w$]*)\("/v1/script-status",\s*\{\s*jobId\s*\}\)\s*\);')
UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
class Blocked(Exception):
    pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def check(condition, code):
    if not condition:
        raise Blocked(code)

def read_factory():
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    check(re.fullmatch("[a-fA-F0-9]{32}", account) and len(token) >= 20, "AUTH_MISSING")
    base = "https://api.cloudflare.com/client/v4/accounts/" + account + TARGET
    opener = build_opener(NoRedirect())
    def get(path, raw=False):
        check(path in ("/deployments", "/settings", "/versions?per_page=10", "/content/v2", "/script-settings") or re.fullmatch(r"/versions/[a-f0-9-]{36}", path), "PATH_DENIED")
        req = Request(base + path, headers={"Authorization": "Bearer " + token, "Accept": "*/*" if raw else "application/json"}, method="GET")
        with opener.open(req, timeout=45) as response:
            cap = 160_000_000 if raw else 2_000_000
            data = response.read(cap + 1)
            check(len(data) <= cap, "BODY_TOO_LARGE")
            if raw:
                return data, response.headers.get("Content-Type", "")
        obj = json.loads(data)
        check(obj.get("success") is True, "API_REJECTED")
        return obj["result"]
    return get

def active(get):
    data = get("/deployments")
    rows = data.get("deployments") if isinstance(data, dict) else data
    check(isinstance(rows, list) and rows, "DEPLOYMENTS_UNKNOWN")
    versions = rows[0]["versions"]
    check(len(versions) == 1 and versions[0]["percentage"] == 100, "ACTIVE_AMBIGUOUS")
    v = versions[0]["version_id"]
    check(UUID.fullmatch(v), "VERSION_INVALID")
    return v

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read_modules(get):
    raw, mime = get("/content/v2", raw=True)
    check(mime.lower().startswith("multipart/"), "MULTIPART_REQUIRED")
    msg = BytesParser(policy=default).parsebytes(b"MIME-Version: 1.0\r\nContent-Type: " + mime.encode("ascii") + b"\r\n\r\n" + raw)
    parts = [(p.get_param("name", header="content-disposition"), p.get_content_type(), p.get_payload(decode=True)) for p in msg.iter_parts()]
    check(sorted(n for n, _, _ in parts) in (["index.js"], ["index.js", "index.js.map"]), "MODULE_LAYOUT_CHANGED")
    check(all(isinstance(data, bytes) for _, _, data in parts), "INVALID_MODULE")
    return parts

def audit(get):
    v = active(get)
    versions = get("/versions?per_page=10")
    versions = versions.get("items", versions.get("versions", [])) if isinstance(versions, dict) else versions
    check(isinstance(versions, list) and versions and versions[0]["id"] == v, "LATEST_NOT_ACTIVE")
    meta = get("/versions/" + v)
    current = get("/settings")
    bs = current["bindings"]
    types = {b["name"]: b["type"] for b in bs}
    check(len(types) == len(bs), "DUPLICATE_BINDING")
    required = {"OAUTH_KV", "PC_AGENT_RELAY", "VPS_AGENT_RELAY", "VPS_AGENT_SERVICE", "SERVERSPACE_SERVICE"}
    check(required <= types.keys(), "REQUIRED_BINDING_MISSING")
    by_name = {b["name"]: b for b in bs}
    for key, entry in (("VPS_AGENT_SERVICE", "VpsAdminEntrypoint"), ("SERVERSPACE_SERVICE", "ServerspaceReadOnlyEntrypoint")):
        b = by_name[key]
        check(b["type"] == "service" and b.get("service") == "babit-vps-bridge" and b.get("entrypoint") == entry, "SERVICE_DRIFT")
    for key, value in (("PC_AGENT_ENABLED", "true"), ("PC_AGENT_TRANSPORT", "wss"), ("VPS_AGENT_ENABLED", "true"), ("VPS_AGENT_ROUTE", "dedicated"), ("SERVERSPACE_ENABLED", "true")):
        b = by_name.get(key, {})
        check((b.get("text") or b.get("value")) == value, "FLAG_DRIFT")
    mods = read_modules(get)
    code = next(b for n, _, b in mods if n == "index.js")
    source = code.decode("utf-8")
    anchors = list(REG.finditer(source))
    # Check the new registration invokes exactly the same signed status route,
    # using the same captured server, schema library and invoke closure.
    check(len(anchors) == 1, "STATUS_ANCHOR_NOT_UNIQUE")
    a = anchors[0]
    new_reg = re.compile(re.escape(a["server"]) + r'\.registerTool\("pc_job_list",\s*\{\s*description:\s*"[^"]*",\s*inputSchema:\s*' + re.escape(a["z"]) + r'\.object\(\{\s*project:\s*' + re.escape(a["z"]) + r'\.string\(\)\.regex\(/\^\[A-Za-z0-9\]\[A-Za-z0-9\._ -\]\{0,62\}\$/\),\s*limit:\s*' + re.escape(a["z"]) + r'\.number\(\)\.int\(\)\.min\(1\)\.max\(50\)\.default\(20\)\s*\}\)\.strict\(\)\s*\},\s*async\s*\(\{\s*project,\s*limit\s*\}\)\s*=>\s*' + re.escape(a["invoke"]) + r'\("/v1/script-status",\s*\{\s*project,\s*limit\s*\}\)\s*\);')
    job_shape_count = len(new_reg.findall(source))
    previous_meta = get("/versions/" + EXPECTED)
    old_resources = previous_meta.get("resources") or {}
    new_resources = meta.get("resources") or {}
    old_bindings = old_resources.get("bindings")
    new_bindings = new_resources.get("bindings")
    check(isinstance(old_bindings, list) and isinstance(new_bindings, list), "VERSION_BINDINGS_UNKNOWN")
    # Compare every returned binding field in memory, never emit raw values.
    bindings_exact = sorted(old_bindings, key=lambda b:b["name"]) == sorted(new_bindings, key=lambda b:b["name"])
    runtime_exact = old_resources.get("script_runtime") == new_resources.get("script_runtime")
    runtime = (meta.get("resources") or {}).get("script_runtime") or {}
    check(active(get) == v, "ACTIVE_DRIFT")
    return {"status": "read_only_passed", "version": v, "expected_baseline": v == EXPECTED,
            "latest_is_active": True, "binding_count": len(bs), "binding_names_types_sha256": digest(json.dumps(types, sort_keys=True).encode()),
            "module_sha256": digest(code), "module_count": len(mods),
            "pc_status_registration_count": source.count('registerTool("pc_script_status"'),
            "status_exact_shape_count": len(anchors), "pc_job_list_registration_count": source.count('registerTool("pc_job_list"'),
            "job_list_exact_shape_count": job_shape_count, "version_bindings_exact": bindings_exact,
            "runtime_metadata_exact": runtime_exact, "runtime_metadata_present": bool(runtime), "dedicated_routes_preserved": True,
            "cloud_write_attempted": False}


def metrics():
    # Fixed read-only GraphQL queries; no user input, raw results, account IDs or credentials logged.
    from datetime import datetime, timedelta, timezone
    from urllib.error import HTTPError
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID","")
    token = os.getenv("CLOUDFLARE_API_TOKEN","")
    check(re.fullmatch("[a-fA-F0-9]{32}", account) and len(token)>=20,"AUTH_MISSING")
    end=datetime.now(timezone.utc).replace(microsecond=0)
    start=end-timedelta(hours=1)
    def fmt(t): return t.strftime("%Y-%m-%dT%H:%M:%SZ")
    def gql(dataset,fields,script):
        query="{ viewer { accounts(filter:{accountTag:"+json.dumps(account)+"}) { "+dataset+"(limit:100,filter:{datetime_geq:"+json.dumps(fmt(start))+",datetime_leq:"+json.dumps(fmt(end))+",scriptName:"+json.dumps(script)+"}) { "+fields+" } } } }"
        req=Request("https://api.cloudflare.com/client/v4/graphql", data=json.dumps({"query":query}).encode(),headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"},method="POST")
        try:
            with build_opener(NoRedirect()).open(req,timeout=25) as res:
                raw=res.read(2_000_001)
            if len(raw)>2_000_000:return {"result":"response_too_large"}
            p=json.loads(raw)
            if p.get("errors"):
                # Classify errors without printing returned strings.
                msgs=" ".join(str(e.get("message","")) for e in p["errors"] if isinstance(e,dict)).lower()
                return {"result":"graphql_error","permission_denied":any(x in msgs for x in ("permission","not authorized","not have access","forbidden","access denied","authentication")),"schema_error":any(x in msgs for x in ("unknown field","cannot query field","unknown argument","not defined","does not exist"))}
            rows=p["data"]["viewer"]["accounts"][0][dataset]
            if not isinstance(rows,list):return {"result":"invalid_schema"}
            safe=[]
            allowed={"success","clientDisconnected","scriptThrewException","exceededResources","internalError","unknown","exceededCpu","exceededMemory","canceled"}
            for row in rows:
                dims=row.get("dimensions",{})
                status=dims.get("status","ungrouped")
                if status not in allowed and status!="ungrouped":status="other"
                item={"status":status}
                for k in ("requests","errors"):
                    v=row.get("sum",{}).get(k)
                    if isinstance(v,(int,float)) and 0<=v<1e15:item[k]=v
                for k in ("cpuTimeP50","cpuTimeP99","wallTimeP50","wallTimeP99"):
                    v=row.get("quantiles",{}).get(k)
                    if isinstance(v,(int,float)) and 0<=v<1e15:item[k]=v
                safe.append(item)
            return {"result":"ok","rows":safe}
        except HTTPError as e:return {"result":"http_error","http_status":e.code}
        except Exception:return {"result":"network_or_schema_error"}
    results={}
    for script,label in (("t-invest-mcp-proxy","shared_worker"),("babit-vps-bridge","dedicated_worker")):
        results[label]={
            "workers":gql("workersInvocationsAdaptive","sum { requests errors } quantiles { cpuTimeP50 cpuTimeP99 wallTimeP50 wallTimeP99 } dimensions { status }",script),
            "durable_objects":gql("durableObjectsInvocationsAdaptiveGroups","sum { requests } quantiles { cpuTimeP99 } dimensions { status }",script)
        }
    print(json.dumps({"metrics_read_only":True,"start_utc":fmt(start),"end_utc":fmt(end),"results":results},sort_keys=True),flush=True)

if __name__ == "__main__":
    try:
        metrics()
        print(json.dumps(audit(read_factory()), sort_keys=True), flush=True)
    except Blocked as exc:
        print(json.dumps({"status": "blocked", "code": str(exc), "cloud_write_attempted": False}), flush=True)
        sys.exit(3)
    except Exception:
        print('{"status":"blocked","code":"API_OR_SCHEMA_FAILURE","cloud_write_attempted":false}', flush=True)
        sys.exit(3)

# Explicit read-only Actions run after branch creation.

# D150 authorized PC maintenance preflight: GET only, no production write.

# D151: refresh read-only live baseline during simultaneous PC/VPS transport timeouts.

# D176: refresh existing read-only exact baseline and aggregate metrics after PC_AGENT_HTTP_503.
