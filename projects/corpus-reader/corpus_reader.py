"""Verified, source-neutral private corpus reader. Outputs metadata unless a private path is provided."""
import argparse,hashlib,json,math,os,re,urllib.request,urllib.parse
from pathlib import Path
NS="1468098312aa47c995e87ff51252a38a"
ID=re.compile(r"^[A-Za-z0-9_-]{11}$")
def normalize(raw,receipt):
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=receipt["sha256"]:raise ValueError("SHA256 mismatch")
    doc=json.loads(raw);vid=receipt["video_id"]
    if not ID.fullmatch(vid):raise ValueError("invalid video ID")
    if doc.get("video_id",doc.get("youtube_id_candidate"))!=vid:raise ValueError("video ID mismatch")
    if doc.get("language")!="ru":raise ValueError("unexpected language")
    native="response" in doc
    if not native and doc.get("podcast_guid")!=receipt.get("podcast_guid"):raise ValueError("podcast GUID mismatch")
    src=doc["response"]["transcript"] if native else doc["segments"]
    segments=[]
    for i,s in enumerate(src):
        start=float(s["start"]);end=start+float(s["duration"]) if native else float(s["end"])
        if not(math.isfinite(start) and math.isfinite(end) and 0<=start<=end):raise ValueError("invalid timestamps")
        if not isinstance(s["text"],str):raise ValueError("invalid text")
        if segments and start<segments[-1]["start"]:raise ValueError("non-monotonic segment order")
        segments.append({"index":i,"start":start,"end":end,"text":s["text"]})
    if not segments or not any(s["text"].strip() for s in segments):raise ValueError("empty transcript")
    duration=float(doc.get("audio_duration_s",doc.get("expected_duration_s",receipt["expected_duration_s"])))
    if not math.isfinite(duration) or duration<=0:raise ValueError("invalid duration")
    return {"schema_version":1,"video_id":vid,"source":receipt["source"],"source_sha256":digest,"timeline":"youtube" if native else "podcast_audio_not_verified_equal_to_youtube","duration_s":duration,"title":doc.get("title",doc.get("response",{}).get("title")),"language":"ru","segments":segments}
def metrics(record):
    seg=record["segments"];duration=record["duration_s"];end=0.;covered=0.;gap=0.;overlaps=0
    for s in seg:
        a,b=s["start"],s["end"]
        gap=max(gap,a-end)
        if a<end:overlaps+=1
        covered+=max(0,min(b,duration)-max(a,end))
        end=max(end,b)
    gap=max(gap,duration-end)
    return {"video_id":record["video_id"],"source":record["source"],"source_sha256":record["source_sha256"],"timeline":record["timeline"],"segments":len(seg),"duration_s":duration,"first_s":seg[0]["start"],"last_s":end,"coverage_fraction":round(covered/duration,5),"largest_gap_s":round(gap,3),"overlapping_segments":overlaps,"characters":sum(len(x["text"]) for x in seg)}
def read_window(record,start,end):
    if not(math.isfinite(start) and math.isfinite(end) and 0<=start<end):raise ValueError("invalid interval")
    return [s for s in record["segments"] if s["start"]<end and s["end"]>start]
def fetch(receipt):
    vid=receipt["video_id"];key=receipt["key"]
    if not ID.fullmatch(vid) or not re.fullmatch(r"(?:native/youtube/[A-Za-z0-9_-]{11}/[a-z0-9-]+\.json|asr/podcast/[a-f0-9-]{36}/[a-z0-9-]+\.json)",key):raise ValueError("invalid archive key")
    if key.startswith("native/") and key.split("/")[2]!=vid:raise ValueError("key/video mismatch")
    if key.startswith("asr/") and key.split("/")[2]!=receipt.get("podcast_guid"):raise ValueError("key/podcast mismatch")
    account=os.environ["CLOUDFLARE_ACCOUNT_ID"];token=os.environ["CLOUDFLARE_API_TOKEN"]
    url=f"https://api.cloudflare.com/client/v4/accounts/{account}/storage/kv/namespaces/{NS}/values/"+urllib.parse.quote(key,safe="")
    with urllib.request.urlopen(urllib.request.Request(url,headers={"Authorization":"Bearer "+token}),timeout=30) as r:raw=r.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise ValueError("archive record too large")
    return normalize(raw,receipt)
def main():
    p=argparse.ArgumentParser();p.add_argument("manifest",type=Path);p.add_argument("--video-id");p.add_argument("--start",type=float,default=0);p.add_argument("--end",type=float);p.add_argument("--private-output",type=Path);a=p.parse_args()
    if a.private_output and (not a.video_id or not a.private_output.is_absolute()):raise ValueError("private absolute output and single video ID required")
    receipts=[json.loads(x) for x in a.manifest.read_text(encoding="utf-8").splitlines() if x.strip()]
    if a.video_id:receipts=[r for r in receipts if r["video_id"]==a.video_id]
    if not receipts:raise ValueError("no matching receipt")
    for receipt in receipts:
        record=fetch(receipt);m=metrics(record)
        if a.private_output:
            record["segments"]=read_window(record,a.start,a.end if a.end is not None else record["duration_s"]+1)
            a.private_output.write_text(json.dumps(record,ensure_ascii=False),encoding="utf-8")
            m["private_output_written"]=True
        print("CORPUS_METRIC "+json.dumps(m,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
