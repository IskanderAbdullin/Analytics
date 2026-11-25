"""Integration test of documented public FreeTranscriptAPI, private KV only."""
import datetime,hashlib,json,os,re,time,urllib.request,urllib.error,urllib.parse
NS="1468098312aa47c995e87ff51252a38a"
API="https://api.freetranscriptapi.com/v1/transcript"
CASES=[("aLM-8X7VRyo",10245),("Mz2iGw8Zcek",9696),("Z3mNOytc-W4",1502)]
# Middle pilot duration is supplied by catalog at workflow setup, never infer.
def req(method,url,data=None,headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers or {},method=method),timeout=60) as r:
            return r.status,r.read(12*1024*1024),dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code,e.read(4096),dict(e.headers)
def log(**kw):print("NATIVE_PILOT "+json.dumps(kw,ensure_ascii=False),flush=True)
def main():
    account=os.environ["CLOUDFLARE_ACCOUNT_ID"];token=os.environ["CLOUDFLARE_API_TOKEN"]
    base="https://api.cloudflare.com/client/v4/accounts/"+account+"/storage/kv/namespaces/"+NS+"/values/"
    auth={"Authorization":"Bearer "+token}
    for vid,duration in CASES:
        key="native/youtube/"+vid+"/fta-v1.json"
        dst=base+urllib.parse.quote(key,safe="")
        code,old,_=req("GET",dst,headers=auth)
        if code==200:
            log(video_id=vid,status="already_exists",sha256=hashlib.sha256(old).hexdigest(),bytes=len(old));continue
        if code!=404:log(video_id=vid,status="kv_lookup_failed",http=code);break
        url=API+"?"+urllib.parse.urlencode({"video_url":vid,"lang":"ru","format":"json"})
        code,b,h=req("GET",url,headers={"Accept":"application/json","User-Agent":"DNS-Research-Integration-Test/1.0"})
        remaining=next((v for k,v in h.items() if k.lower()=="x-ratelimit-remaining"),None)
        if code!=200:
            try:err=json.loads(b).get("error",{}).get("code","unknown")
            except Exception:err="unknown"
            log(video_id=vid,status="provider_error",http=code,error_code=err,remaining=remaining)
            if code in (401,402,403,429) or code>=500:break
            continue
        d=json.loads(b);lines=d.get("transcript",[]);lang=d.get("language")
        if lang not in ("ru","ru-RU") or not isinstance(lines,list) or not lines:
            log(video_id=vid,status="wrong_language_or_empty",language=lang,remaining=remaining);continue
        try:
            starts=[float(x["start"]) for x in lines];ends=[float(x["start"])+float(x["duration"]) for x in lines]
            chars=sum(len(x["text"]) for x in lines)
            assert all(x>=0 for x in starts) and all(b>=a for a,b in zip(starts,ends)) and starts==sorted(starts) and chars>0
        except Exception:
            log(video_id=vid,status="invalid_timing");continue
        first=starts[0];last=max(ends);ratio=last/duration
        status="coverage_ok_unreviewed" if .95<=ratio<=1.05 and first<60 else "coverage_review"
        obj={"schema_version":1,"source":"FreeTranscriptAPI public native captions","video_id":vid,"expected_duration_s":duration,"retrieved_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"language":lang,"first_s":first,"last_s":last,"review_status":status,"response":d}
        payload=json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode()
        sha=hashlib.sha256(payload).hexdigest()
        if len(payload)>4*1024*1024:log(video_id=vid,status="size_limit");continue
        code,_,_=req("PUT",dst,payload,{**auth,"Content-Type":"application/octet-stream"})
        if code not in (200,201):log(video_id=vid,status="kv_put_failed",http=code);break
        code,check,_=req("GET",dst,headers=auth)
        if code!=200 or hashlib.sha256(check).hexdigest()!=sha:log(video_id=vid,status="kv_readback_failed",http=code);break
        log(video_id=vid,status="archived_verified",coverage=status,language=lang,segments=len(lines),chars=chars,first=first,last=last,expected_duration_s=duration,coverage_fraction=round(ratio,5),bytes=len(payload),sha256=sha,key=key,remaining=remaining)
        time.sleep(3)
if __name__=="__main__":main()
