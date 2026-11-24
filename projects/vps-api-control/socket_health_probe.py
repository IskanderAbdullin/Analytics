"""Read only private DO device WebSocket ready-state counts, no IDs.

Reuses existing diagnostic Cloudflare Worker and KV. No shell command,
no device secret, no WebSocket close, no VPS power mutation. Read-only
same-account Service binding to the newly staged private diagnostic export.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from canary import WORKER, BRIDGE, KV_TITLE, ProbeError, api, multipart, emit

REQ=Path(__file__).with_name("socket_health_probe_request.json")
KEY="vps_socket_samples_v1"
ENTRY="VpsSocketHealthEntrypoint"
SAMPLE_TARGET=4
JS=r'''
const STORAGE_KEY="vps_socket_samples_v1";
const MAX_SAMPLES=4;
const MAX_ATTEMPTS=8;
export default {
  fetch(){return new Response("Not found",{status:404});},
  async scheduled(event,env,ctx){
    ctx.waitUntil((async()=>{
      let state=await env.PROBE_RESULTS.get(STORAGE_KEY,"json");
      if(!state || state.schema_version!==1 || !Array.isArray(state.samples) ||
         !Number.isInteger(state.attempts) || state.attempts<0 ||
         state.samples.length>MAX_SAMPLES || state.attempts>MAX_ATTEMPTS)
        state={schema_version:1,attempts:0,samples:[],errors:0};
      if(state.samples.length>=MAX_SAMPLES || state.attempts>=MAX_ATTEMPTS)
        return;
      state.attempts++;
      try{
        const res=await env.VPS_SOCKET_SERVICE.fetch(
          "http://vps.internal/internal/vps/socket-health",
          {method:"GET",redirect:"manual",signal:AbortSignal.timeout(10000)});
        if(!res.ok)throw new Error("private_http");
        if(!res.headers.get("content-type")?.toLowerCase().includes("application/json"))
          throw new Error("bad_content_type");
        const raw=await res.text();
        if(raw.length>1000)throw new Error("response_too_large");
        const data=JSON.parse(raw);
        const fields=["open","closing","closed","other","total"];
        if(!data || typeof data!=="object" ||
           Object.keys(data).sort().join(",")!==[...fields].sort().join(",")||
           !fields.every(k=>Number.isInteger(data[k])&&data[k]>=0&&data[k]<=1000)||
           data.open+data.closing+data.closed+data.other!==data.total)
          throw new Error("invalid_schema");
        state.samples.push({open:data.open,closing:data.closing,
          closed:data.closed,other:data.other,total:data.total});
      }catch(_){state.errors++;}
      await env.PROBE_RESULTS.put(STORAGE_KEY,JSON.stringify(state),
         {expirationTtl:3600});
    })());
  }
};
'''
def request_mode():
    obj=json.loads(REQ.read_text("utf-8"))
    if(not isinstance(obj,dict) or set(obj)!={"schema_version","nonce","operation"}
       or obj.get("schema_version")!=1 or type(obj.get("nonce")) is not int
       or not 0<=obj["nonce"]<=2147483647 or obj.get("operation") not in
          ("dry_run","stage","read")):
        raise ProbeError("invalid_request")
    return obj["operation"]

def existing_ns():
    names=api("GET","/storage/kv/namespaces?per_page=100")
    if not isinstance(names,list):
        raise ProbeError("kv_response_invalid")
    ids=[r.get("id") for r in names if isinstance(r,dict)
         and r.get("title")==KV_TITLE]
    if len(ids)!=1 or not isinstance(ids[0],str) or not re.fullmatch(r"[0-9a-fA-F]{32}",ids[0]):
        raise ProbeError("kv_namespace_not_unique")
    return ids[0]

def existing_worker(ns):
    base="/workers/scripts/"+WORKER
    info=api("GET",base+"/settings")
    bindings=info.get("bindings") if isinstance(info,dict) else None
    if not isinstance(bindings,list):
        raise ProbeError("worker_bindings_invalid")
    by={x.get("name"):x for x in bindings if isinstance(x,dict)}
    original={"SERVERSPACE_SERVICE","PROBE_RESULTS"}
    optional={"VPS_ADMIN_SERVICE","POWER_PLAN_SERVICE","VPS_SOCKET_SERVICE"}
    if(not original.issubset(by) or not set(by).issubset(original|optional)
       or len(by)!=len(bindings)):
        raise ProbeError("worker_bindings_unexpected")
    kv=by["PROBE_RESULTS"]
    inventory=by["SERVERSPACE_SERVICE"]
    if(kv.get("type")!="kv_namespace" or kv.get("namespace_id")!=ns
       or inventory.get("type")!="service" or inventory.get("service")!=BRIDGE
       or inventory.get("entrypoint")!="ServerspaceReadOnlyEntrypoint"):
        raise ProbeError("worker_baseline_modified")
    for key,exp in [("VPS_ADMIN_SERVICE","VpsAdminEntrypoint"),
                    ("POWER_PLAN_SERVICE","ServerspacePowerPlanEntrypoint"),
                    ("VPS_SOCKET_SERVICE",ENTRY)]:
        if key in by:
            v=by[key]
            if(v.get("type")!="service" or v.get("service")!=BRIDGE
               or v.get("entrypoint")!=exp):
                raise ProbeError("existing_private_binding_changed")
    return base,by

def export_live():
    base="/workers/scripts/"+BRIDGE
    hist=api("GET",base+"/deployments")
    rows=hist.get("deployments") if isinstance(hist,dict) else hist
    if not isinstance(rows,list) or not rows:
        raise ProbeError("main_deployment_missing")
    matches=[v.get("version_id") for v in rows[0].get("versions") or []
             if v.get("percentage")==100]
    if len(matches)!=1 or not isinstance(matches[0],str):
        raise ProbeError("main_version_unexpected")
    info=api("GET",base+"/versions/"+matches[0])
    exports=((info.get("resources") or {}).get("script_runtime") or {}).get("exports") or {}
    if exports.get(ENTRY,{}).get("type")!="worker":
        raise ProbeError("socket_health_entry_not_live")

def stage(ns):
    export_live()
    base,bindings=existing_worker(ns)
    raw=api("GET",base+"/content/v2",raw=True)
    if b"vps_socket_samples_v1" in raw and "VPS_SOCKET_SERVICE" in bindings:
        emit("private_socket","already_staged")
    else:
        if b"provider_plan_v1" not in raw:
            raise ProbeError("unexpected_diagnostic_source")
        all_bind=[
          {"type":"kv_namespace","name":"PROBE_RESULTS","namespace_id":ns},
          {"type":"service","name":"SERVERSPACE_SERVICE","service":BRIDGE,
           "entrypoint":"ServerspaceReadOnlyEntrypoint"},
          {"type":"service","name":"VPS_SOCKET_SERVICE","service":BRIDGE,
           "entrypoint":ENTRY}
        ]
        for key,name in [("VPS_ADMIN_SERVICE","VpsAdminEntrypoint"),
                         ("POWER_PLAN_SERVICE","ServerspacePowerPlanEntrypoint")]:
            if key in bindings:
                all_bind.append({"type":"service","name":key,
                   "service":BRIDGE,"entrypoint":name})
        body,ctype=multipart({"main_module":"main.mjs",
          "compatibility_date":"2026-11-23","bindings":all_bind},JS)
        api("PUT",base,body,ctype)
        _,after=existing_worker(ns)
        if "VPS_SOCKET_SERVICE" not in after or not set(bindings).issubset(after):
            raise ProbeError("original_bindings_lost")
        if b"vps_socket_samples_v1" not in api("GET",base+"/content/v2",raw=True):
            raise ProbeError("diagnostic_script_not_live")
        emit("private_socket","script_accepted",binding_count=len(after))
    api("PUT",base+"/schedules",json.dumps([{"cron":"* * * * *"}]).encode())
    emit("private_socket","cron_scheduled",no_credentials=True)
    return 0

def read(ns):
    base,bindings=existing_worker(ns)
    if "VPS_SOCKET_SERVICE" not in bindings:
        raise ProbeError("socket_binding_unavailable")
    try:
        payload=json.loads(api("GET","/storage/kv/namespaces/"+ns+
                               "/values/"+KEY,raw=True))
    except ProbeError as exc:
        if str(exc).startswith("http_404"):
            emit("private_socket","pending")
            return 5
        raise
    except (ValueError,TypeError):
        raise ProbeError("probe_invalid_json")
    if not isinstance(payload,dict) or payload.get("schema_version")!=1:
        raise ProbeError("probe_schema")
    attempts=payload.get("attempts")
    samples=payload.get("samples")
    errors=payload.get("errors")
    if(type(attempts) is not int or not 0<=attempts<=8 or
       type(errors) is not int or not 0<=errors<=8 or
       not isinstance(samples,list) or not 0<=len(samples)<=SAMPLE_TARGET):
        raise ProbeError("probe_counts_invalid")
    series=[]
    for row in samples:
        if(not isinstance(row,dict) or set(row)!={"open","closing","closed","other","total"}
           or any(type(row[k]) is not int or not 0<=row[k]<=1000 for k in row)
           or sum(row[k] for k in ("open","closing","closed","other"))!=row["total"]):
            raise ProbeError("sample_invalid")
        series.append(row)
    if len(series)<SAMPLE_TARGET and attempts<8:
        emit("private_socket","collecting",attempts=attempts,
             valid_samples=len(series),errors=errors)
        return 5
    if series:
        values=[x["open"] for x in series]
        emit("private_socket","sample_complete",valid_samples=len(series),
             attempts=attempts,errors=errors,
             min_open=min(values),max_open=max(values),
             mean_open=round(sum(values)/len(values),2),
             min_total=min(x["total"] for x in series),
             max_total=max(x["total"] for x in series))
    else:
        emit("private_socket","sample_no_success",attempts=attempts,errors=errors)
    api("PUT",base+"/schedules",json.dumps([]).encode())
    emit("private_socket","cron_disabled_after_completion")
    return 0 if len(series)==SAMPLE_TARGET else 4

def main():
    op=request_mode()
    ns=existing_ns()
    if op=="dry_run":
        base,b=existing_worker(ns)
        raw=api("GET",base+"/content/v2",raw=True)
        emit("private_socket","preflight",existing_bindings=len(b),
             plan_probe_present=b"provider_plan_v1" in raw)
        return 0
    return stage(ns) if op=="stage" else read(ns)

if __name__=="__main__":
    try:
        sys.exit(main())
    except ProbeError as exc:
        code=str(exc)
        if not re.fullmatch(r"[a-zA-Z0-9_]{3,90}",code):
            code="api_unavailable"
        emit("private_socket","blocked",code=code)
        sys.exit(3)
