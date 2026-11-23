"""Activate existing private Serverspace READ-ONLY flag with full inherited exports.

Uses the reviewed Cloudflare Workers source/version upload helper already
deployed successfully on this account. Works entirely in ephemeral GitHub
Actions; production Worker code and secret values never enter GitHub.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"cloudflare-control"))
from serverspace_rebuild import (Cloudflare, TARGET, MARKER, decode_worker,
                                 encode_upload, SafeError, get_versions, fetch_version)
from canary import emit, ProbeError

FLAG="SERVERSPACE_API_ENABLED"
ENTRY="ServerspaceReadOnlyEntrypoint"

def deployed(cf):
    records=cf.call("GET",TARGET+"/deployments")
    items=records.get("deployments") if isinstance(records,dict) else records
    if not isinstance(items,list) or not items: raise ProbeError("deployment_missing")
    version=next((v.get("version_id") for v in items[0].get("versions",[])
                  if v.get("percentage")==100),None)
    if not isinstance(version,str): raise ProbeError("active_version_missing")
    return version

def inspect(cf,version):
    v,exports,names=fetch_version(cf,version)
    if not isinstance(exports,dict) or exports.get(ENTRY,{}).get("type")!="worker":
        raise ProbeError("entrypoint_missing")
    if not {"SERVERSPACE_API_KEY","VPS_AGENT_RELAY"}.issubset(names):
        raise ProbeError("vps_binding_missing")
    if "VpsAgentRelay" not in exports: raise ProbeError("vps_export_missing")
    bindings=(v.get("resources") or {}).get("bindings") or []
    flag=next((b.get("text") or b.get("value") for b in bindings
               if isinstance(b,dict) and b.get("name")==FLAG),None)
    return v,exports,set(names),flag=="true"

def main():
    cf=Cloudflare()
    baseline=deployed(cf)
    current,old_exports,old_names,enabled=inspect(cf,baseline)
    if enabled:
        emit("read_only_activation","already_enabled",vps_relay_preserved=True)
        return 0
    # Fetch active production script into the runner's memory only.
    source,source_type,main_header=cf.call("GET",TARGET+"/content/v2",raw=True)
    modules,main_module=decode_worker(source_type,source,main_header)
    main_source=next((m.content for m in modules if m.filename==main_module),b"")
    if MARKER.encode() not in main_source:
        raise ProbeError("production_source_not_recognized")
    # Prevent a racing publisher from changing the source baseline.
    if deployed(cf)!=baseline: raise ProbeError("active_version_changed")
    names=sorted(old_names)
    # Inherit every existing binding including secrets and Durable Objects.
    # Override ONLY this one nonsecret flag with an explicit plain-text var.
    bindings=[{"type":"plain_text","name":FLAG,"text":"true"}
              if name==FLAG else {"type":"inherit","name":name}
              for name in names]
    if FLAG not in old_names:bindings.append({"type":"plain_text","name":FLAG,"text":"true"})
    runtime=(current.get("resources") or {}).get("script_runtime") or {}
    meta={
       "bindings":bindings,
       "exports":old_exports,
       "compatibility_date":str(runtime.get("compatibility_date") or "2026-11-22")[:10],
       "annotations":{"workers/message":"Enable existing private Serverspace read-only API"}
    }
    upload,ctype=encode_upload(modules,main_module,meta)
    cf.call("PUT",TARGET+"?bindings_inherit=strict",upload,ctype)
    emit("read_only_activation","version_upload_accepted")
    candidate=None
    for version in get_versions(cf)[:10]:
        vid=version.get("id") if isinstance(version,dict) else None
        if not isinstance(vid,str):continue
        try:
            _,exports,after_names,active=inspect(cf,vid)
        except (ProbeError,SafeError):
            continue
        if active and after_names==old_names|{FLAG} and exports==old_exports:
            candidate=vid
            break
    if not candidate:raise ProbeError("new_version_integrity_unverified")
    cf.call("POST",TARGET+"/deployments",json.dumps({
        "strategy":"percentage",
        "versions":[{"version_id":candidate,"percentage":100}]
    }).encode(),"application/json")
    if deployed(cf)!=candidate:raise ProbeError("deployment_not_confirmed")
    _,exports,after_names,active=inspect(cf,candidate)
    if not active or after_names!=old_names|{FLAG} or exports!=old_exports:
        raise ProbeError("production_bindings_not_preserved")
    emit("read_only_activation","live",vps_relay_preserved=True)
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (ProbeError,SafeError) as exc:
        code=str(exc)
        if not re.fullmatch(r"[A-Za-z0-9_]{3,80}",code):
            code="cloudflare_api_error"
        emit("read_only_activation","blocked",code=code)
        raise SystemExit(3)
