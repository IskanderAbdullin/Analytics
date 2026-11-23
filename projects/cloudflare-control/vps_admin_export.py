"""Restore a pre-existing VPS private WorkerEntrypoint as declared export.

The class/function already exists in the ACTIVE dedicated Worker source.
This operation only declares the missing named export; it inherits EVERY
existing binding, keeps the original source, and changes no Ubuntu service.
Run on public Analytics Actions with existing Cloudflare credentials.
Never expose actual Worker source, identifiers or secret values in public logs.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from serverspace_rebuild import (
    Cloudflare, TARGET, SafeError, decode_worker, encode_upload,
    fetch_version, get_versions
)

REQUEST=Path(__file__).with_name("vps_admin_export_request.json")
ADMIN="VpsAdminEntrypoint"
SPACE="ServerspaceReadOnlyEntrypoint"
REQUIRED={
    "VPS_AGENT_RELAY","VPS_AGENT_ENABLED","VPS_AGENT_DEVICE_ID",
    "VPS_AGENT_DEVICE_SECRET","VPS_AGENT_HMAC_SECRET","SERVERSPACE_API_KEY",
    "SERVERSPACE_API_ENABLED"
}

def emit(step,result,**kw):
    print(json.dumps({"stage":"vps_private_export","step":step,
                      "result":result,**kw},sort_keys=True),flush=True)

def mode():
    obj=json.loads(REQUEST.read_text(encoding="utf-8"))
    if (not isinstance(obj,dict) or
        set(obj)!={"schema_version","nonce","operation"} or
        obj.get("schema_version")!=1 or type(obj.get("nonce")) is not int or
        not 0<=obj["nonce"]<=2147483647 or
        obj.get("operation") not in ("dry_run","activate")):
        raise SafeError("INVALID_REQUEST")
    return obj["operation"]

def active_version(cf):
    h=cf.call("GET",TARGET+"/deployments")
    ds=h.get("deployments") if isinstance(h,dict) else h
    if not isinstance(ds,list) or not ds:
        raise SafeError("DEPLOYMENT_MISSING")
    versions=ds[0].get("versions") or []
    ids=[v.get("version_id") for v in versions if v.get("percentage")==100]
    if len(ids)!=1 or not isinstance(ids[0],str):
        raise SafeError("ACTIVE_VERSION_UNKNOWN")
    return ids[0]

def inspect(cf, version):
    v,exports,names=fetch_version(cf,version)
    if (not isinstance(exports,dict) or
        exports.get(SPACE,{}).get("type")!="worker" or
        "VpsAgentRelay" not in exports or not REQUIRED.issubset(names)):
        raise SafeError("DEDICATED_BASELINE_UNEXPECTED")
    bindings=(v.get("resources") or {}).get("bindings") or []
    if not isinstance(bindings,list) or len(names)!=len(bindings):
        raise SafeError("BINDINGS_DUPLICATED")
    return v,exports,set(names)

def source(cf):
    content,ctype,main_header=cf.call("GET",TARGET+"/content/v2",raw=True)
    modules,main=decode_worker(ctype,content,main_header)
    merged=b"\n".join(m.content for m in modules)
    if (b"VpsAdminEntrypoint" not in merged or
        b"privateAdminFetch" not in merged or
        b"ServerspaceReadOnlyEntrypoint" not in merged or
        b"/v1/vps/status" not in merged):
        raise SafeError("ADMIN_CLASS_NOT_IN_SOURCE")
    return modules,main

def main():
    op=mode()
    cf=Cloudflare()
    old=active_version(cf)
    current,exports,names=inspect(cf,old)
    modules,main_module=source(cf)
    if exports.get(ADMIN,{}).get("type")=="worker":
        emit("preflight","already_registered",binding_count=len(names))
        return 0
    emit("preflight","ready",binding_count=len(names),modules_count=len(modules),
         admin_class_in_source=True,source_code_unchanged=True)
    if op=="dry_run":return 0
    if active_version(cf)!=old:
        raise SafeError("CONCURRENT_DEPLOYMENT")
    meta_exports=dict(exports)
    meta_exports[ADMIN]={"type":"worker"}
    runtime=((current.get("resources") or {}).get("script_runtime") or {})
    date=str(runtime.get("compatibility_date") or "2026-11-22")[:10]
    metadata={
        "main_module":main_module,
        "compatibility_date":date,
        "bindings":[{"type":"inherit","name":name} for name in sorted(names)],
        "exports":meta_exports,
        "annotations":{"workers/message":"Restore named private VPS admin export"}
    }
    flags=runtime.get("compatibility_flags")
    if isinstance(flags,list):metadata["compatibility_flags"]=flags
    content,ctype=encode_upload(modules,main_module,metadata)
    cf.call("PUT",TARGET+"?bindings_inherit=strict",content,ctype)
    emit("upload","accepted")
    candidate=None
    for entry in get_versions(cf)[:10]:
        version=entry.get("id") if isinstance(entry,dict) else None
        if not isinstance(version,str):continue
        try:
            _,exp,after=inspect(cf,version)
        except SafeError:continue
        if exp==meta_exports and after==names:
            candidate=version
            break
    if not candidate:
        raise SafeError("VERSION_INTEGRITY_NOT_CONFIRMED")
    if active_version(cf)!=old:
        raise SafeError("CONCURRENT_ACTIVATION")
    cf.call("POST",TARGET+"/deployments",json.dumps({
        "strategy":"percentage",
        "versions":[{"version_id":candidate,"percentage":100}]
    }).encode("utf-8"),"application/json")
    if active_version(cf)!=candidate:
        raise SafeError("ACTIVATION_NOT_CONFIRMED")
    _,live_exports,live_names=inspect(cf,candidate)
    if (live_names!=names or live_exports!=meta_exports or
        live_exports.get(ADMIN,{}).get("type")!="worker"):
        raise SafeError("LIVE_INTEGRITY_FAILED")
    emit("activation","live",vps_admin_private_export=True,
         serverspace_export_preserved=True,relay_preserved=True,
         all_binding_names_preserved=True)

if __name__=="__main__":
    try:
        sys.exit(main())
    except SafeError as exc:
        code=str(exc)
        if not re.fullmatch(r"[A-Z0-9_]{3,72}",code):
            code="CLOUDFLARE_OPERATION_FAILED"
        emit("halt","blocked",code=code)
        sys.exit(3)
