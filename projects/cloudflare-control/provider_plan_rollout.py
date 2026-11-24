"""Read-only future VPS power planning in the existing private Serverspace entrypoint.

This script never sends Serverspace power API requests. It edits only the
existing privately bound WorkerEntryPoint route to call its already-proven
read-only list provider. Public default WSS route and existing OAuth/DO/HMAC
bindings, exports and secrets are strictly preserved.

GitHub Actions dry_run by default. Raw deployed code and account identifiers
stay exclusively in ephemeral runner memory; only safe structural outcomes
are printed in public logs.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from serverspace_rebuild import (Cloudflare, TARGET, SafeError, decode_worker,
                                 encode_upload, fetch_version, get_versions)

REQ=Path(__file__).with_name("provider_plan_request.json")
ROUTE="/internal/serverspace/power-plan"
MARK="__serverspacePrivatePowerPlanV1"
REQUIRED={"SERVERSPACE_API_ENABLED","SERVERSPACE_API_KEY",
          "VPS_AGENT_RELAY","VPS_AGENT_ENABLED","VPS_AGENT_DEVICE_ID",
          "VPS_AGENT_DEVICE_SECRET","VPS_AGENT_HMAC_SECRET"}
EXPECTED_EXPORTS={"VpsAgentRelay":"durable_object",
                  "VpsAdminEntrypoint":"worker",
                  "ServerspaceReadOnlyEntrypoint":"worker"}
# Strictly private and strictly read-only: the only network call here is
# the already deployed, fixed private function for inventory.
JS=r'''
async function __serverspacePrivatePowerPlanV1(request,env){
  const reply=(payload,status=200)=>new Response(JSON.stringify(payload),{
    status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"}
  });
  const failure=(code,status=400)=>reply({error:code},status);
  try{
    const u=new URL(request.url);
    if(u.pathname!=="/internal/serverspace/power-plan"||u.search||u.hash)
      return failure("NOT_FOUND",404);
    if(request.method!=="POST")return failure("METHOD_NOT_ALLOWED",405);
    if(Number(request.headers.get("content-length")||0)>2048)
      return failure("BODY_TOO_LARGE",413);
    const raw=await request.text();
    if(new TextEncoder().encode(raw).length>2048)return failure("BODY_TOO_LARGE",413);
    let input;
    try{input=JSON.parse(raw);}catch{return failure("INVALID_JSON");}
    if(!input||typeof input!=="object"||Array.isArray(input)||
       Object.keys(input).sort().join(",")!=="action,mode,target"||
       input.mode!=="plan"||input.target!=="sole"||
       typeof input.action!=="string"||
       !["on","shutdown","reboot","off","reset"].includes(input.action))
       return failure("INVALID_ARGUMENTS");
    // Call only the already reviewed provider GET /api/v1/servers via existing
    // private no-body function. Never call /power, no requests except list.
    const upstream=await serverspacePrivateFetch(
       new Request("http://serverspace.internal/internal/serverspace/list-servers",
                   {method:"POST"}),env);
    if(!upstream.ok)return failure("INVENTORY_UNAVAILABLE",502);
    if(!upstream.headers.get("content-type")?.toLowerCase().includes("application/json"))
       return failure("INVENTORY_SCHEMA",502);
    const json=await upstream.text();
    if(new TextEncoder().encode(json).length>128000)
       return failure("INVENTORY_TOO_LARGE",502);
    const payload=JSON.parse(json);
    if(!payload||!Array.isArray(payload.servers)||payload.servers.length!==1||
       payload.count!==1) return failure("TARGET_NOT_UNIQUE",409);
    const only=payload.servers[0];
    if(!only||typeof only!=="object"||typeof only.id!=="string"||
       !/^l[0-9]+s[0-9]+$/.test(only.id)||
       typeof only.is_power_on!=="boolean")
       return failure("TARGET_SCHEMA_INVALID",502);
    const on=only.is_power_on;
    if((input.action==="on"&&on)||
       (["off","shutdown"].includes(input.action)&&!on))
       return reply({state:"no_change",action:input.action,execution_enabled:false});
    if(["reboot","reset"].includes(input.action)&&!on)
       return failure("POWER_STATE_CONFLICT",409);
    return reply({state:"ready",action:input.action,
      method_if_authorized:"POST",hard_power:["off","reset"].includes(input.action),
      execution_enabled:false});
  }catch(_){return failure("PLAN_UNAVAILABLE",502);}
}
'''
class Halt(SafeError):
    pass

def emit(stage,outcome,**kw):
    print(json.dumps({"stage":"serverspace_private_power_plan",
                      "phase":stage,"outcome":outcome,**kw},sort_keys=True),flush=True)

def conf():
    obj=json.loads(REQ.read_text("utf-8"))
    if(not isinstance(obj,dict) or set(obj)!={"schema_version","nonce","operation"}
       or obj.get("schema_version")!=1 or type(obj.get("nonce")) is not int
       or not 0<=obj["nonce"]<=2147483647
       or obj.get("operation") not in ("dry_run","activate")):
       raise Halt("REQUEST_INVALID")
    return obj["operation"]

def deployed(cf):
    result=cf.call("GET",TARGET+"/deployments")
    deployments=result.get("deployments") if isinstance(result,dict) else result
    if not isinstance(deployments,list) or not deployments:
        raise Halt("DEPLOYMENTS_UNEXPECTED")
    ids=[v.get("version_id") for v in deployments[0].get("versions") or []
         if v.get("percentage")==100]
    if len(ids)!=1 or not isinstance(ids[0],str):
        raise Halt("ACTIVE_VERSION_UNKNOWN")
    return ids[0]

def baseline(cf,version):
    item,exports,names=fetch_version(cf,version)
    resources=(item or {}).get("resources") or {}
    bindings=resources.get("bindings") or []
    if(len(bindings)!=len(names) or not REQUIRED.issubset(names)
       or not all(exports.get(k,{}).get("type")==v
         for k,v in EXPECTED_EXPORTS.items())
       or len(names)<7):
       raise Halt("PRODUCTION_BASELINE_UNEXPECTED")
    if not isinstance(exports,dict):
       raise Halt("EXPORTS_UNEXPECTED")
    return item,exports,set(names)

def patch(cf):
    content,mime,head=cf.call("GET",TARGET+"/content/v2",raw=True)
    modules,main=decode_worker(mime,content,head)
    if not modules or len(modules)>2:
        raise Halt("MODULE_LAYOUT_UNEXPECTED")
    hits=[i for i,m in enumerate(modules) if m.filename==main]
    if len(hits)!=1:
        raise Halt("MAIN_MODULE_UNEXPECTED")
    index=hits[0]
    source=modules[index].content.decode("utf-8")
    # Idempotent safe exit if the new private plan already exists.
    if MARK in source:
        if ROUTE not in source:raise Halt("PARTIAL_DEPLOYMENT")
        return modules,main,False,source
    targets=list(re.finditer(r"\breturn\s+serverspacePrivateFetch\s*\(\s*(\w+)\s*,\s*this\.env\s*\)\s*;",source))
    emit("source_structure","observed",matching_dispatches=len(targets),
         class_name_present="ServerspaceReadOnlyEntrypoint" in source,
         handler_present="serverspacePrivateFetch" in source)
    if len(targets)!=1:
        raise Halt("PRIVATE_DISPATCH_ANCHOR_UNEXPECTED")
    match=targets[0]
    scope=source[max(0,match.start()-1600):match.start()]
    if "ServerspaceReadOnlyEntrypoint" not in scope or "fetch(" not in scope:
        raise Halt("PRIVATE_ENTRYPOINT_SCOPE_UNEXPECTED")
    arg=match.group(1)
    replacement=(f'if(new URL({arg}.url).pathname==="{ROUTE}")'
                 f' return {MARK}({arg},this.env);\n    '+match.group(0))
    updated=(source[:match.start()]+replacement+source[match.end():]
              +"\n"+JS)
    original=modules[index]
    modules[index]=original._replace(content=updated.encode("utf-8"))
    return modules,main,True,updated

def check_js(code):
    with tempfile.TemporaryDirectory() as tmp:
        file=Path(tmp)/"index.mjs"
        file.write_text(code,"utf-8")
        p=subprocess.run(["node","--check",str(file)],stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,timeout=30)
        if p.returncode:
            raise Halt("SYNTAX_FAILURE")

def main():
    op=conf()
    cf=Cloudflare()
    old=deployed(cf)
    info,exports,names=baseline(cf,old)
    modules,main_name,needed,source=patch(cf)
    check_js(source)
    emit("preflight","passed",patch_needed=needed,
         inherited_binding_count=len(names),private_export_count=len(exports),
         syntax_valid=True,public_route_unchanged=True,
         provider_power_request_possible=False)
    if op=="dry_run":
        return 0
    if not needed:
        emit("activation","already_present")
        return 0
    if deployed(cf)!=old:raise Halt("CONCURRENT_DEPLOYMENT")
    runtime=((info.get("resources") or {}).get("script_runtime") or {})
    day=str(runtime.get("compatibility_date") or "2026-11-22")[:10]
    meta={"main_module":main_name,"compatibility_date":day,
          "bindings":[{"type":"inherit","name":x} for x in sorted(names)],
          "exports":dict(exports),
          "annotations":{"workers/message":"Add private read-only Serverspace power planning"}}
    flags=runtime.get("compatibility_flags")
    if isinstance(flags,list):meta["compatibility_flags"]=flags
    body,ctype=encode_upload(modules,main_name,meta)
    cf.call("PUT",TARGET+"?bindings_inherit=strict",body,ctype)
    emit("upload","accepted")
    candidates=[]
    for entry in get_versions(cf)[:10]:
        vid=entry.get("id") if isinstance(entry,dict) else None
        if not isinstance(vid,str):continue
        try:
            _,exp,binding_names=baseline(cf,vid)
        except (Halt,SafeError):continue
        if exp==exports and binding_names==names:
            candidates.append(vid)
    active_now=deployed(cf)
    if active_now==old:
        # Uploaded immutable version needs explicit 100% activation.
        newest=next((x for x in get_versions(cf)[:10]
                     if isinstance(x,dict) and x.get("id") in candidates),None)
        if not newest:raise Halt("VERSION_NOT_CONFIRMED")
        candidate=newest["id"]
        cf.call("POST",TARGET+"/deployments",json.dumps({
          "strategy":"percentage",
          "versions":[{"version_id":candidate,"percentage":100}]
        }).encode("utf-8"),"application/json")
    elif active_now in candidates:
        candidate=active_now
        emit("activation","automatically_live")
    else:
        raise Halt("CONCURRENT_ACTIVATION")
    if deployed(cf)!=candidate:
        raise Halt("ACTIVATION_NOT_CONFIRMED")
    _,live_exports,live_names=baseline(cf,candidate)
    if live_exports!=exports or live_names!=names:
        raise Halt("POST_DEPLOYMENT_BINDINGS_CHANGED")
    _,_,requires_patch,live_source=patch(cf)
    if requires_patch or MARK not in live_source:
        raise Halt("POST_DEPLOYMENT_SOURCE_NOT_PRESENT")
    emit("activation","verified_live",owner_private_plan=True,
         all_bindings_preserved=True,all_exports_preserved=True,
         provider_mutation_path_absent=True)
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except (Halt,SafeError) as e:
        code=str(e)
        if not re.fullmatch("[A-Z0-9_]{3,80}",code):
            code="PROVIDER_PLAN_BLOCKED"
        emit("halt","blocked",code=code)
        sys.exit(3)
    except Exception:
        emit("halt","blocked",code="UNEXPECTED_FAILURE")
        sys.exit(3)
