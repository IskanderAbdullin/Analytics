"""Read only the status of the existing PC tunnel; never print API response data."""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from cloudflare import NoRedirect

ROOT = "https://api.cloudflare.com/client/v4/accounts"
NAME = "pc-agent-private"
LIMIT = 120_000
STATES = {"inactive", "degraded", "healthy", "down"}


def summarize(payload):
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return {"result": "api_rejected"}
    rows = payload.get("result")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return {"result": "invalid_schema"}
    matches = [row for row in rows if row.get("name") == NAME
               and row.get("deleted_at") is None]
    if len(matches) != 1:
        return {"result": "not_found" if not matches else "ambiguous"}
    state = matches[0].get("status")
    if not isinstance(state, str) or state not in STATES:
        return {"result": "unknown_status"}
    return {"result": "ok", "tunnel_status": state,
            "edge_connected": state in {"healthy", "degraded"}}


def audit(account, token, transport=None):
    if not re.fullmatch(r"[0-9a-fA-F]{32}", account) or len(token) < 12:
        return {"result": "secrets_unavailable"}
    # Fixed GET only. No token endpoint, route changes, private data or shell.
    req = Request(f"{ROOT}/{account}/cfd_tunnel?name=pc-agent-private&is_deleted=false&per_page=10",
                  method="GET", headers={"Authorization": "Bearer " + token,
                                         "Accept": "application/json"})
    try:
        opener = transport or build_opener(NoRedirect()).open
        with opener(req, timeout=10) as res:
            if res.status != 200:
                return {"result": "http_error", "http_status": int(res.status)}
            if "application/json" not in res.headers.get("Content-Type", "").lower():
                return {"result": "invalid_content_type"}
            raw = res.read(LIMIT + 1)
        if len(raw) > LIMIT:
            return {"result": "response_too_large"}
        return summarize(json.loads(raw))
    except HTTPError as e:
        return {"result": "http_error", "http_status": int(e.code)}
    except (URLError, TimeoutError, OSError):
        return {"result": "network_unavailable"}
    except (ValueError, TypeError, UnicodeError):
        return {"result": "invalid_schema"}


if __name__ == "__main__":
    out = audit(os.getenv("CLOUDFLARE_ACCOUNT_ID", ""),
                os.getenv("CLOUDFLARE_API_TOKEN", ""))
    print(json.dumps({"pc_tunnel_read_only": out}, sort_keys=True))
    raise SystemExit(0 if out["result"] == "ok" else 3)
