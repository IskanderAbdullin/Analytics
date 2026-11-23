"""Collect non-identifying VPS power-state aggregates over the proven private binding.

Uses the EXISTING Cloudflare diagnostic Worker and KV namespace. No new Worker,
no public route, no server ID/IP/name, no provider power operation. Raw provider
response lives only in Cloudflare and is not committed or logged by Actions.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from canary import (BRIDGE, KV_TITLE, ProbeError, WORKER, api, emit,
                    get_namespace, multipart)

REQUEST = Path(__file__).with_name("summary_request.json")
KEY = "summary_v1"
SUMMARY_SCHEMA = 1
JS = r"""
export default {
  fetch() { return new Response("Not found", {status:404}); },
  async scheduled(event, env, ctx) {
    ctx.waitUntil((async () => {
      if (await env.PROBE_RESULTS.get("summary_v1")) return;
      let summary = {schema_version:1,outcome:"fetch_failed"};
      try {
        const response = await env.SERVERSPACE_SERVICE.fetch(
          "http://serverspace.internal/internal/serverspace/list-servers",
          {method:"POST",redirect:"manual",signal:AbortSignal.timeout(12000)}
        );
        if (!response.ok) {
          summary.outcome="bridge_http_"+response.status;
        } else {
          const payload=await response.json();
          if (!payload || !Array.isArray(payload.servers) ||
              !Number.isInteger(payload.count) ||
              payload.count !== payload.servers.length ||
              payload.count > 250) {
            summary.outcome="invalid_schema";
          } else {
            let on=0, off=0, unknown=0;
            for (const item of payload.servers) {
              if (!item || typeof item !== "object" || typeof item.id !== "string") {
                summary.outcome="invalid_schema";
                break;
              }
              if (item.is_power_on === true) on++;
              else if (item.is_power_on === false) off++;
              else unknown++;
            }
            if (summary.outcome === "fetch_failed") {
              summary={
                schema_version:1,outcome:"summary_ok",
                count:payload.count,powered_on:on,powered_off:off,
                power_unknown:unknown
              };
            }
          }
        }
      } catch (_) { summary={schema_version:1,outcome:"fetch_failed"}; }
      await env.PROBE_RESULTS.put("summary_v1",JSON.stringify(summary),
        {expirationTtl:summary.outcome==="summary_ok"?3600:180});
    })());
  }
};
"""

def request():
    obj=json.loads(REQUEST.read_text("utf-8"))
    if (not isinstance(obj,dict) or
        set(obj)!={"schema_version","nonce","operation"} or
        obj["schema_version"]!=1 or type(obj["nonce"]) is not int or
        not 0 <= obj["nonce"] <= 2147483647 or
        obj["operation"] not in ("stage","read")):
        raise ProbeError("invalid_request")
    return obj["operation"]

def verified_existing(ns):
    base="/workers/scripts/"+WORKER
    cfg=api("GET",base+"/settings")
    if not isinstance(cfg,dict):raise ProbeError("diagnostic_settings_schema")
    bindings=cfg.get("bindings") or []
    if not isinstance(bindings,list) or len(bindings)!=2:
        raise ProbeError("diagnostic_binding_count")
    found={b.get("name"):b for b in bindings if isinstance(b,dict)}
    svc=found.get("SERVERSPACE_SERVICE",{})
    kv=found.get("PROBE_RESULTS",{})
    if (svc.get("type")!="service" or svc.get("service")!=BRIDGE or
        svc.get("entrypoint")!="ServerspaceReadOnlyEntrypoint" or
        kv.get("type")!="kv_namespace" or kv.get("namespace_id")!=ns):
        raise ProbeError("diagnostic_bindings_changed")
    dep=api("GET",base+"/deployments")
    records=dep.get("deployments") if isinstance(dep,dict) else dep
    if not isinstance(records,list) or not records:
        raise ProbeError("diagnostic_not_deployed")
    emit("summary_probe","existing_diagnostic_confirmed")
    return base

def audit_scheduled_version(base):
    deployments=api("GET",base+"/deployments")
    records=deployments.get("deployments") if isinstance(deployments,dict) else deployments
    if not isinstance(records,list) or not records:
        raise ProbeError("diagnostic_deployments_schema")
    active=next((v.get("version_id") for v in records[0].get("versions",[])
                 if v.get("percentage")==100),None)
    if not isinstance(active,str):
        raise ProbeError("diagnostic_active_version_unknown")
    versions=api("GET",base+"/versions?per_page=10")
    options=versions.get("items",versions.get("versions",[])) if isinstance(versions,dict) else versions
    if not isinstance(options,list) or not options or not isinstance(options[0].get("id"),str):
        raise ProbeError("diagnostic_versions_schema")
    latest=options[0]["id"]
    def scheduled_for(version):
        resource=api("GET",base+"/versions/"+version)
        script=(resource or {}).get("resources",{}).get("script",{})
        return "scheduled" in (script.get("handlers") or [])
    active_scheduled=scheduled_for(active)
    latest_scheduled=scheduled_for(latest)
    emit("summary_probe","deployment_audit",
         active_scheduled=active_scheduled,
         latest_scheduled=latest_scheduled,
         active_is_latest=active==latest)
    return active,latest,active_scheduled,latest_scheduled

def stage(ns):
    base=verified_existing(ns)
    # The source is script-only and public-safe, but the uploaded package
    # always preserves the two fixed existing bindings by explicit comparison.
    existing=api("GET",base+"/content/v2",raw=True)
    if b"summary_v1" in existing and b"serverspace.internal" in existing:
        emit("summary_probe","already_staged")
    else:
        if b"serverspace_inventory_ok" not in existing:
            raise ProbeError("diagnostic_source_unrecognized")
        metadata={"main_module":"main.mjs","compatibility_date":"2026-11-23",
          "bindings":[
            {"type":"service","name":"SERVERSPACE_SERVICE",
             "service":BRIDGE,"entrypoint":"ServerspaceReadOnlyEntrypoint"},
            {"type":"kv_namespace","name":"PROBE_RESULTS","namespace_id":ns}
          ]}
        body,ctype=multipart(metadata,JS)
        api("PUT",base,body,ctype)
        emit("summary_probe","code_accepted")
        verified_existing(ns)
        actual=api("GET",base+"/content/v2",raw=True)
        if b"summary_v1" not in actual:
            raise ProbeError("summary_source_not_confirmed")
    api("PUT",base+"/schedules",json.dumps([{"cron":"* * * * *"}]).encode())
    emit("summary_probe","scheduled",aggregate_only=True)
    return 0

def read(ns):
    base=verified_existing(ns)
    audit_scheduled_version(base)
    try:
        payload=json.loads(api("GET","/storage/kv/namespaces/"+ns+
                               "/values/"+KEY,raw=True))
    except ProbeError as exc:
        if str(exc).startswith("http_404"):
            emit("summary_probe","pending")
            return 5
        raise
    except (ValueError,TypeError):
        raise ProbeError("summary_invalid_json") from None
    if not isinstance(payload,dict) or payload.get("schema_version")!=SUMMARY_SCHEMA:
        raise ProbeError("summary_schema")
    code=payload.get("outcome")
    if code!="summary_ok":
        if not isinstance(code,str) or not re.fullmatch(r"[a-z_0-9]{3,70}",code):
            raise ProbeError("summary_error_invalid")
        emit("summary_probe","retryable",error_category=code)
        return 4
    expected={"schema_version","outcome","count","powered_on","powered_off",
              "power_unknown"}
    if set(payload)!=expected:
        raise ProbeError("summary_keys")
    counts=[payload[k] for k in ("count","powered_on","powered_off","power_unknown")]
    if any(type(x) is not int or not 0<=x<=250 for x in counts) or sum(counts[1:])!=counts[0]:
        raise ProbeError("summary_counts")
    emit("summary_probe","summary_ok",count=counts[0],
         powered_on=counts[1],powered_off=counts[2],power_unknown=counts[3])
    api("PUT",base+"/schedules",json.dumps([]).encode())
    emit("summary_probe","cron_disabled_after_success")
    return 0

def main():
    op=request()
    ns=get_namespace()
    return stage(ns) if op=="stage" else read(ns)

if __name__=="__main__":
    try:sys.exit(main())
    except ProbeError as exc:
        code=str(exc)
        if not re.fullmatch(r"[a-zA-Z0-9_]{3,90}",code):
            code="cloudflare_api_error"
        emit("summary_probe","blocked",code=code)
        sys.exit(3)
