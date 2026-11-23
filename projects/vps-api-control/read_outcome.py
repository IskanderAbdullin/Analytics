"""Read ONLY the pre-existing private Cloudflare canary outcome.

No cron re-arm, KV deletion, Worker mutation or disclosure of VM records.
Safe to execute independently while the main canary is running.
"""
import json
from canary import api, get_namespace, emit, ProbeError

def main():
    ns=get_namespace()
    try:
        data=json.loads(api("GET","/storage/kv/namespaces/"+ns+"/values/result",raw=True))
    except ProbeError as exc:
        if str(exc).startswith("http_404"):
            emit("cloudflare_private_call","pending_no_result")
            return 5
        emit("cloudflare_private_call","blocked")
        return 4
    except (ValueError,TypeError):
        emit("cloudflare_private_call","invalid_result")
        return 4
    outcome=data.get("outcome") if isinstance(data,dict) else None
    if outcome not in {"serverspace_inventory_ok","invalid_schema","fetch_failed",
                       "bridge_http_400","bridge_http_401","bridge_http_403",
                       "bridge_http_404","bridge_http_405","bridge_http_500",
                       "bridge_http_502","bridge_http_503","bridge_http_504"}:
        emit("cloudflare_private_call","unknown_result")
        return 4
    emit("cloudflare_private_call",outcome)
    return 0 if outcome=="serverspace_inventory_ok" else 4

if __name__=="__main__":
    raise SystemExit(main())
