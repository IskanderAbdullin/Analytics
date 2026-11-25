"""Read only aggregate close reasons for D183/D184 temporary diagnostic Workers."""
import json
import os
import re
from pc_tcp_probe import ROOT, request, Blocked

SQL = """SELECT ConnectionCloseReason AS reason, COUNT(*) AS n
FROM zero_trust_network_sessions
WHERE SessionStartTime >= '2026-11-25T10:43:45Z'
AND SessionStartTime <= '2026-11-25T10:46:10Z'
AND OnrampType = 'WORKERS_VPC'
AND (SourceName LIKE 'pc-vpc-status-%' OR SourceName LIKE 'pc-vpc-tcp-%')
GROUP BY ConnectionCloseReason LIMIT 20"""
REASONS = set("""CLIENT_CLOSED CLIENT_IDLE_TIMEOUT CLIENT_TLS_ERROR CLIENT_ERROR
ORIGIN_CLOSED ORIGIN_TLS_ERROR ORIGIN_ERROR ORIGIN_UNREACHABLE ORIGIN_UNROUTABLE
PROXY_CONN_REFUSED EGRESS_PORT_ALLOCATION_ERROR UNKNOWN MISMATCHED_IP_VERSIONS
TOO_MANY_ACTIVE_SESSIONS_FOR_ACCOUNT TOO_MANY_ACTIVE_SESSIONS_FOR_USER
TOO_MANY_NEW_SESSIONS_FOR_ACCOUNT TOO_MANY_NEW_SESSIONS_FOR_USER""".split())


def summary(payload):
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return {"result": "query_rejected"}
    rows = payload.get("result")
    if not isinstance(rows, list) or len(rows) > 20:
        return {"result": "invalid_schema"}
    reasons = {}
    for row in rows:
        if not isinstance(row, dict):
            return {"result": "invalid_schema"}
        r = row.get("reason")
        n = row.get("n")
        if type(n) is not int or n < 0 or n > 1000:
            return {"result": "invalid_count"}
        key = r if isinstance(r, str) and r in REASONS else "UNRECOGNIZED"
        reasons[key] = reasons.get(key, 0) + n
    return {"result": "ok" if rows else "no_matching_records", "reasons": reasons}


def main():
    account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    token = os.getenv("CLOUDFLARE_API_TOKEN", "")
    if not re.fullmatch(r"[0-9a-fA-F]{32}", account) or len(token) < 12:
        print('{"result":"secrets_unavailable"}')
        return 3
    try:
        status, payload = request(ROOT + "/" + account + "/logs/explorer/query/sql",
                                  "POST", token, SQL.encode(), "text/plain")
        out = summary(payload) if status == 200 else {"result":"http_error","http_status":status}
    except (Blocked, ValueError, TypeError, OSError):
        out = {"result":"query_unavailable"}
    print(json.dumps(out,sort_keys=True))
    return 0 if out["result"] in ("ok", "no_matching_records") else 3


if __name__ == "__main__":
    raise SystemExit(main())
