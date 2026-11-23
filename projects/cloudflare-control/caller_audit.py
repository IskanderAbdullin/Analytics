"""Inspect live OAuth Worker compatibility without disclosing code or bindings."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cloudflare-control"))
from serverspace_deploy import Cloudflare, SafeError, decode_worker

TARGET="/workers/scripts/t-invest-mcp-proxy"
CHECK=("list_upstream_tool_names","list_allowed_market_tools","call_market_tool",
       "pc_status","vps_status","serverspace_list_servers",
       "function createServer", "function createServer(", "return server;",
       "registerTool(", "SERVERSPACE_SERVICE", "SERVERSPACE_ENABLED")

def audit():
    cf=Cloudflare()
    print('{"stage":"oauth_caller_audit","phase":"deployments"}',flush=True)
    ds=cf.call("GET", TARGET+"/deployments")
    ds=ds.get("deployments") if isinstance(ds,dict) else ds
    if not isinstance(ds,list) or not ds:
        raise SafeError("CALLER_DEPLOYMENT_MISSING")
    active=next((v.get("version_id") for v in ds[0].get("versions",[])
                 if v.get("percentage")==100),None)
    if not isinstance(active,str): raise SafeError("CALLER_ACTIVE_UNKNOWN")
    print('{"stage":"oauth_caller_audit","phase":"version"}',flush=True)
    version=cf.call("GET", TARGET+"/versions/"+active)
    resources=version.get("resources") or {}
    bindings=resources.get("bindings") or []
    names={b.get("name") for b in bindings if isinstance(b,dict)}
    types={b.get("name"):b.get("type") for b in bindings if isinstance(b,dict)}
    runtime=resources.get("script_runtime") or {}
    print('{"stage":"oauth_caller_audit","phase":"content"}',flush=True)
    source, source_type, main_header=cf.call("GET", TARGET+"/content/v2", raw=True)
    modules, main=decode_worker(source_type,source,main_header)
    body=next((m.content for m in modules if m.filename==main),b"")
    if not body:raise SafeError("CALLER_SOURCE_UNKNOWN")
    flags={}
    for key in ("PC_AGENT_ENABLED","VPS_AGENT_ENABLED","SERVERSPACE_ENABLED"):
        b=next((x for x in bindings if isinstance(x,dict) and x.get("name")==key),None)
        flags[key] = "true" if b and (b.get("text") or b.get("value"))=="true" else "not_true"
    print(json.dumps({"stage":"oauth_caller_audit","result":"inspected",
      "module_count":len(modules),"main_module_bytes":len(body),
      "known_bindings_present":{k:k in names for k in ("OAUTH_KV",
       "GOOGLE_CLIENT_ID","GOOGLE_CLIENT_SECRET","COOKIE_ENCRYPTION_KEY",
       "ALLOWED_GOOGLE_EMAIL","TINVEST_TOKEN","PC_AGENT_RELAY",
       "VPS_AGENT_RELAY","SERVERSPACE_SERVICE")},
      "service_binding_kind":types.get("SERVERSPACE_SERVICE","absent"),
      "flags":flags,
      "named_exports":sorted((runtime.get("exports") or {}).keys()),
      "anchors":{s:body.count(s.encode()) for s in CHECK}
    },sort_keys=True))
if __name__=="__main__":
    try:audit()
    except SafeError as exc:
        raw=str(exc)
        code=raw if re.fullmatch(r"[A-Za-z0-9_:-]{2,72}",raw) else "cloudflare_api_error"
        print(json.dumps({"stage":"oauth_caller_audit","result":"blocked","code":code}))
        raise SystemExit(3)
