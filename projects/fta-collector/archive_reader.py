"""Authenticated private archive reader. Never run text-output mode in public CI."""
import argparse,hashlib,json,os,urllib.request,urllib.parse,re
from pathlib import Path
NS="1468098312aa47c995e87ff51252a38a"
ID=re.compile(r"^[A-Za-z0-9_-]{11}$")
def read_window(record,start,end):
    if not 0<=start<end:raise ValueError("invalid interval")
    lines=record["response"]["transcript"]
    return [x for x in lines if x["start"]<end and x["start"]+x["duration"]>=start]
def fetch(vid,expected_hash):
    if not ID.fullmatch(vid):raise ValueError("invalid video ID")
    account=os.environ["CLOUDFLARE_ACCOUNT_ID"];token=os.environ["CLOUDFLARE_API_TOKEN"]
    key=urllib.parse.quote("native/youtube/"+vid+"/fta-v1.json",safe="")
    url="https://api.cloudflare.com/client/v4/accounts/"+account+"/storage/kv/namespaces/"+NS+"/values/"+key
    with urllib.request.urlopen(urllib.request.Request(url,headers={"Authorization":"Bearer "+token}),timeout=30) as r:raw=r.read(8*1024*1024)
    digest=hashlib.sha256(raw).hexdigest()
    if expected_hash and digest!=expected_hash:raise ValueError("SHA256 mismatch")
    record=json.loads(raw)
    if record["video_id"]!=vid:raise ValueError("video ID mismatch")
    return record,digest
def main():
    p=argparse.ArgumentParser();p.add_argument("video_id");p.add_argument("--expected-sha256")
    p.add_argument("--start",type=float,default=0);p.add_argument("--end",type=float,default=3600)
    p.add_argument("--private-output",type=Path);a=p.parse_args()
    record,digest=fetch(a.video_id,a.expected_sha256);lines=read_window(record,a.start,a.end)
    if a.private_output:
        if not a.private_output.is_absolute():raise ValueError("private output path must be absolute")
        a.private_output.write_text(json.dumps({"video_id":a.video_id,"source_sha256":digest,"segments":lines},ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"video_id":a.video_id,"sha256":digest,"window":[a.start,a.end],"segments":len(lines),"private_output_written":bool(a.private_output)}))
if __name__=="__main__":main()
