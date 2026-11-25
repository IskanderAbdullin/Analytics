"""One temporary TCP reachability probe; no SSH handshake, credentials or commands."""
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = "https://api.cloudflare.com/client/v4/accounts"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Blocked(Exception):
    pass


def request(url, method, token, data=None, content_type=None):
    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    try:
        with build_opener(NoRedirect()).open(
            Request(url, method=method, headers=headers, data=data), timeout=20
        ) as response:
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise Blocked("response_limit")
            return response.status, json.loads(raw)
    except HTTPError as exc:
        return exc.code, None
    except Exception:
        raise Blocked("network_or_schema_error") from None


def api(url, method, token, data=None, content_type=None):
    status, obj = request(url, method, token, data, content_type)
    if not 200 <= status < 300:
        raise Blocked("api_http_" + str(status))
    if not isinstance(obj, dict) or obj.get("success") is not True:
        raise Blocked("api_rejected")
    return obj.get("result")


def multipart(host, challenge, expires):
    boundary = "probe-" + secrets.token_hex(16)
    meta = {"main_module": "index.js", "compatibility_date": "2026-01-01",
            "bindings": [
                {"type": "secret_text", "name": "TARGET_HOST", "text": host},
                {"type": "secret_text", "name": "PROBE_TOKEN", "text": challenge},
                {"type": "plain_text", "name": "EXPIRES_MS", "text": str(expires)}
            ]}
    source = Path(__file__).with_name("pc_tcp_probe.mjs").read_bytes()
    pieces = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"metadata\"\r\nContent-Type: application/json\r\n\r\n".encode(),
        json.dumps(meta).encode(), b"\r\n",
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"index.js\"; filename=\"index.js\"\r\nContent-Type: application/javascript+module\r\n\r\n".encode(),
        source, f"\r\n--{boundary}--\r\n".encode()
    ]
    return b"".join(pieces), "multipart/form-data; boundary=" + boundary


def main():
    host = os.environ.get("PC_SSH_PROBE_HOST", "").strip()
    if not host:
        print('{"result":"target_secret_missing","worker_created":false}')
        return 3
    try:
        addr = ipaddress.IPv4Address(host)
        if not addr.is_global or addr.is_multicast:
            raise ValueError()
    except ValueError:
        print('{"result":"invalid_target","worker_created":false}')
        return 3
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not re.fullmatch(r"[0-9a-fA-F]{32}", account) or len(token) < 12:
        print('{"result":"cloud_auth_missing","worker_created":false}')
        return 3
    base = ROOT + "/" + account + "/workers"
    name = "pc-tcp-probe-" + secrets.token_hex(12)
    target = base + "/scripts/" + name
    attempted = False
    created = False
    out = {"result": "not_run"}
    try:
        sub = api(base + "/subdomain", "GET", token)
        subdomain = sub.get("subdomain", "") if isinstance(sub, dict) else ""
        if not re.fullmatch(r"[a-z0-9-]{1,63}", subdomain):
            raise Blocked("subdomain_unavailable")
        code, _ = request(target + "/script-settings", "GET", token)
        if code != 404:
            raise Blocked("fresh_name_not_verified")
        challenge = secrets.token_hex(32)
        body, ctype = multipart(str(addr), challenge, int(time.time() * 1000) + 180_000)
        attempted = True
        api(target, "PUT", token, body, ctype)
        created = True
        api(target + "/subdomain", "POST", token,
            b'{"enabled":true,"previews_enabled":false}', "application/json")
        time.sleep(4)
        status, data = request("https://" + name + "." + subdomain + ".workers.dev/probe",
                               "POST", challenge, b"")
        if status == 200 and isinstance(data, dict) and data.get("result") in (
            "tcp_open", "connection_failed", "timeout"
        ):
            out = {"result": data["result"], "port": 22}
        else:
            out = {"result": "probe_http_" + str(status)}
    except Blocked as exc:
        out = {"result": str(exc)}
    except Exception:
        out = {"result": "unexpected_error"}
    finally:
        out["worker_created"] = created
        if attempted:
            try:
                status, payload = request(target, "DELETE", token)
                out["cleanup_confirmed"] = status == 404 or (
                    200 <= status < 300 and isinstance(payload, dict) and payload.get("success") is True
                )
            except Exception:
                out["cleanup_confirmed"] = False
            if not out["cleanup_confirmed"]:
                # Only the random temporary Worker name; no account, target or tokens.
                out["cleanup_worker_name"] = name
        print(json.dumps(out, sort_keys=True))
    return 0 if out["result"] in ("tcp_open", "connection_failed", "timeout") and out.get("cleanup_confirmed") else 3


if __name__ == "__main__":
    raise SystemExit(main())
