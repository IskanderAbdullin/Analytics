"""Two-video documented TranscriptFetch trial; only receipts in public logs."""
import os,json,hashlib,datetime,time,requests,urllib.parse
NS="1468098312aa47c995e87ff51252a38a"
CASES=[("GIrQV9wMNbg",10774),("EHQ-x9o_du0",11431)]
API="https://transcriptfetch.com/mcp/try"
def log(**kw):print("TF_TRIAL "+json.dumps(kw,ensure_ascii=False),flush=True)
def main():
 account=os.environ["CLOUDFLARE_ACCOUNT_ID"];token=os.environ["CLOUDFLARE_API_TOKEN"]
 base=f"https://api.cloudflare.com/client/v4/accounts/{account}/storage/kv/namespaces/{NS}/values/"
 auth={"Authorization":"Bearer "+token}
 for vid,duration in CASES:
  key=f"native/youtube/{vid}/tf-v1.json";dst=base+urllib.parse.quote(key,safe="")
  old=requests.get(dst,headers=auth,timeout=30)
  if old.status_code==200:
   log(video_id=vid,status="already_exists",sha256=hashlib.sha256(old.content).hexdigest());continue
  if old.status_code!=404:log(video_id=vid,status="kv_lookup_failed",http=old.status_code);break
  try:
   r=requests.post(API,json={"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_transcript","arguments":{"video":vid,"timestamps":True}}},headers={"Accept":"application/json, text/event-stream"},timeout=90)
   if r.status_code!=200:log(video_id=vid,status="provider_http_error",http=r.status_code);break
   if len(r.content)>12000000:log(video_id=vid,status="oversized");break
   try:d=r.json()
   except ValueError:
    events=[json.loads(l[6:]) for l in r.text.splitlines() if l.startswith("data: ") and l[6:].startswith("{")]
    d=next((x for x in events if x.get("id")==1),{})
   result=d.get("result",{})
   s=result.get("structuredContent",{})
   if result.get("isError") or not isinstance(s,dict) or not s:
    log(video_id=vid,status="no_structured_success",rpc_error=bool(d.get("error")),is_error=bool(result.get("isError")),result_keys=list(result.keys())[:12]);break
   lang=s.get("language","");lines=s.get("segments")
   if not isinstance(lang,str) or lang.lower().split("-")[0] not in ("ru","rus") or not isinstance(lines,list) or not lines:
    log(video_id=vid,status="language_or_segments_mismatch",language=lang,keys=list(s.keys())[:20]);break
   try:
    starts=[float(x["start"]) for x in lines];ends=[a+float(x["duration"]) for a,x in zip(starts,lines)]
    assert starts==sorted(starts) and all(a>=0 and b>=a for a,b in zip(starts,ends))
    chars=sum(len(x["text"]) for x in lines);assert chars>0
   except Exception:log(video_id=vid,status="invalid_segments");break
   first,last=starts[0],max(ends);ratio=last/duration
   coverage="coverage_ok_unreviewed" if .95<=ratio<=1.05 and first<60 else "coverage_review"
   record={"schema_version":1,"source":"TranscriptFetch trial native captions","video_id":vid,"expected_duration_s":duration,"retrieved_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"language":"ru","first_s":first,"last_s":last,"review_status":coverage,"response":{"title":s.get("title"),"language":lang,"transcript":lines}}
   raw=json.dumps(record,ensure_ascii=False,separators=(",",":")).encode();sha=hashlib.sha256(raw).hexdigest()
   if len(raw)>4000000:log(video_id=vid,status="size_limit");break
   put=requests.put(dst,data=raw,headers={**auth,"Content-Type":"application/octet-stream"},timeout=30)
   if not put.ok:log(video_id=vid,status="kv_write_failed",http=put.status_code);break
   check=requests.get(dst,headers=auth,timeout=30)
   if not check.ok or hashlib.sha256(check.content).hexdigest()!=sha:log(video_id=vid,status="kv_readback_failed",http=check.status_code);break
   log(video_id=vid,status="archived_verified",source="TranscriptFetch trial",coverage=coverage,language=lang,segments=len(lines),chars=chars,first=first,last=last,expected_duration_s=duration,coverage_fraction=ratio,bytes=len(raw),sha256=sha,key=key)
   time.sleep(3)
  except Exception as e:log(video_id=vid,status="exception",error_type=type(e).__name__);break
if __name__=="__main__":main()
