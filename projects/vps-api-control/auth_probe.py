"""Non-executing HMAC rejection probe for the existing named VPS admin binding.

Only the already deployed diagnostic Worker is reused; no new Worker or token.
Never submits an authenticated VPS action, never reads HMAC keys, never
discloses a device/server identifier. Distinguishes disabled/invalid Worker
environment (503) from a healthy HMAC guard (401) before checking WSS status.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from canary import ProbeError, WORKER, BRIDGE, api, get_namespace, emit, multipart

REQUEST=Path(__file__).with_name("auth_probe_request.json")
KEY="vps_admin_auth_probe_v1"
ADMIN_BINDING="VPS_ADMIN_SERVICE"
ADMIN_EXPORT="VpsAdminEntrypoint"
TARGET="babit-vps-bridge"
JS=r'''
export default {
  fetch() { return new Response("Not found",{status:404}); },
  async scheduled(event, env, ctx) {
    ctx.waitUntil((async()=>{
      if(await env.PROBE_RESULTS.get("vps_admin_auth_probe_v1")) return;
      let code="probe_failed";
      try {
        const res=await env.VPS_ADMIN_SERVICE.fetch(
          "http://vps.internal/v1/vps/status",
          {method:"POST",redirect:"manual",body:"{}",
           headers:{"Content-Type":"application/json"},
           signal:AbortSignal.timeout(8000)});
        // Deliberately omit all X-VPS-* HMAC headers: 401 is EXPECTED.
        // Signed Linux commands can never be dispatched by this probe.
        code="admin_http_"+res.status;
      }catch(_){code="probe_failed";}
      await env.PROBE_RESULTS.put("vps_admin_auth_probe_v1",
        JSON.stringify({schema:1,outcome:code}),
        {expirationTtl:3600});
    })());
  }
};
'''

def check_request():
    obj=json.loads(REQUEST.read_text(encoding="utf-8"))
    if (not isinstance(obj,dict) or
        set(obj)!={"schema_version","nonce","operation"} or
        obj["schema_version"]!=1 or
        type(obj["nonce"]) is not int or not 0<=obj["nonce"]<=2147483647
        or obj["operation"] not in ("stage","read")):
        raise ProbeError("invalid_request")
    return obj["operation"]

def safe_existing(ns, needs_admin=False):
    base="/workers/scripts/"+WORKER
    settings=api("GET",base+"/settings")
    bindings=settings.get("bindings") if isinstance(settings,dict) else None
    if not isinstance(bindings,list):
        raise ProbeError("diagnostic_bindings_missing")
    names={b.get("name"):b for b in bindings if isinstance(b,dict)}
    if set(names)-{"PROBE_RESULTS","SERVERSPACE_SERVICE",ADMIN_BINDING}:
        raise ProbeError("diagnostic_unknown_binding")
    if set(names)!={"PROBE_RESULTS","SERVERSPACE_SERVICE"} and (
        set(names)!={"PROBE_RESULTS","SERVERSPACE_SERVICE",ADMIN_BINDING}):
        raise ProbeError("diagnostic_binding_shape")
    ss=names["SERVERSPACE_SERVICE"];store=names["PROBE_RESULTS"]
    if (ss.get("type")!="service" or ss.get("service")!=BRIDGE
        or ss.get("entrypoint")!="ServerspaceReadOnlyEntrypoint"
        or store.get("type")!="kv_namespace" or store.get("namespace_id")!=ns):
        raise ProbeError("diagnostic_original_binding_changed")
    has_admin=ADMIN_BINDING in names
    if has_admin:
        admin=names[ADMIN_BINDING]
        if (admin.get("type")!="service" or admin.get("service")!=TARGET
            or admin.get("entrypoint")!=ADMIN_EXPORT):
            raise ProbeError("diagnostic_admin_binding_changed")
    if needs_admin and not has_admin:
        raise ProbeError("admin_binding_not_live")
    return base,has_admin

def ensure_private_export():
    base="/workers/scripts/"+TARGET
    history=api("GET",base+"/deployments")
    entries=history.get("deployments") if isinstance(history,dict) else history
    if not isinstance(entries,list) or not entries:
        raise ProbeError("admin_target_not_deployed")
    active=next((v.get("version_id") for v in entries[0].get("versions",[])
                 if v.get("percentage")==100),None)
    if not isinstance(active,str):
        raise ProbeError("admin_target_version_unknown")
    details=api("GET",base+"/versions/"+active)
    exports=(((details or {}).get("resources") or {}).get("script_runtime") or {}).get("exports") or {}
    if exports.get(ADMIN_EXPORT,{}).get("type")!="worker":
        raise ProbeError("admin_target_export_missing")

def stage(ns):
    base,has_admin=safe_existing(ns)
    ensure_private_export()
    raw=api("GET",base+"/content/v2",raw=True)
    if b"vps_admin_auth_probe_v1" in raw and has_admin:
        emit("vps_auth_probe","already_staged")
    else:
        if b"summary_v1" not in raw:
            raise ProbeError("unknown_diagnostic_source")
        bindings=[
          {"type":"service","name":"SERVERSPACE_SERVICE",
           "service":BRIDGE,"entrypoint":"ServerspaceReadOnlyEntrypoint"},
          {"type":"kv_namespace","name":"PROBE_RESULTS","namespace_id":ns},
          {"type":"service","name":ADMIN_BINDING,"service":TARGET,
           "entrypoint":ADMIN_EXPORT}]
        body,ctype=multipart({"main_module":"main.mjs",
                              "compatibility_date":"2026-11-23",
                              "bindings":bindings},JS)
        api("PUT",base,body,ctype)
        safe_existing(ns,needs_admin=True)
        latest=api("GET",base+"/content/v2",raw=True)
        if b"vps_admin_auth_probe_v1" not in latest:
            raise ProbeError("auth_probe_upload_not_live")
        emit("vps_auth_probe","upload_confirmed")
    api("PUT",base+"/schedules",json.dumps([{"cron":"* * * * *"}]).encode())
    emit("vps_auth_probe","scheduled",intentionally_unsigned=True)
    return 0

def read(ns):
    base,_=safe_existing(ns,needs_admin=True)
    try:
        payload=json.loads(api("GET","/storage/kv/namespaces/"+ns+
                               "/values/"+KEY,raw=True))
    except ProbeError as exc:
        if str(exc).startswith("http_404"):
            emit("vps_auth_probe","pending")
            return 5
        raise
    except (ValueError,TypeError):
        raise ProbeError("invalid_probe_result") from None
    if not isinstance(payload,dict) or payload.get("schema")!=1:
        raise ProbeError("probe_schema_invalid")
    outcome=payload.get("outcome")
    if not isinstance(outcome,str) or not re.fullmatch(r"(admin_http_[0-9]{3}|probe_failed)",outcome):
        raise ProbeError("probe_outcome_unexpected")
    emit("vps_auth_probe",outcome,
         interpretation=("vps_hmac_guard_ready" if outcome=="admin_http_401"
                         else "vps_config_or_route_issue" if outcome=="admin_http_503"
                         else "unexpected_response"))
    api("PUT",base+"/schedules",json.dumps([]).encode())
    emit("vps_auth_probe","cron_stopped_after_read")
    return 0 if outcome=="admin_http_401" else 4

def main():
    operation=check_request()
    ns=get_namespace()
    return stage(ns) if operation=="stage" else read(ns)

if __name__=="__main__":
    try:sys.exit(main())
    except ProbeError as exc:
        code=str(exc)
        if not re.fullmatch(r"[a-zA-Z0-9_]{3,88}",code):
            code="cloudflare_api_error"
        emit("vps_auth_probe","blocked",code=code)
        raise SystemExit(3)
