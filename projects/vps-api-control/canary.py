"""Isolated single-purpose Cloudflare same-account Serverspace private-binding probe.

Public repository: never log cloud credentials, resource IDs, Worker bodies or VPS
names. Runs only on GitHub Actions with the owner's existing Cloudflare secrets.
Does not execute commands, change VPS state or interact with brokers.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

WORKER = "babit-ss-diagnostic-1123"
KV_TITLE = "babit-ss-diagnostic-1123"
BRIDGE = "babit-vps-bridge"
ROOT = "https://api.cloudflare.com/client/v4/accounts"
JS = r'''
export default {
  fetch() { return new Response("Not found", {status:404}); },
  async scheduled(controller, env, ctx) {
    ctx.waitUntil((async () => {
      if (await env.PROBE_RESULTS.get("result")) return;
      let outcome = "fetch_failed";
      try {
        const response = await env.SERVERSPACE_SERVICE.fetch(
          "http://serverspace.internal/internal/serverspace/list-servers",
          {method:"POST", redirect:"manual", signal:AbortSignal.timeout(12000)}
        );
        if (response.ok) {
          const value = await response.json();
          outcome = value && Array.isArray(value.servers) &&
            Number.isInteger(value.count) && value.count === value.servers.length
            ? "serverspace_inventory_ok" : "invalid_schema";
        } else {
          outcome = "bridge_http_" + response.status;
        }
      } catch (_) { outcome = "fetch_failed"; }
      await env.PROBE_RESULTS.put("result", JSON.stringify({outcome}),
                                 {expirationTtl:3600});
    })());
  }
};
'''
class ProbeError(Exception):
    pass

def emit(stage, outcome, **extra):
    print(json.dumps({"stage":stage,"outcome":outcome,**extra},sort_keys=True),flush=True)

def api(method, path, data=None, mime="application/json", raw=False):
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID","")
    token = os.environ.get("CLOUDFLARE_API_TOKEN","")
    if not re.fullmatch(r"[0-9a-fA-F]{32}",account) or len(token)<12:
        raise ProbeError("secrets_unavailable")
    if not path.startswith("/") or "//" in path or ".." in path:
        raise ProbeError("path_refused")
    req=Request(ROOT+"/"+account+path, data=data, method=method,
                headers={"Authorization":"Bearer "+token,
                         "Accept":"application/json",
                         **({"Content-Type":mime} if data is not None else {})})
    try:
        with urlopen(req,timeout=20) as response:
            body=response.read(240000)
            if len(body)>=240000: raise ProbeError("response_oversize")
            if raw: return body
            result=json.loads(body)
            if not isinstance(result,dict) or result.get("success") is not True:
                raise ProbeError("cloudflare_rejected")
            return result.get("result")
    except HTTPError as exc:
        raise ProbeError("http_"+str(exc.code)) from None
    except (URLError,TimeoutError,OSError):
        raise ProbeError("connection_failed") from None
    except (ValueError,UnicodeError):
        raise ProbeError("invalid_json") from None

def multipart(metadata, js):
    boundary="----BabitCanary"+uuid.uuid4().hex
    parts=[]
    for name,body,ctype in (("metadata",json.dumps(metadata).encode(),"application/json"),
                            ("main.mjs",js.encode(),"application/javascript+module")):
        parts.extend([
            ("--"+boundary+"\r\n").encode(),
            ('Content-Disposition: form-data; name="'+name+'"'+
             ('; filename="main.mjs"' if name=="main.mjs" else '')+"\r\n").encode(),
            ("Content-Type: "+ctype+"\r\n\r\n").encode(),body,b"\r\n"
        ])
    parts.append(("--"+boundary+"--\r\n").encode())
    return b"".join(parts),"multipart/form-data; boundary="+boundary

def get_namespace():
    namespaces=api("GET","/storage/kv/namespaces?per_page=100")
    if not isinstance(namespaces,list): raise ProbeError("kv_list_schema")
    matching=[n for n in namespaces if isinstance(n,dict) and n.get("title")==KV_TITLE]
    if len(matching)>1: raise ProbeError("duplicate_kv_namespaces")
    if matching:
        ns=matching[0].get("id")
        if not isinstance(ns,str) or not re.fullmatch(r"[0-9a-fA-F]{32}",ns):
            raise ProbeError("kv_id_schema")
        return ns
    ns=api("POST","/storage/kv/namespaces",json.dumps({"title":KV_TITLE}).encode())
    if not isinstance(ns,dict) or not re.fullmatch(r"[0-9a-fA-F]{32}",ns.get("id","")):
        raise ProbeError("kv_create_schema")
    return ns["id"]

def main():
    # Existing dedicated Worker is never modified; only its metadata is read.
    history=api("GET","/workers/scripts/"+BRIDGE+"/deployments")
    records=history.get("deployments") if isinstance(history,dict) else history
    if not isinstance(records,list) or not records:
        raise ProbeError("existing_bridge_not_deployed")
    active=next((v.get("version_id") for v in records[0].get("versions",[])
                 if v.get("percentage")==100),None)
    if not isinstance(active,str): raise ProbeError("active_bridge_unknown")
    version=api("GET","/workers/scripts/"+BRIDGE+"/versions/"+active)
    exports=((version or {}).get("resources") or {}).get("script_runtime",{}).get("exports",{})
    if not isinstance(exports,dict) or exports.get("ServerspaceReadOnlyEntrypoint",{}).get("type")!="worker":
        raise ProbeError("private_entrypoint_missing")
    bindings=((version or {}).get("resources") or {}).get("bindings",[])
    names={x.get("name") for x in bindings if isinstance(x,dict)}
    if "SERVERSPACE_API_KEY" not in names: raise ProbeError("serverspace_secret_not_bound")
    enabled=next((x.get("text") or x.get("value") for x in bindings
                  if isinstance(x,dict) and x.get("name")=="SERVERSPACE_API_ENABLED"),None)
    emit("bridge_audit","entrypoint_present",api_enabled=(enabled=="true"))
    ns=get_namespace()
    emit("canary","kv_namespace_ready")
    # Never overwrite an unknown Worker. If this exact one already exists,
    # inspect its schedules and result only rather than replacing its script.
    base="/workers/scripts/"+WORKER
    existing=False
    try:
        api("GET",base+"/settings")
        existing=True
    except ProbeError as exc:
        if str(exc)!="http_404": raise
    if not existing:
        meta={"main_module":"main.mjs","compatibility_date":"2026-11-23",
              "bindings":[
                  {"type":"service","name":"SERVERSPACE_SERVICE",
                   "service":BRIDGE,"entrypoint":"ServerspaceReadOnlyEntrypoint"},
                  {"type":"kv_namespace","name":"PROBE_RESULTS","namespace_id":ns}
              ]}
        body,ctype=multipart(meta,JS)
        api("PUT",base,body,ctype)
        emit("canary","worker_uploaded")
        deployments=api("GET",base+"/deployments")
        ds=deployments.get("deployments") if isinstance(deployments,dict) else deployments
        if not isinstance(ds,list) or not ds:
            versions=api("GET",base+"/versions?per_page=5")
            vs=versions.get("items") if isinstance(versions,dict) else versions
            if not isinstance(vs,list) or not vs or not isinstance(vs[0].get("id"),str):
                raise ProbeError("new_worker_version_not_found")
            api("POST",base+"/deployments",json.dumps({"strategy":"percentage",
                "versions":[{"version_id":vs[0]["id"],"percentage":100}]}).encode())
        api("PUT",base+"/schedules",json.dumps({"schedules":[{"cron":"* * * * *"}]}).encode())
        emit("canary","cron_enabled")
    else:
        # This is our fixed diagnostic Worker; only re-arm its known KV key
        # and cron. Never update or replace the existing script or bindings.
        api("DELETE","/storage/kv/namespaces/"+ns+"/values/result")
        api("PUT",base+"/schedules",json.dumps({"schedules":[{"cron":"* * * * *"}]}).encode())
        emit("canary","existing_worker_rearmed_without_code_change")
    # Cron propagation may take up to 15 minutes; a timeout is not a failed API.
    key="/storage/kv/namespaces/"+ns+"/values/result"
    for attempt in range(19):
        time.sleep(10)
        try:
            payload=json.loads(api("GET",key,raw=True))
        except ProbeError as exc:
            if str(exc)=="http_404": continue
            raise
        except ValueError:
            raise ProbeError("probe_result_invalid")
        code=payload.get("outcome") if isinstance(payload,dict) else None
        if not isinstance(code,str) or not re.fullmatch(r"[a-z0-9_]{3,55}",code):
            raise ProbeError("probe_result_invalid")
        emit("cloudflare_private_call",code)
        # Disable recurrence after any final response, preserve diagnostics.
        api("PUT",base+"/schedules",json.dumps({"schedules":[]}).encode())
        emit("canary","cron_disabled")
        return 0 if code=="serverspace_inventory_ok" else 4
    emit("cloudflare_private_call","pending_cron_propagation")
    return 5

if __name__=="__main__":
    try: sys.exit(main())
    except ProbeError as exc:
        emit("stopped",str(exc))
        sys.exit(3)
