"""Add an isolated, fixed, read-only Serverspace power plan WorkerEntrypoint.

No modification of existing public fetch, OAuth, VPS WSS, Durable Object,
original Serverspace inventory entrypoint or bindings. New private named
export is read-only: the ONLY provider call is GET /api/v1/servers.
No actual provider power POST is possible in the uploaded source patch.

Production source bytes and all Cloudflare credentials stay exclusively inside
the ephemeral GitHub Actions runner, not this public repository.
"""
from __future__ import annotations

import dataclasses
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from serverspace_rebuild import (Cloudflare, TARGET, SafeError, decode_worker,
                                 encode_upload, fetch_version, get_versions)

REQ=Path(__file__).with_name("provider_plan_request.json")
ENTRY="ServerspacePowerPlanEntrypoint"
MARK="__serverspacePrivatePowerPlanV2"
REQUIRED={"SERVERSPACE_API_ENABLED","SERVERSPACE_API_KEY",
          "VPS_AGENT_RELAY","VPS_AGENT_ENABLED","VPS_AGENT_DEVICE_ID",
          "VPS_AGENT_DEVICE_SECRET","VPS_AGENT_HMAC_SECRET"}
JS=r'''
// Separate named private Cloudflare entrypoint; no default fetch route changed.
// This component has NO provider POST, shell, restart or mutation operation.
import { WorkerEntrypoint as __ServerspacePrivatePlanBase } from "cloudflare:workers";
async function __serverspacePrivatePowerPlanV2(request,env){
  const reply=(data,status=200)=>new Response(JSON.stringify(data),{
    status,headers:{"Content-Type":"application/json; charset=utf-8",
                    "Cache-Control":"no-store"}
  });
  const fail=(code,status=400)=>reply({error:code},status);
  try{
    const u=new URL(request.url);
    if(u.pathname!=="/internal/serverspace/power-plan"||u.search||u.hash)
      return fail("NOT_FOUND",404);
    if(request.method!=="POST")return fail("METHOD_NOT_ALLOWED",405);
    if(env.SERVERSPACE_API_ENABLED!=="true"||
       typeof env.SERVERSPACE_API_KEY!=="string"||
       env.SERVERSPACE_API_KEY.length<16)return fail("NOT_CONFIGURED",503);
    if(Number(request.headers.get("content-length")||0)>2048)
      return fail("BODY_TOO_LARGE",413);
    const raw=await request.text();
    if(new TextEncoder().encode(raw).length>2048)
      return fail("BODY_TOO_LARGE",413);
    let input;
    try{input=JSON.parse(raw);}catch{return fail("INVALID_JSON");}
    if(!input||typeof input!=="object"||Array.isArray(input)||
       Object.keys(input).sort().join(",")!=="action,mode,target"||
       input.mode!=="plan"||input.target!=="sole"||
       typeof input.action!=="string"||
       !["on","shutdown","reboot","off","reset"].includes(input.action))
      return fail("INVALID_ARGUMENTS");
    // Only read the owner's inventory; NEVER call Serverspace /power.
    const res=await fetch("https://api.serverspace.ru/api/v1/servers",{
      method:"GET",redirect:"manual",
      headers:{"X-API-KEY":env.SERVERSPACE_API_KEY,"Accept":"application/json"},
      signal:AbortSignal.timeout(8000)});
    if(res.status===401||res.status===403)
      return fail("PROVIDER_AUTH_DENIED",502);
    if(res.status===429)
      return fail("PROVIDER_THROTTLED",503);
    if(!res.ok)return fail("PROVIDER_UNAVAILABLE",502);
    if(!res.headers.get("content-type")?.toLowerCase().includes("application/json"))
      return fail("INVENTORY_SCHEMA",502);
    if(Number(res.headers.get("content-length")||0)>128000)
      return fail("INVENTORY_TOO_LARGE",502);
    const rawInventory=await res.text();
    if(new TextEncoder().encode(rawInventory).length>128000)
      return fail("INVENTORY_TOO_LARGE",502);
    const data=JSON.parse(rawInventory);
    if(!data||!Array.isArray(data.servers)||data.servers.length!==1)
      return fail("TARGET_NOT_UNIQUE",409);
    const server=data.servers[0];
    if(!server||typeof server!=="object"||typeof server.id!=="string"||
       !/^l[0-9]+s[0-9]+$/.test(server.id)||
       typeof server.is_power_on!=="boolean")
      return fail("TARGET_SCHEMA_INVALID",502);
    const on=server.is_power_on,act=input.action;
    if((act==="on"&&on)||
       ((act==="off"||act==="shutdown")&&!on))
      return reply({state:"no_change",action:act,execution_enabled:false});
    if((act==="reboot"||act==="reset")&&!on)
      return fail("POWER_STATE_CONFLICT",409);
    return reply({state:"ready",action:act,method_if_authorized:"POST",
                  hard_power:act==="off"||act==="reset",
                  execution_enabled:false});
  }catch(_){return fail("PLAN_UNAVAILABLE",502);}
}
export class ServerspacePowerPlanEntrypoint extends __ServerspacePrivatePlanBase {
  fetch(request){return __serverspacePrivatePowerPlanV2(request,this.env);}
}
'''
class Halt(SafeError):
    pass

def emit(phase,outcome,**kw):
    print(json.dumps({"stage":"serverspace_private_power_plan",
                      "phase":phase,"outcome":outcome,**kw},sort_keys=True),flush=True)

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
       or "VpsAgentRelay" not in exports
       or not all(exports.get(k,{}).get("type")=="worker"
           for k in ("VpsAdminEntrypoint","ServerspaceReadOnlyEntrypoint"))
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
    ix=hits[0]
    source=modules[ix].content.decode("utf-8")
    # No source-specific regex replacement or changes to prior functions.
    if MARK in source:
        if ENTRY not in source:
            raise Halt("PARTIAL_SOURCE_UNEXPECTED")
        return modules,main,False,source
    if "ServerspaceReadOnlyEntrypoint" not in source or "VpsAdminEntrypoint" not in source:
        raise Halt("PREVIOUS_ENTRYPOINTS_NOT_FOUND")
    updated=source.rstrip()+"\n"+JS+"\n"
    old=modules[ix]
    if hasattr(old,"_replace"):
        modules[ix]=old._replace(content=updated.encode("utf-8"))
    elif dataclasses.is_dataclass(old):
        modules[ix]=dataclasses.replace(old,content=updated.encode("utf-8"))
    else:
        raise Halt("MODULE_UPDATE_UNSUPPORTED")
    return modules,main,True,updated

def check_js(source):
    with tempfile.TemporaryDirectory() as tmp:
        file=Path(tmp)/"index.mjs"
        file.write_text(source,"utf-8")
        p=subprocess.run(["node","--check",str(file)],stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,timeout=30)
        if p.returncode:
            raise Halt("SYNTAX_FAILURE")

def main():
    mode=conf()
    cf=Cloudflare()
    old=deployed(cf)
    info,exports,names=baseline(cf,old)
    modules,main_name,needed,source=patch(cf)
    check_js(source)
    if ENTRY in exports and exports[ENTRY].get("type")!="worker":
        raise Halt("ENTRYPOINT_NAME_CONFLICT")
    if (not needed) != (ENTRY in exports):
        raise Halt("SOURCE_METADATA_MISMATCH")
    emit("preflight","passed",patch_needed=needed,
         inherited_binding_count=len(names),old_export_count=len(exports),
         syntax_valid=True,public_route_unchanged=True,
         provider_mutation_path_absent=True)
    if mode=="dry_run":
        return 0
    if not needed:
        emit("activation","already_live")
        return 0
    if deployed(cf)!=old:
        raise Halt("CONCURRENT_DEPLOYMENT")
    runtime=((info.get("resources") or {}).get("script_runtime") or {})
    day=str(runtime.get("compatibility_date") or "2026-11-22")[:10]
    new_exports=dict(exports)
    new_exports[ENTRY]={"type":"worker"}
    meta={"main_module":main_name,"compatibility_date":day,
          "bindings":[{"type":"inherit","name":x} for x in sorted(names)],
          "exports":new_exports,
          "annotations":{"workers/message":"Private read-only Serverspace power planning"}}
    flags=runtime.get("compatibility_flags")
    if isinstance(flags,list):
        meta["compatibility_flags"]=flags
    body,ctype=encode_upload(modules,main_name,meta)
    cf.call("PUT",TARGET+"?bindings_inherit=strict",body,ctype)
    emit("upload","accepted")
    candidates=[]
    for entry in get_versions(cf)[:10]:
        vid=entry.get("id") if isinstance(entry,dict) else None
        if not isinstance(vid,str):
            continue
        try:
            _,exp,binding_names=baseline(cf,vid)
        except (Halt,SafeError):
            continue
        if exp==new_exports and binding_names==names:
            candidates.append(vid)
    active_now=deployed(cf)
    if active_now==old:
        if not candidates:
            raise Halt("NEW_VERSION_NOT_CONFIRMED")
        candidate=candidates[0]
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
    if live_exports!=new_exports or live_names!=names:
        raise Halt("BINDINGS_OR_EXPORTS_LOST")
    _,_,still_missing,live_source=patch(cf)
    if still_missing or MARK not in live_source:
        raise Halt("SOURCE_VERIFY_FAILED")
    emit("activation","verified_live",private_readonly_plan=True,
         all_bindings_preserved=True,all_original_exports_preserved=True,
         live_provider_power_calls_possible=False)
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except (Halt,SafeError) as exc:
        code=str(exc)
        if not re.fullmatch(r"[A-Z0-9_]{3,80}",code):
            code="PROVIDER_PLAN_BLOCKED"
        emit("halt","blocked",code=code)
        sys.exit(3)
    except Exception:
        emit("halt","blocked",code="UNEXPECTED_FAILURE")
        sys.exit(3)
