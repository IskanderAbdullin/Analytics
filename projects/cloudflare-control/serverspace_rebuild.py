"""One-shot Cloudflare full Worker upload with inherited Secrets and declared exports.

Runs ONLY inside GitHub Actions with existing Cloudflare credentials.
Original production source never leaves the ephemeral runner. No trade actions.
"""
from __future__ import annotations
import json
from serverspace_deploy import (
    Cloudflare, TARGET, MARKER, decode_worker, encode_upload, SafeError
)


def names_from_bindings(bindings):
    if not isinstance(bindings, list):
        raise SafeError("BINDINGS_SCHEMA_UNEXPECTED")
    names = [x.get("name") for x in bindings if isinstance(x, dict)]
    if any(not isinstance(x, str) for x in names):
        raise SafeError("BINDINGS_INVALID")
    return names


def get_versions(cf):
    result = cf.call("GET", TARGET + "/versions?per_page=10")
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for field in ("items", "versions", "result"):
            if isinstance(result.get(field), list):
                return result[field]
    raise SafeError("VERSIONS_SCHEMA_UNEXPECTED")


def fetch_version(cf, version_id):
    v = cf.call("GET", TARGET + "/versions/" + version_id)
    resources = v.get("resources") or {}
    exports = (resources.get("script_runtime") or {}).get("exports") or {}
    return v, exports, names_from_bindings(resources.get("bindings") or [])


def main():
    cf = Cloudflare()
    history = cf.call("GET", TARGET + "/deployments")
    deployments = history.get("deployments") if isinstance(history, dict) else history
    if not isinstance(deployments, list) or not deployments:
        raise SafeError("NO_DEPLOYMENT")
    active = next((x.get("version_id") for x in deployments[0].get("versions", [])
                   if x.get("percentage") == 100), None)
    if not active:
        raise SafeError("NO_ACTIVE_VERSION")
    current, old_exports, old_names = fetch_version(cf, active)
    if "VpsAgentRelay" not in old_exports or "SERVERSPACE_API_KEY" not in old_names:
        raise SafeError("CURRENT_VERSION_UNEXPECTED")
    if old_exports.get("ServerspaceReadOnlyEntrypoint", {}).get("type") == "worker":
        print(json.dumps({"action":"none","result":"already_live"}))
        return
    source, source_type, main_header = cf.call("GET", TARGET + "/content/v2", raw=True)
    modules, main_module = decode_worker(source_type, source, main_header)
    body = next((m.content for m in modules if m.filename == main_module), b"")
    if MARKER.encode() not in body:
        raise SafeError("PATCHED_SOURCE_NOT_FOUND")
    # Re-create current Worker version with *all* bindings inherited. The
    # API refuses the upload if any existing Secret/DO binding cannot resolve.
    all_bindings = [{"type":"inherit","name":x} for x in old_names]
    exports = dict(old_exports)
    exports["ServerspaceReadOnlyEntrypoint"] = {"type":"worker"}
    runtime = current.get("resources", {}).get("script_runtime") or {}
    date = str(runtime.get("compatibility_date") or "2026-11-22")[:10]
    meta = {
        "bindings": all_bindings,
        "exports": exports,
        "compatibility_date": date,
        "annotations": {"workers/message":"Serverspace named read-only WorkerEntryPoint"}
    }
    upload, ctype = encode_upload(modules, main_module, meta)
    cf.call("PUT", TARGET + "?bindings_inherit=strict", upload, ctype)
    print(json.dumps({"stage":"full_upload","result":"accepted"}))
    chosen = None
    for entry in get_versions(cf)[:5]:
        v = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(v,str):continue
        _, exp, names = fetch_version(cf,v)
        if (exp.get("ServerspaceReadOnlyEntrypoint",{}).get("type") == "worker"
            and "VpsAgentRelay" in exp and
            {"SERVERSPACE_API_KEY","VPS_AGENT_RELAY"}.issubset(names)):
            chosen=v
            break
    if not chosen:
        raise SafeError("EXPORT_NOT_REGISTERED")
    cf.call("POST", TARGET+"/deployments", json.dumps({
        "strategy":"percentage","versions":[{"version_id":chosen,"percentage":100}]
    }).encode("utf-8"), "application/json")
    latest = cf.call("GET",TARGET+"/deployments")
    ds = latest.get("deployments") if isinstance(latest,dict) else latest
    verified = bool(ds) and any(
       x.get("version_id") == chosen and x.get("percentage") == 100
       for x in ds[0].get("versions",[]))
    if not verified:
        raise SafeError("DEPLOYMENT_NOT_CONFIRMED")
    print(json.dumps({"stage":"activation","result":"live",
        "serverspace_private_entrypoint":True,"vps_relay_preserved":True}))


if __name__ == "__main__":
    try:
        main()
    except SafeError as e:
        print(json.dumps({"stage":"blocked","code":str(e)}))
        raise SystemExit(3)
