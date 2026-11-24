"""Bounded, read-only Workers Observability aggregation by response status.

No raw invocations, URLs, ray IDs, task details, account IDs or secrets are
returned or printed. The official API uses POST to *run a query*, not a Worker
deployment or VPS operation; no state mutation in the user's scripts.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

SCRIPT="babit-vps-bridge"
URL="https://api.cloudflare.com/client/v4/accounts/{account}/workers/observability/telemetry/query"
def output(stage,**kw):
    print(json.dumps({"stage":"vps_wss_edge_metrics","result":stage,**kw},
                     sort_keys=True),flush=True)
def main():
    token=os.environ.get("CLOUDFLARE_API_TOKEN","")
    account=os.environ.get("CLOUDFLARE_ACCOUNT_ID","")
    if not token or not account:
        output("secrets_unavailable")
        return 3
    if not __import__("re").fullmatch(r"[a-f0-9]{32}",account):
        output("account_id_invalid")
        return 3
    to=int(dt.datetime.now(dt.timezone.utc).timestamp()*1000)
    start=to-6*60*60*1000
    body={"queryId":"vps-wss-edge-aggregate-20261124",
          "dry":True,
          "timeframe":{"from":start,"to":to},
          "view":"calculations","chartType":"aggregate","ignoreSeries":True,
          "limit":15,
          "parameters":{
              "datasets":["cloudflare-workers"],
              "filters":[{"key":"$metadata.service","operation":"eq","type":"string","value":SCRIPT}],
              "calculations":[{"operator":"count","alias":"requests"}],
              "groupBys":[{"value":"$metadata.statusCode","type":"number"}]
          }}
    request=urllib.request.Request(
      URL.format(account=account),data=json.dumps(body).encode(),
      headers={"Authorization":"Bearer "+token,
               "Content-Type":"application/json","Accept":"application/json"},
      method="POST")
    try:
        with urllib.request.urlopen(request,timeout=20) as result:
            raw=result.read(1_000_000)
    except urllib.error.HTTPError as error:
        output("api_denied_or_unavailable",http_status=error.code)
        return 4
    except Exception:
        output("network_error")
        return 4
    try:
        data=json.loads(raw)
    except (ValueError,TypeError):
        output("invalid_json")
        return 4
    if not isinstance(data,dict) or data.get("success") is False:
        output("observability_unavailable_or_invalid_query",
               error_count=len(data.get("errors") or []))
        return 4
    result=data.get("result") or {}
    stats=(result.get("statistics") or {}) if isinstance(result,dict) else {}
    summaries=((result.get("calculations") or {}) if isinstance(result,dict) else {})
    # Cloudflare versions differ; fail closed if grouping schema is unknown.
    raw_rows=summaries.get("groups") if isinstance(summaries,dict) else None
    if not isinstance(raw_rows,list):
        output("response_schema_unknown",top_level_keys=sorted(result)[:12])
        return 4
    codes={}
    for row in raw_rows:
        if not isinstance(row,dict):continue
        group=row.get("groups") or {}
        aggr=row.get("aggregates") or {}
        code=group.get("$metadata.statusCode") if isinstance(group,dict) else None
        n=aggr.get("requests") if isinstance(aggr,dict) else None
        if type(code) is int and 100<=code<=599 and type(n) is int and 0<=n<=1_000_000:
            codes[str(code)]=n
    output("aggregate_ok",status_counts=codes,rows_total=len(raw_rows),
           window_hours=6,source_sampling_caveat=True)
    return 0
if __name__=="__main__":
    sys.exit(main())
