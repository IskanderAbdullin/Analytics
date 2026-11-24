"""Source-preserving, no-secret private socket-count introspection.

Adds one named private WorkerEntrypoint to an EXISTING Worker and a
strict read-only DO fetch branch, while preserving all original Worker
source, WSS auth/reconnect handling, Secrets, bindings and exports.
Never closes or changes a socket. Dry run by default. Requires separately
audited same-account Cloudflare Service binding for calling private route.
"""
from __future__ import annotations

import dataclasses
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from serverspace_rebuild import (Cloudflare,TARGET,SafeError,decode_worker,
                                 encode_upload,fetch_version,get_versions)

REQUEST=Path(__file__).with_name("socket_health_rollout_request.json")
ENTRY="VpsSocketHealthEntrypoint"
MARK="__privateVpsSocketHealthV1"
REQUIRED={"SERVERSPACE_API_KEY","SERVERSPACE_API_ENABLED",
  "VPS_AGENT_RELAY","VPS_AGENT_ENABLED","VPS_AGENT_DEVICE_ID",
  "VPS_AGENT_DEVICE_SECRET","VPS_AGENT_HMAC_SECRET"}
PRESERVE=("VpsAgentRelay","VpsAdminEntrypoint",
  "ServerspaceReadOnlyEntrypoint","ServerspacePowerPlanEntrypoint")
JS=r'''
// A separate private name, not the original public Worker HTTP handler.
// Never inspects, logs, closes or mutates socket sessions or secrets.
import {WorkerEntrypoint as __PrivateVpsSocketBase} from "cloudflare:workers";
const __privateVpsSocketHealthPath="/internal/vps/socket-health";
const __originalVpsRelayFetch=VpsAgentRelay.prototype.fetch;
if(typeof __originalVpsRelayFetch==="function"){
  VpsAgentRelay.prototype.fetch=function(request){
    const u=new URL(request.url);
    if(u.pathname===__privateVpsSocketHealthPath){
      if(request.method!=="GET"||u.search||u.hash)
        return new Response(null,{status:405});
      try{
        const sockets=this.state.getWebSockets("device");
        let open=0,closing=0,closed=0,other=0;
        for(const socket of sockets){
          if(socket.readyState===1)open++;
          else if(socket.readyState===2)closing++;
          else if(socket.readyState===3)closed++;
          else other++;
        }
        return new Response(JSON.stringify({
          open,closing,closed,other,total:sockets.length
        }),{headers:{"Content-Type":"application/json; charset=utf-8",
                    "Cache-Control":"no-store"}});
      }catch(_){return new Response(null,{status:502});}
    }
    return __originalVpsRelayFetch.call(this,request);
  };
}
export class VpsSocketHealthEntrypoint extends __PrivateVpsSocketBase{
  async fetch(request){
    const u=new URL(request.url);
    if(u.pathname!==__privateVpsSocketHealthPath||u.search||u.hash)
      return new Response(null,{status:404});
    if(request.method!=="GET")return new Response(null,{status:405});
    const env=this.env;
    if(!env.VPS_AGENT_RELAY||env.VPS_AGENT_ENABLED!=="true"||
       typeof env.VPS_AGENT_DEVICE_ID!=="string"||
       !env.VPS_AGENT_DEVICE_ID.length)return new Response(null,{status:503});
    try{
      const id=env.VPS_AGENT_RELAY.idFromName(env.VPS_AGENT_DEVICE_ID);
      const obj=env.VPS_AGENT_RELAY.get(id);
      const response=await obj.fetch(
        new Request("http://internal.private/internal/vps/socket-health",{method:"GET"}));
      // Only statuses + fixed numeric counters, no remote raw error forwarding.
      if(!response.ok)return new Response(null,{status:response.status});
      if(!response.headers.get("content-type")?.toLowerCase().includes("application/json"))
        return new Response(null,{status:502});
      const raw=await response.text();
      if(raw.length>1000)return new Response(null,{status:502});
      const data=JSON.parse(raw);
      const fields=["open","closing","closed","other","total"];
      if(!data||typeof data!=="object"||Object.keys(data).sort().join(",")!==
          [...fields].sort().join(","))
        return new Response(null,{status:502});
      if(!fields.every(k=>Number.isInteger(data[k])&&data[k]>=0&&data[k]<=1000)||
         data.open+data.closing+data.closed+data.other!==data.total)
        return new Response(null,{status:502});
      return new Response(JSON.stringify(data),{
        headers:{"Content-Type":"application/json; charset=utf-8",
                 "Cache-Control":"no-store"}});
    }catch(_){return new Response(null,{status:502});}
  }
}
'''
class Halt(SafeError):pass
def emit(stage,outcome,**kw):
    print(json.dumps({"stage":"private_vps_socket_inspection",
      "phase":stage,"outcome":outcome,**kw},sort_keys=True),flush=True)

def operation():
    conf=json.loads(REQUEST.read_text("utf-8"))
    if(not isinstance(conf,dict) or set(conf)!={"schema_version","nonce","operation"}
       or conf["schema_version"]!=1 or type(conf["nonce"]) is not int
       or not 0<=conf["nonce"]<=2147483647
       or conf["operation"] not in ("dry_run","activate")):
        raise Halt("REQUEST_INVALID")
    return conf["operation"]

def current_version(cf):
    status=cf.call("GET",TARGET+"/deployments")
    items=status.get("deployments") if isinstance(status,dict) else status
    if not isinstance(items,list) or not items:
        raise Halt("DEPLOYMENT_MISSING")
    active=[v.get("version_id") for v in items[0].get("versions") or []
            if v.get("percentage")==100]
    if len(active)!=1 or not isinstance(active[0],str):
        raise Halt("ACTIVE_VERSION_UNEXPECTED")
    return active[0]

def evidence(cf,vid):
    item,exports,names=fetch_version(cf,vid)
    bindings=((item.get("resources") or {}).get("bindings") or [])
    if(not isinstance(exports,dict) or len(names)!=len(bindings)
       or not REQUIRED.issubset(names)
       or "VpsAgentRelay" not in exports
       or not all(exports.get(k,{}).get("type")=="worker" for k in PRESERVE[1:])):
        raise Halt("EXISTING_RUNTIME_UNEXPECTED")
    return item,exports,set(names)

def patched_source(cf):
    blob,mime,head=cf.call("GET",TARGET+"/content/v2",raw=True)
    modules,main=decode_worker(mime,blob,head)
    found=[i for i,m in enumerate(modules) if m.filename==main]
    if len(found)!=1 or not modules or len(modules)>2:
        raise Halt("SCRIPT_LAYOUT_UNEXPECTED")
    i=found[0]
    source=modules[i].content.decode("utf-8")
    if MARK in source:
        if ENTRY not in source:
            raise Halt("SOURCE_PARTIALLY_PATCHED")
        return modules,main,False,source
    # Require a true local lexical binding. We never patch an unknown class.
    local=bool(re.search(
      r"\b(?:var|let|const)\s+VpsAgentRelay\s*=\s*class\b|\bclass\s+VpsAgentRelay\b",
      source))
    has_websockets="getWebSockets" in source and "vps-agent/device" in source
    has_plan="__serverspacePrivatePowerPlanV2" in source
    emit("source_structure","observed",local_class=local,
         websocket_api_present=has_websockets,prior_plan_preserved=has_plan)
    if not local or not has_websockets or not has_plan:
        raise Halt("RUNTIME_COMPATIBILITY_UNCONFIRMED")
    after=source.rstrip()+"\n"+JS+"\n"
    old=modules[i]
    if hasattr(old,"_replace"):
        modules[i]=old._replace(content=after.encode("utf-8"))
    elif dataclasses.is_dataclass(old):
        modules[i]=dataclasses.replace(old,content=after.encode("utf-8"))
    else:
        raise Halt("MODULE_REPLACE_UNSUPPORTED")
    return modules,main,True,after

def syntax(code):
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/"worker.mjs"
        p.write_text(code,"utf-8")
        r=subprocess.run(["node","--check",str(p)],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        if r.returncode:raise Halt("SYNTAX_FAILED")

def main():
    mode=operation()
    cf=Cloudflare()
    active=current_version(cf)
    item,exports,names=evidence(cf,active)
    modules,mainfile,needed,code=patched_source(cf)
    syntax(code)
    if ENTRY in exports and exports[ENTRY].get("type")!="worker":
        raise Halt("EXPORT_NAME_COLLISION")
    if (not needed)!=(ENTRY in exports):
        raise Halt("EXPORT_CODE_MISMATCH")
    emit("preflight","passed",code_addition_needed=needed,
         bindings_preserved_count=len(names),old_exports_count=len(exports),
         syntax_valid=True,public_fetch_unchanged=True,
         no_socket_closures_in_patch=True,no_vps_operations=True)
    if mode=="dry_run":return 0
    if not needed:
        emit("activation","already_live")
        return 0
    if current_version(cf)!=active:
        raise Halt("CONCURRENT_DEPLOYMENT")
    runtime=((item.get("resources") or {}).get("script_runtime") or {})
    meta={"main_module":mainfile,
          "compatibility_date":str(runtime.get("compatibility_date") or "2026-11-22")[:10],
          "bindings":[{"type":"inherit","name":n} for n in sorted(names)],
          "exports":{**exports,ENTRY:{"type":"worker"}},
          "annotations":{"workers/message":"Add private read-only DO socket counts"}}
    flags=runtime.get("compatibility_flags")
    if isinstance(flags,list):
        meta["compatibility_flags"]=flags
    data,ctype=encode_upload(modules,mainfile,meta)
    cf.call("PUT",TARGET+"?bindings_inherit=strict",data,ctype)
    emit("upload","accepted")
    candidate=None
    for version in get_versions(cf)[:10]:
        vid=version.get("id") if isinstance(version,dict) else None
        if not isinstance(vid,str):continue
        try:
            _,exp,nn=evidence(cf,vid)
        except SafeError:continue
        if exp==meta["exports"] and nn==names:
            candidate=vid
            break
    if not candidate:raise Halt("UPLOADED_VERSION_NOT_FOUND")
    after=current_version(cf)
    if after==active:
        cf.call("POST",TARGET+"/deployments",json.dumps({
          "strategy":"percentage","versions":[{"version_id":candidate,"percentage":100}]
        }).encode(),"application/json")
    elif after==candidate:
        emit("activation","automatically_live")
    else:
        raise Halt("CONCURRENT_ACTIVATION")
    if current_version(cf)!=candidate:
        raise Halt("DEPLOYMENT_VERIFY_FAILED")
    _,new_exports,new_names=evidence(cf,candidate)
    if new_exports!=meta["exports"] or new_names!=names:
        raise Halt("RUNTIME_METADATA_LOST")
    _,_,still_unpatched,new_code=patched_source(cf)
    if still_unpatched or MARK not in new_code:
        raise Halt("SOURCE_NOT_LIVE")
    emit("activation","verified_live",only_private_diagnostic_added=True,
         original_bindings_and_exports_preserved=True)
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except (Halt,SafeError) as ex:
        code=str(ex)
        if not re.fullmatch(r"[A-Z0-9_]{3,80}",code):
            code="INSPECTION_BLOCKED"
        emit("halt","blocked",code=code)
        sys.exit(3)
    except Exception:
        emit("halt","blocked",code="UNEXPECTED_ERROR")
        sys.exit(3)
