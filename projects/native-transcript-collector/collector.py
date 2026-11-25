"""Native transcript pilot; run only with authorized access and private output storage."""
import argparse,csv,datetime,hashlib,json,os,re,time,urllib.parse,urllib.request,urllib.error
from pathlib import Path
ID=re.compile(r"^[A-Za-z0-9_-]{11}$")
ROOT="https://api.supadata.ai/v1/transcript"
def now():
    return datetime.datetime.now(datetime.timezone.utc)
def atomic(path,data):
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_bytes(data); os.replace(tmp,path)
def dump(path,obj):
    atomic(path,json.dumps(obj,ensure_ascii=False,indent=2).encode("utf-8"))
def build_url(vid):
    if not ID.fullmatch(vid): raise ValueError("invalid video id")
    return ROOT+"?"+urllib.parse.urlencode({"url":"https://www.youtube.com/watch?v="+vid,"lang":"ru","text":"false","mode":"native"})
def validate(data,duration_s):
    content=data.get("content")
    if not isinstance(content,list) or not content: return {"status":"invalid_or_empty"}
    if data.get("lang") not in ("ru","ru-RU"): return {"status":"wrong_language"}
    end=0; starts=[]; chars=0
    for seg in content:
        if not isinstance(seg,dict) or not isinstance(seg.get("text"),str): return {"status":"invalid_segment"}
        a,b=seg.get("offset"),seg.get("duration")
        if not isinstance(a,(int,float)) or not isinstance(b,(int,float)) or a<0 or b<0: return {"status":"invalid_timestamp"}
        starts.append(a); end=max(end,a+b); chars+=len(seg["text"])
    if starts!=sorted(starts): return {"status":"invalid_order"}
    if not chars:return {"status":"invalid_or_empty"}
    coverage=end/(duration_s*1000) if duration_s else None
    status="coverage_ok_unreviewed" if coverage is not None and .90<=coverage<=1.10 else "coverage_review"
    return {"status":status,"segments":len(content),"chars":chars,"first_ms":starts[0],"last_ms":end,"end_fraction":coverage}
def http(url,key):
    req=urllib.request.Request(url,headers={"x-api-key":key,"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=45) as r:
            return r.status,json.load(r),r.headers.get("x-billable-requests")
    except urllib.error.HTTPError as e:
        return e.code,{},e.headers.get("x-billable-requests")
def run(catalog,out,limit,monthly_cap,execute):
    if not 1<=limit<=100 or not 1<=monthly_cap<=100:raise ValueError("limits must be 1..100")
    if not out.is_absolute():raise ValueError("use an absolute private output path")
    if not execute:
        print("Dry run: no requests. Use --execute only after confirming private storage, access rights and free plan quota.");return
    key=os.environ.get("SUPADATA_API_KEY")
    if not key:raise SystemExit("SUPADATA_API_KEY missing")
    out.mkdir(parents=True,exist_ok=True)
    ledger_path=out/"attempts.json";ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    month=now().strftime("%Y-%m");spent=sum(1 for r in ledger if r["month"]==month)
    seen={r["video_id"] for r in ledger}
    attempts=0
    with catalog.open(encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            vid=row["video_id"]
            if not ID.fullmatch(vid) or vid in seen or row.get("episode_status")=="excluded":continue
            if attempts>=limit or spent>=monthly_cap:break
            d=float(row.get("duration_seconds") or 0)
            record={"video_id":vid,"month":month,"utc":now().isoformat(),"status":"started"}
            ledger.append(record);dump(ledger_path,ledger);attempts+=1;spent+=1;seen.add(vid)
            try:
                code,data,bill=http(build_url(vid),key);record.update(http_status=code,billable=bill)
                if code==202:
                    job=data.get("jobId","")
                    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}",job):raise ValueError("invalid job id")
                    for _ in range(30):
                        time.sleep(2);code,data,_=http(ROOT+"/"+job,key)
                        if code!=200 or data.get("status") in ("failed","completed"):break
                    if data.get("status")=="completed":
                        data=data.get("result",data)
                    else:
                        record["status"]="job_not_completed";dump(ledger_path,ledger);break
                if code!=200:
                    record["status"]="unavailable" if code==206 else "http_error"
                    dump(ledger_path,ledger)
                    if code in (401,402,403,429) or code>=500:break
                    time.sleep(1.1);continue
                review=validate(data,d);record.update(review)
                if review["status"] in ("coverage_ok_unreviewed","coverage_review"):
                    raw=json.dumps(data,ensure_ascii=False,separators=(",",":")).encode("utf-8")
                    atomic(out/(vid+".json"),raw)
                    record.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
                dump(ledger_path,ledger)
                print(vid,record["status"],record.get("segments",0))
                time.sleep(1.1)
            except Exception as e:
                record["status"]="error_"+type(e).__name__;dump(ledger_path,ledger);break
    print("Requests attempted:",attempts,"Local monthly count:",spent)
def main():
    p=argparse.ArgumentParser();p.add_argument("catalog",type=Path);p.add_argument("output",type=Path)
    p.add_argument("--limit",type=int,default=3);p.add_argument("--monthly-cap",type=int,default=95);p.add_argument("--execute",action="store_true")
    a=p.parse_args();run(a.catalog,a.output,a.limit,a.monthly_cap,a.execute)
if __name__=="__main__":main()
