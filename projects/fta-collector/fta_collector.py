"""FreeTranscriptAPI native-caption collector for an authorized private corpus.
No public output content. Default dry run; one serialized process per ledger.
"""
import argparse,datetime,hashlib,json,os,re,time,urllib.request,urllib.error,urllib.parse
from pathlib import Path
BASE="https://api.freetranscriptapi.com/v1/transcript"
NS="1468098312aa47c995e87ff51252a38a"
ID=re.compile(r"^[A-Za-z0-9_-]{11}$")
def utc():return datetime.datetime.now(datetime.timezone.utc)
def atomic(path,raw):
    tmp=path.with_suffix(path.suffix+".tmp");tmp.write_bytes(raw);os.replace(tmp,path)
def read_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
def json_bytes(obj):return json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode("utf-8")
def ledger_save(path,rows):atomic(path,b"\n".join(json_bytes(x) for x in rows)+b"\n")
def build_url(vid):
    if not ID.fullmatch(vid):raise ValueError("invalid video ID")
    return BASE+"?"+urllib.parse.urlencode({"video_url":vid,"lang":"ru","format":"json"})
def validate(d,duration):
    if d.get("language") not in ("ru","ru-RU"):return {"status":"wrong_language"}
    lines=d.get("transcript")
    if not isinstance(lines,list) or not lines:return {"status":"empty"}
    try:
        starts=[x["start"] for x in lines];ends=[x["start"]+x["duration"] for x in lines]
        if any(not isinstance(x,(float,int)) or not 0<=x<1e7 for x in starts+ends):raise ValueError()
        if starts!=sorted(starts) or any(b<a for a,b in zip(starts,ends)):raise ValueError()
        if any(not isinstance(x["text"],str) for x in lines):raise ValueError()
        chars=sum(len(x["text"]) for x in lines)
        if not chars:raise ValueError()
    except Exception:return {"status":"invalid_segments"}
    first,last=starts[0],max(ends);ratio=last/duration if duration else None
    return {"status":"coverage_ok_unreviewed" if ratio is not None and .95<=ratio<=1.05 and first<60 else "coverage_review","first":first,"last":last,"coverage_fraction":ratio,"segments":len(lines),"chars":chars}
def count_recent(rows,at):
    hour=at-datetime.timedelta(hours=1)
    return sum(1 for r in rows if r.get("provider_attempt") and datetime.datetime.fromisoformat(r["utc"])>hour)
def request(method,url,body=None,headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,data=body,headers=headers or {},method=method),timeout=60) as r:return r.status,r.read(8*1024*1024),dict(r.headers)
    except urllib.error.HTTPError as e:return e.code,e.read(4096),dict(e.headers)
def get_header(h,name):return next((v for k,v in h.items() if k.lower()==name.lower()),None)
def kv_url(vid):
    if not ID.fullmatch(vid):raise ValueError("invalid video ID")
    account=os.environ["CLOUDFLARE_ACCOUNT_ID"]
    return "https://api.cloudflare.com/client/v4/accounts/"+account+"/storage/kv/namespaces/"+NS+"/values/"+urllib.parse.quote("native/youtube/"+vid+"/fta-v1.json",safe="")
def run(queue,ledger,limit,reserved,execute):
    if not 1<=limit<=20 or not 0<=reserved<=20:raise ValueError("invalid bounded-run limits")
    if not ledger.is_absolute():raise ValueError("ledger must be in private absolute path")
    items=read_jsonl(queue);rows=read_jsonl(ledger) if ledger.exists() else []
    seen={r["video_id"] for r in rows if r.get("status") in ("archived_verified","already_verified","not_found")}
    eligible=[x for x in items if ID.fullmatch(x.get("youtube_id","")) and x["youtube_id"] not in seen and x.get("transcript_status")=="not_archived" and x.get("episode_status")!="excluded"]
    key=os.environ.get("FREETRANSCRIPT_API_KEY");remaining=limit if key else max(0,min(limit,20-reserved-count_recent(rows,utc())))
    print(json.dumps({"mode":"authenticated" if key else "anonymous","eligible":len(eligible),"planned":min(remaining,len(eligible)),"execute":execute}),flush=True)
    if not execute:return
    token=os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token or not os.environ.get("CLOUDFLARE_ACCOUNT_ID"):raise SystemExit("missing Cloudflare credentials")
    ledger.parent.mkdir(parents=True,exist_ok=True)
    auth={"Authorization":"Bearer "+token}
    attempts=0
    for item in eligible:
        if attempts>=limit or (not key and count_recent(rows,utc())+reserved>=20):break
        vid=item["youtube_id"];duration=item.get("duration_s")
        dst=kv_url(vid);code,old,_=request("GET",dst,headers=auth)
        if code==200:
            rows.append({"video_id":vid,"utc":utc().isoformat(),"provider_attempt":False,"status":"already_verified","sha256":hashlib.sha256(old).hexdigest(),"bytes":len(old)});ledger_save(ledger,rows);continue
        if code!=404:break
        record={"video_id":vid,"utc":utc().isoformat(),"provider_attempt":True,"status":"started"}
        rows.append(record);ledger_save(ledger,rows);attempts+=1
        try:
            headers={"Accept":"application/json"}
            if key:headers["Authorization"]="Bearer "+key
            code,raw,h=request("GET",build_url(vid),headers=headers)
            record["http_status"]=code
            record["remaining"]=get_header(h,"X-Credits-Remaining" if key else "X-RateLimit-Remaining")
            if code!=200:
                record["status"]="not_found" if code==404 else "provider_error"
                ledger_save(ledger,rows)
                if code in (401,402,403,429) or code>=500:break
                continue
            d=json.loads(raw);v=validate(d,duration);record.update(v)
            if v["status"] not in ("coverage_ok_unreviewed","coverage_review"):
                ledger_save(ledger,rows);continue
            payload=json_bytes({"schema_version":1,"source":"FreeTranscriptAPI public native captions","video_id":vid,"expected_duration_s":duration,"retrieved_utc":utc().isoformat(),"language":d["language"],"first_s":v["first"],"last_s":v["last"],"review_status":v["status"],"response":d})
            if len(payload)>4*1024*1024:
                record["status"]="size_limit";ledger_save(ledger,rows);continue
            digest=hashlib.sha256(payload).hexdigest()
            code,_,_=request("PUT",dst,payload,{**auth,"Content-Type":"application/octet-stream"})
            if code not in (200,201):
                record["status"]="kv_write_failed";ledger_save(ledger,rows);break
            code,readback,_=request("GET",dst,headers=auth)
            if code!=200 or hashlib.sha256(readback).hexdigest()!=digest:
                record["status"]="kv_readback_failed";ledger_save(ledger,rows);break
            record.update(status="archived_verified",coverage=v["status"],sha256=digest,bytes=len(payload),key="native/youtube/"+vid+"/fta-v1.json")
            ledger_save(ledger,rows)
            print(json.dumps({k:record[k] for k in ("video_id","status","coverage","sha256","bytes","remaining")}),flush=True)
            if record["remaining"]=="0":break
            time.sleep(3)
        except Exception as exc:
            record["status"]="error_"+type(exc).__name__;ledger_save(ledger,rows);break
    print("Provider attempts:",attempts,flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument("queue",type=Path);p.add_argument("ledger",type=Path)
    p.add_argument("--limit",type=int,default=3);p.add_argument("--reserved-attempts",type=int,default=0,help="Other calls in current rolling hour; conservative count")
    p.add_argument("--execute",action="store_true");a=p.parse_args();run(a.queue,a.ledger,a.limit,a.reserved_attempts,a.execute)
if __name__=="__main__":main()
