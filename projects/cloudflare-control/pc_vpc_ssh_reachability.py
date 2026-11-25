"""One fixed TCP22 reachability check through the existing tunnel binding; no SSH data or commands."""
import json
import os
from pathlib import Path
import re
import secrets
import time
from pc_tcp_probe import ROOT, api, request, Blocked

OUTCOMES = {"tcp_open","timeout","connection_failed","connection_refused","connection_timeout","destination_unavailable","destination_not_found","destination_ip_prohibited","destination_ip_unroutable","dns_error","http_request_denied","proxy_internal_error","connection_read_timeout","connection_write_timeout","rate_limited","connection_reset","tls_error","unknown_proxy_error","connect_type_error","socket_type_error","connect_other_error","socket_other_error","missing_connect_method","invalid_socket_shape"}


def japi(url, method, token, payload):
    return api(url, method, token, json.dumps(payload).encode(), "application/json")


def resource_id(obj, key):
    value = obj.get(key, "") if isinstance(obj, dict) else ""
    if not re.fullmatch(r"[0-9a-fA-F]{32}", value):
        raise Blocked("resource_id_invalid")
    return value


def multipart(tunnel_id, nonce, expires, ns):
    boundary = "probe-" + secrets.token_hex(16)
    meta = {"main_module":"index.js", "compatibility_date":"2026-01-01",
            "bindings":[
                {"type":"vpc_network","name":"PRIVATE_TUNNEL","tunnel_id":tunnel_id},
                {"type":"secret_text","name":"NONCE","text":nonce},
                {"type":"plain_text","name":"EXPIRES_MS","text":str(expires)},
                {"type":"kv_namespace","name":"RESULT","namespace_id":ns}
            ]}
    source = Path(__file__).with_name("pc_vpc_ssh_reachability.mjs").read_bytes()
    return b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"metadata\"\r\nContent-Type: application/json\r\n\r\n".encode(),
        json.dumps(meta).encode(), b"\r\n",
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"index.js\"; filename=\"index.js\"\r\nContent-Type: application/javascript+module\r\n\r\n".encode(),
        source, f"\r\n--{boundary}--\r\n".encode()
    ]), "multipart/form-data; boundary=" + boundary


def read_result(url, token, nonce):
    status, obj = request(url, "GET", token)
    if status == 404:
        return None
    if status != 200:
        raise Blocked("result_http_" + str(status))
    if (not isinstance(obj, dict) or obj.get("nonce") != nonce
            or obj.get("port") != 22 or obj.get("result") not in OUTCOMES):
        raise Blocked("result_schema_invalid")
    return obj["result"]


def cleanup(url, token):
    try:
        status, obj = request(url, "DELETE", token)
        return status == 404 or (200 <= status < 300 and isinstance(obj, dict)
                                 and obj.get("success") is True)
    except Exception:
        return False


def main():
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    try:
        if not re.fullmatch(r"[0-9a-fA-F]{32}", account) or len(token) < 12:
            raise ValueError()
    except ValueError:
        print('{"result":"missing_or_invalid_configuration"}', flush=True)
        return 3
    root = ROOT + "/" + account
    name = "pc-vpc-tcp-" + secrets.token_hex(12)
    script = root + "/workers/scripts/" + name
    kv = root + "/storage/kv/namespaces"
    queues = root + "/queues"
    qurl = nsurl = consumer = None
    attempted = False
    stage = "existing_tunnel_preflight"
    out = {"result":"not_run"}
    try:
        tunnel_rows = api(root + "/cfd_tunnel?name=pc-agent-private&is_deleted=false&per_page=10","GET",token)
        matches = [x for x in tunnel_rows if x.get("name") == "pc-agent-private" and x.get("deleted_at") is None]
        if len(matches) != 1 or matches[0].get("status") not in ("healthy","degraded"):
            raise Blocked("existing_tunnel_not_connected")
        tid = matches[0].get("id")
        if not isinstance(tid,str) or not re.fullmatch(r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}",tid):
            raise Blocked("tunnel_id_invalid")
        stage = "fresh_name"
        code, _ = request(script + "/script-settings", "GET", token)
        if code != 404:
            raise Blocked("fresh_name_not_verified")
        stage = "queue_create"
        q = japi(queues, "POST", token, {"queue_name":name})
        qurl = queues + "/" + resource_id(q, "queue_id")
        stage = "kv_create"
        ns = resource_id(japi(kv,"POST",token,{"title":name}), "id")
        nsurl = kv + "/" + ns
        nonce = secrets.token_hex(32)
        body, ctype = multipart(tid,nonce,int(time.time()*1000)+180_000,ns)
        stage = "worker_upload"
        attempted = True
        api(script,"PUT",token,body,ctype)
        stage = "disable_public_route"
        japi(script+"/subdomain","POST",token,{"enabled":False,"previews_enabled":False})
        stage = "consumer_create"
        c = japi(qurl+"/consumers","POST",token,{"script_name":name,"type":"worker",
                 "settings":{"batch_size":1,"max_retries":0,"max_wait_time_ms":1000,"max_concurrency":1}})
        consumer = qurl+"/consumers/"+resource_id(c,"consumer_id")
        stage = "publish_one_message"
        japi(qurl+"/messages","POST",token,{"body":{"probe":nonce}})
        print('{"stage":"one_message_published"}', flush=True)
        stage = "read_result"
        deadline = time.monotonic()+100
        while time.monotonic() < deadline:
            result = read_result(nsurl+"/values/result",token,nonce)
            if result:
                out = {"result":result,"port":22,"source":"cloudflare_vpc_tunnel"}
                break
            time.sleep(3)
        else:
            out = {"result":"no_worker_result"}
    except Blocked as exc:
        out = {"result":str(exc),"stage":stage}
    except Exception:
        out = {"result":"unexpected_error","stage":stage}
    finally:
        results = {}
        for key,url in (("consumer",consumer),("worker",script if attempted else None),
                        ("queue",qurl),("kv",nsurl)):
            if url:
                results[key] = cleanup(url,token)
        out["cleanup"] = results
        # Names only, only if cleanup not confirmed; never log credentials or target.
        if not all(results.values()) or stage in ("queue_create","kv_create"):
            out["temporary_resource_name"] = name
        print(json.dumps(out,sort_keys=True),flush=True)
    return 0 if out["result"] in OUTCOMES and all(results.values()) else 3


if __name__ == "__main__":
    raise SystemExit(main())
