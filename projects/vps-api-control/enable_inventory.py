"""Enable ONLY the existing read-only Serverspace endpoint on existing Worker.

Cloudflare settings PATCH uses env merge, not binding-list replacement.
Preserves the original Worker, Durable Object, secrets, and WSS routing.
Never reads secret values, prints server/account IDs or executes VPS commands.
"""
import json
import time
import uuid
from canary import api, emit, ProbeError, BRIDGE

BASE="/workers/scripts/"+BRIDGE
ENTRY="ServerspaceReadOnlyEntrypoint"

def current():
    deployments=api("GET",BASE+"/deployments")
    items=deployments.get("deployments") if isinstance(deployments,dict) else deployments
    if not isinstance(items,list) or not items: raise ProbeError("deployment_missing")
    version=next((v.get("version_id") for v in items[0].get("versions",[])
                  if v.get("percentage")==100),None)
    if not isinstance(version,str): raise ProbeError("active_version_missing")
    return version

def inspect(version):
    data=api("GET",BASE+"/versions/"+version)
    if not isinstance(data,dict): raise ProbeError("version_schema")
    resources=data.get("resources") or {}
    exports=(resources.get("script_runtime") or {}).get("exports") or {}
    bindings=resources.get("bindings") or []
    if not isinstance(exports,dict) or exports.get(ENTRY,{}).get("type")!="worker":
        raise ProbeError("entrypoint_not_registered")
    if not isinstance(bindings,list): raise ProbeError("bindings_schema")
    names={x.get("name") for x in bindings if isinstance(x,dict) and isinstance(x.get("name"),str)}
    if not {"SERVERSPACE_API_KEY","VPS_AGENT_RELAY"}.issubset(names) or "VpsAgentRelay" not in exports:
        raise ProbeError("existing_vps_bindings_missing")
    value=next((x.get("text") or x.get("value") for x in bindings
                if isinstance(x,dict) and x.get("name")=="SERVERSPACE_API_ENABLED"),None)
    return names, exports, value=="true"

def main():
    baseline=current()
    expected_names, expected_exports, enabled=inspect(baseline)
    if enabled:
        emit("read_only_activation","already_enabled")
        return 0
    # API's /settings PATCH requires multipart/form-data with a field
    # called 'settings'; application/json returns HTTP 415.
    payload={"env":{"SERVERSPACE_API_ENABLED":{"type":"plain_text","text":"true"}}}
    boundary="----BabitSettings"+uuid.uuid4().hex
    crlf=bytes([13,10])
    body=b"".join([
        ("--"+boundary).encode(),crlf,
        b'Content-Disposition: form-data; name="settings"',crlf,
        b"Content-Type: application/json",crlf,crlf,
        json.dumps(payload).encode(),crlf,
        ("--"+boundary+"--").encode(),crlf
    ])
    api("PATCH",BASE+"/settings",body,"multipart/form-data; boundary="+boundary)
    emit("read_only_activation","settings_patch_accepted")
    candidate=None
    for _ in range(5):
        response=api("GET",BASE+"/versions?per_page=10")
        versions=response.get("items") if isinstance(response,dict) else response
        if not isinstance(versions,list): raise ProbeError("version_list_schema")
        for entry in versions[:10]:
            version=entry.get("id") if isinstance(entry,dict) else None
            if not isinstance(version,str): continue
            try:
                names,exports,active=inspect(version)
            except ProbeError:
                # Older versions may predate the private entrypoint.
                continue
            if active and names==expected_names|{"SERVERSPACE_API_ENABLED"} and exports==expected_exports:
                candidate=version
                break
        if candidate:break
        time.sleep(2)
    if not candidate:raise ProbeError("patched_version_not_verified")
    if current()!=candidate:
        api("POST",BASE+"/deployments",json.dumps({
            "strategy":"percentage",
            "versions":[{"version_id":candidate,"percentage":100}]
        }).encode())
    if current()!=candidate:raise ProbeError("promotion_not_confirmed")
    names,exports,active=inspect(candidate)
    if not active or names!=expected_names|{"SERVERSPACE_API_ENABLED"} or exports!=expected_exports:
        raise ProbeError("active_binding_integrity_failure")
    emit("read_only_activation","active",vps_relay_preserved=True)
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except ProbeError as exc:
        emit("read_only_activation","blocked",code=str(exc))
        raise SystemExit(3)
