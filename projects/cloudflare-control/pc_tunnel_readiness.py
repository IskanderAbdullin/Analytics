"""Inspect existing named tunnel readiness; no credential, route or config mutations."""
import json
import os
import re
from pc_tcp_probe import ROOT, request, Blocked

NAME = "pc-agent-private"
STATES = {"healthy", "degraded", "inactive", "down"}
UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")


def response(url, token):
    status, payload = request(url, "GET", token)
    if status != 200:
        return {"http_status": status}, None
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return {"result": "api_rejected"}, None
    return {"result": "ok"}, payload.get("result")


def config_summary(obj):
    if obj is None or (isinstance(obj, dict) and obj.get("config") is None):
        return {"result": "configuration_not_returned"}
    if not isinstance(obj, dict) or not isinstance(obj.get("config"), dict):
        return {"result": "invalid_schema"}
    cfg = obj["config"]
    ingress = cfg.get("ingress", [])
    if not isinstance(ingress, list) or any(not isinstance(x, dict) for x in ingress):
        return {"result": "invalid_schema"}
    return {"result": "ok", "hostname_rule_present": any(bool(x.get("hostname")) for x in ingress),
            "origin_rule_present": any(x.get("service") != "http_status:404" for x in ingress),
            "private_routing_enabled": cfg.get("warp-routing", {}).get("enabled") is True
            if isinstance(cfg.get("warp-routing", {}), dict) else False}


def audit(account, token):
    if not re.fullmatch(r"[0-9a-fA-F]{32}", account) or len(token) < 12:
        return {"result": "secrets_unavailable"}
    root = ROOT + "/" + account + "/cfd_tunnel"
    meta, rows = response(root + "?name=" + NAME + "&is_deleted=false&per_page=10", token)
    if meta.get("result") != "ok":
        return meta
    if not isinstance(rows, list):
        return {"result": "invalid_schema"}
    match = [x for x in rows if isinstance(x, dict) and x.get("name") == NAME
             and x.get("deleted_at") is None]
    if len(match) != 1:
        return {"result": "not_found_or_ambiguous"}
    row = match[0]
    ident = row.get("id", "")
    state = row.get("status")
    if not isinstance(ident, str) or not UUID.fullmatch(ident) or state not in STATES:
        return {"result": "invalid_schema"}
    src = row.get("config_src")
    out = {"result": "ok", "status": state, "config_source":
           src if src in ("cloudflare", "local") else "unknown"}
    base = root + "/" + ident
    meta, connections = response(base + "/connections", token)
    if meta.get("result") == "ok":
        meta = {"result": "ok", "connection_present": bool(connections)} if isinstance(connections, list) else {"result": "invalid_schema"}
    out["connections"] = meta
    meta, cfg = response(base + "/configurations", token)
    out["configuration"] = config_summary(cfg) if meta.get("result") == "ok" else meta
    meta, services = response(ROOT + "/" + account + "/connectivity/directory/services?per_page=100&type=http", token)
    if meta.get("result") == "ok":
        meta = service_summary(services, ident)
    out["existing_vpc_service"] = meta
    return out


def service_summary(rows, tunnel_id):
    if not isinstance(rows, list):
        return {"result":"invalid_schema"}
    matches = [x for x in rows if isinstance(x, dict) and x.get("name") == "pc-agent-loopback"]
    if len(matches) != 1:
        return {"result":"not_found_or_ambiguous"}
    row = matches[0]
    host = row.get("host")
    if not isinstance(host, dict):
        return {"result":"invalid_schema"}
    network = host.get("network")
    return {"result":"ok", "type_http":row.get("type") == "http",
            "loopback":host.get("ipv4") == "127.0.0.1",
            "port_8765":row.get("http_port") == 8765,
            "same_tunnel":isinstance(network, dict) and network.get("tunnel_id") == tunnel_id}


if __name__ == "__main__":
    try:
        out = audit(os.getenv("CLOUDFLARE_ACCOUNT_ID", ""), os.getenv("CLOUDFLARE_API_TOKEN", ""))
    except (Blocked, ValueError, TypeError, OSError):
        out = {"result": "audit_unavailable"}
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out.get("result") == "ok" else 3)
