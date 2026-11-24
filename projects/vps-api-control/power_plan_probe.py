"""End-to-end read-only provider power-plan proof through private Worker binding.

Reuses existing babit-ss-diagnostic-1123 + its KV. The provider API
requests remain GET only; 'reboot' is an action NAME in a dry plan, never
an executed command. Never store server ID, password, IP, hostname or API key.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from canary import WORKER, BRIDGE, KV_TITLE, ProbeError, api, multipart, emit

REQUEST=Path(__file__).with_name("power_plan_probe_request.json")
KEY="provider_plan_v1"
PLAN_EXPORT="ServerspacePowerPlanEntrypoint"
JS=r'''
export default {
  fetch() { return new Response("Not found",{status:404}); },
  async scheduled(event,env,ctx){
    ctx.waitUntil((async()=>{
      if(await env.PROBE_RESULTS.get("provider_plan_v1"))return;
      let result={schema_version:1,outcome:"plan_unavailable"};
      try{
        let decisions={};
        for(const action of ["on","reboot"]){
          const reply=await env.POWER_PLAN_SERVICE.fetch(
            "http://serverspace.internal/internal/serverspace/power-plan",
            {method:"POST",redirect:"manual",
             body:JSON.stringify({mode:"plan",action,target:"sole"}),
             headers:{"Content-Type":"application/json"},
             signal:AbortSignal.timeout(14000)});
          if(!reply.ok)throw new Error("private_plan_http_"+reply.status);
          if(!reply.headers.get("content-type")?.toLowerCase().includes("application/json"))
            throw new Error("invalid_content_type");
          const b=await reply.text();
          if(b.length>3000)throw new Error("response_too_large");
          const p=JSON.parse(b);
          if(!p || p.action!==action || p.execution_enabled!==false ||
             !["ready","no_change"].includes(p.state))
             throw new Error("unexpected_plan");
          decisions[action]=p.state;
        }
        result={schema_version:1,outcome:"read_only_plan_ok",
          on_decision:decisions.on,reboot_decision:decisions.reboot,
          execution_enabled:false};
      }catch(_){result={schema_version:1,outcome:"plan_unavailable"};}
      await env.PROBE_RESULTS.put("provider_plan_v1",JSON.stringify(result),
       {expirationTtl:result.outcome==="read_only_plan_ok"?3600:180});
    })());
  }
};
'''
def config():
    v=json.loads(REQUEST.read_text("utf-8"))
    if(not isinstance(v,dict) or set(v)!={"schema_version","nonce","operation"}
       or v["schema_version"]!=1 or type(v["nonce"]) is not int
       or not 0<=v["nonce"]<=2147483647 or v["operation"] not in ("stage","read")):
        raise ProbeError("request_invalid")
    return v["operation"]

def existing_kv():
    namespaces=api("GET","/storage/kv/namespaces?per_page=100")
    if not isinstance(namespaces,list):
        raise ProbeError("kv_schema")
    found=[x.get("id") for x in namespaces
           if isinstance(x,dict) and x.get("title")==KV_TITLE]
    if (len(found)!=1 or not isinstance(found[0],str) or
        not re.fullmatch(r"[0-9a-fA-F]{32}",found[0])):
        raise ProbeError("existing_kv_not_unique")
    return found[0]

def baseline(ns):
    base="/workers/scripts/"+WORKER
    settings=api("GET",base+"/settings")
    items=settings.get("bindings") if isinstance(settings,dict) else None
    if not isinstance(items,list):
        raise ProbeError("bindings_schema")
    b={x.get("name"):x for x in items if isinstance(x,dict)}
    originals={"PROBE_RESULTS","SERVERSPACE_SERVICE"}
    optional={"VPS_ADMIN_SERVICE","POWER_PLAN_SERVICE"}
    if(not originals.issubset(b) or
       not set(b).issubset(originals|optional) or len(b)!=len(items)):
        raise ProbeError("existing_probe_bindings_unexpected")
    if (b["PROBE_RESULTS"].get("type")!="kv_namespace" or
        b["PROBE_RESULTS"].get("namespace_id")!=ns):
        raise ProbeError("existing_probe_kv_changed")
    original=b["SERVERSPACE_SERVICE"]
    if(original.get("type")!="service" or original.get("service")!=BRIDGE
       or original.get("entrypoint")!="ServerspaceReadOnlyEntrypoint"):
        raise ProbeError("existing_inventory_binding_changed")
    if "VPS_ADMIN_SERVICE" in b:
        admin=b["VPS_ADMIN_SERVICE"]
        if(admin.get("type")!="service" or admin.get("service")!=BRIDGE
           or admin.get("entrypoint")!="VpsAdminEntrypoint"):
            raise ProbeError("existing_admin_binding_changed")
    if "POWER_PLAN_SERVICE" in b:
        plan=b["POWER_PLAN_SERVICE"]
        if(plan.get("type")!="service" or plan.get("service")!=BRIDGE
           or plan.get("entrypoint")!=PLAN_EXPORT):
            raise ProbeError("plan_binding_changed")
    return base,b

def plan_export_live():
    base="/workers/scripts/"+BRIDGE
    deployments=api("GET",base+"/deployments")
    items=deployments.get("deployments") if isinstance(deployments,dict) else deployments
    if not isinstance(items,list) or not items:
        raise ProbeError("main_worker_not_deployed")
    live=[x.get("version_id") for x in items[0].get("versions") or []
          if x.get("percentage")==100]
    if len(live)!=1 or not isinstance(live[0],str):
        raise ProbeError("main_version_not_unique")
    info=api("GET",base+"/versions/"+live[0])
    exports=((info.get("resources") or {}).get("script_runtime") or {}).get("exports") or {}
    if exports.get(PLAN_EXPORT,{}).get("type")!="worker":
        raise ProbeError("private_plan_export_not_live")

def stage(ns):
    plan_export_live()
    base,b=baseline(ns)
    current=api("GET",base+"/content/v2",raw=True)
    if b"provider_plan_v1" in current and "POWER_PLAN_SERVICE" in b:
        emit("private_plan","already_staged")
    else:
        if b"vps_admin_auth_probe_v1" not in current:
            raise ProbeError("diagnostic_source_unrecognized")
        binds=[
          {"type":"kv_namespace","name":"PROBE_RESULTS","namespace_id":ns},
          {"type":"service","name":"SERVERSPACE_SERVICE","service":BRIDGE,
           "entrypoint":"ServerspaceReadOnlyEntrypoint"},
          {"type":"service","name":"POWER_PLAN_SERVICE","service":BRIDGE,
           "entrypoint":PLAN_EXPORT}
        ]
        if "VPS_ADMIN_SERVICE" in b:
            binds.append({"type":"service","name":"VPS_ADMIN_SERVICE",
              "service":BRIDGE,"entrypoint":"VpsAdminEntrypoint"})
        body,mime=multipart({"main_module":"main.mjs",
           "compatibility_date":"2026-11-23","bindings":binds},JS)
        api("PUT",base,body,mime)
        after,b2=baseline(ns)
        if "POWER_PLAN_SERVICE" not in b2 or set(b)-set(b2):
            raise ProbeError("bindings_not_preserved")
        source=api("GET",base+"/content/v2",raw=True)
        if b"provider_plan_v1" not in source:
            raise ProbeError("probe_source_not_live")
        emit("private_plan","upload_confirmed",binding_count=len(b2))
    api("PUT",base+"/schedules",json.dumps([{"cron":"* * * * *"}]).encode())
    emit("private_plan","cron_scheduled",mutating_provider_api=False)
    return 0

def read(ns):
    base,b=baseline(ns)
    if "POWER_PLAN_SERVICE" not in b:
        raise ProbeError("plan_service_not_bound")
    try:
        obj=json.loads(api("GET","/storage/kv/namespaces/"+ns+"/values/"+KEY,
                           raw=True))
    except ProbeError as exc:
        if str(exc).startswith("http_404"):
            emit("private_plan","pending")
            return 5
        raise
    except (ValueError,TypeError):
        raise ProbeError("result_not_json")
    if not isinstance(obj,dict) or obj.get("schema_version")!=1:
        raise ProbeError("result_schema")
    if obj.get("outcome")!="read_only_plan_ok":
        emit("private_plan","unavailable")
        return 4
    if(set(obj)!={"schema_version","outcome","on_decision",
                 "reboot_decision","execution_enabled"} or
       obj["on_decision"] not in ("ready","no_change") or
       obj["reboot_decision"] not in ("ready","no_change") or
       obj["execution_enabled"] is not False):
        raise ProbeError("result_unexpected")
    emit("private_plan","real_api_plan_ok",
         on_decision=obj["on_decision"],reboot_decision=obj["reboot_decision"],
         execution_enabled=False)
    api("PUT",base+"/schedules",json.dumps([]).encode())
    emit("private_plan","cron_disabled_after_success")
    return 0

def main():
    op=config()
    ns=existing_kv()
    return stage(ns) if op=="stage" else read(ns)

if __name__=="__main__":
    try:
        sys.exit(main())
    except ProbeError as exc:
        code=str(exc)
        if not re.fullmatch(r"[a-zA-Z0-9_]{3,90}",code):
            code="api_unavailable"
        emit("private_plan","blocked",code=code)
        sys.exit(3)
