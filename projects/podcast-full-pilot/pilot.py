"""One full-episode integration test of the private transcript pipeline.
Only public official RSS audio; no full text in logs or public artifacts.
"""
import datetime,hashlib,json,os,re,subprocess,tempfile,time,urllib.request,urllib.error,urllib.parse,wave,xml.etree.ElementTree as ET
from pathlib import Path
import imageio_ffmpeg
import numpy as np
from faster_whisper import WhisperModel
FEED="https://cloud.mave.digital/66566"
GUID="f0699e9e-ba27-452a-aa5d-8a34ab028ffe"
VIDEO_ID="VVhbZkLqKfo"
EXPECTED=4436
NS="1468098312aa47c995e87ff51252a38a"
KEY="asr/podcast/"+GUID+"/small-int8-v1.json"
def request(method,url,data=None,headers=None,timeout=40):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers or {},method=method),timeout=timeout) as r:
            return r.status,r.read(30*1024*1024)
    except urllib.error.HTTPError as e:
        return e.code,b""
def report(stage,**kw):
    print("PILOT "+json.dumps({"stage":stage,**kw},ensure_ascii=False),flush=True)
def main():
    token=os.environ["CLOUDFLARE_API_TOKEN"]
    account=os.environ["CLOUDFLARE_ACCOUNT_ID"]
    base="https://api.cloudflare.com/client/v4/accounts/"+account+"/storage/kv/namespaces/"+NS+"/values/"+urllib.parse.quote(KEY,safe="")
    auth={"Authorization":"Bearer "+token}
    code,old=request("GET",base,headers=auth)
    if code==200:
        report("already_exists",sha256=hashlib.sha256(old).hexdigest(),bytes=len(old));return
    if code!=404:raise RuntimeError("KV lookup failed: "+str(code))
    code,raw=request("GET",FEED)
    if code!=200:raise RuntimeError("RSS inaccessible")
    root=ET.fromstring(raw)
    item=next(e for e in root.findall("./channel/item") if e.findtext("guid")==GUID)
    audio=item.find("enclosure").get("url")
    if urllib.parse.urlparse(audio).scheme!="https":raise ValueError("unexpected enclosure")
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"episode.wav"
        started=time.monotonic()
        result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-nostdin","-v","error","-i",audio,"-t",str(EXPECTED+180),"-vn","-ac","1","-ar","16000",str(path)],capture_output=True,timeout=300)
        if result.returncode:raise RuntimeError("audio decode failed")
        with wave.open(str(path),"rb") as w:
            assert w.getframerate()==16000 and w.getnchannels()==1 and w.getsampwidth()==2
            duration=w.getnframes()/16000
            if not EXPECTED*.95<=duration<=EXPECTED*1.04 or duration>=EXPECTED+179:
                report("duration_mismatch",actual=duration,expected=EXPECTED);raise RuntimeError("audio duration mismatch or cap reached")
            samples=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").astype(np.float32)/32768.
        report("decoded",duration=round(duration,2),seconds=round(time.monotonic()-started,2))
        model=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=2,num_workers=1)
        started=time.monotonic()
        it,info=model.transcribe(samples,language="ru",beam_size=3,vad_filter=True)
        segments=[]
        for s in it:
            segments.append({"start":round(s.start,3),"end":round(s.end,3),"text":s.text.strip(),"avg_logprob":round(s.avg_logprob,4),"no_speech_prob":round(s.no_speech_prob,4)})
        elapsed=time.monotonic()-started
        if not segments or any(s["start"]<0 or s["end"]<s["start"] for s in segments):raise RuntimeError("invalid segment timing")
        if any(b["start"]<a["start"] for a,b in zip(segments,segments[1:])):raise RuntimeError("nonmonotonic timestamps")
        last=max(s["end"] for s in segments);first=segments[0]["start"]
        if first>60 or last<duration*.95 or last>duration+2:raise RuntimeError("insufficient timing coverage")
        obj={"schema_version":1,"source":"official_podcast_rss","rss":FEED,"podcast_guid":GUID,"youtube_id_candidate":VIDEO_ID,"title":item.findtext("title"),"source_publication_date":item.findtext("pubDate"),"retrieved_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"audio_duration_s":round(duration,3),"youtube_duration_s":EXPECTED,"timeline":"podcast_audio_not_verified_equal_to_youtube","model":"faster-whisper small int8","language":"ru","segments":segments,"review_status":"asr_unreviewed"}
        payload=json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode()
        if len(payload)>2*1024*1024:raise RuntimeError("unexpected transcript size")
        digest=hashlib.sha256(payload).hexdigest()
        report("recognized",duration=round(duration,2),segments=len(segments),chars=sum(len(s["text"]) for s in segments),first=first,last=last,seconds=round(elapsed,2),rtf=round(elapsed/duration,4),bytes=len(payload),sha256=digest)
        code,_=request("PUT",base,payload,{**auth,"Content-Type":"application/octet-stream"})
        if code not in (200,201):raise RuntimeError("KV write failed: "+str(code))
        code,verified=request("GET",base,headers=auth)
        if code!=200 or hashlib.sha256(verified).hexdigest()!=digest:raise RuntimeError("KV readback failed")
        report("archived_verified",key=KEY,sha256=digest,bytes=len(payload),segments=len(segments),first=first,last=last,audio_duration_s=round(duration,2))
if __name__=="__main__":main()
