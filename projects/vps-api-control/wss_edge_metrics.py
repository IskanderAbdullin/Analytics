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
    calculations=(result.get("calculations") or []) if isinstance(result,dict) else []
    # Official telemetry schema: calculations[] -> aggregates[] with count +
    # groups:[{key:"$metadata.statusCode",value:NUMBER}]. Print only codes/counts.
    if not isinstance(calculations,list):
        output("response_schema_unknown",calculations_shape="not_array")
        return 4
    codes={}
    total_rows=0
    for item in calculations:
        if not isinstance(item,dict) or item.get("alias") not in ("requests",None):
            continue
        rows=item.get("aggregates") or []
        if not isinstance(rows,list):
            output("response_schema_unknown",aggregates_shape="not_array")
            return 4
        for row in rows:
            total_rows+=1
            if not isinstance(row,dict):continue
            group=row.get("groups") or []
            if not isinstance(group,list):continue
            code=next((g.get("value") for g in group
                if isinstance(g,dict) and g.get("key")=="$metadata.statusCode"),None)
            n=row.get("count")
            if type(code) is int and 100<=code<=599 and type(n) in (int,float) and 0<=n<=1_000_000:
                codes[str(code)]=round(float(n),2)
    output("aggregate_ok",status_counts=codes,rows_total=total_rows,
           window_hours=6,source_sampling_caveat=True)
    return 0
if __name__=="__main__":
    sys.exit(main())
