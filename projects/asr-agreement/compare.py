"""Bounded ASR agreement benchmark. Native captions are a noisy reference, not ground truth."""
import os,json,hashlib,subprocess,urllib.request,urllib.parse,xml.etree.ElementTree as ET,re,tempfile,time,wave
from pathlib import Path
import imageio_ffmpeg,numpy as np
from faster_whisper import WhisperModel
GUID="533a5c34-eca2-4ff3-9689-9e0e7c758b8e";VIDEO="aLM-8X7VRyo"
FEED="https://cloud.mave.digital/66566";NS="1468098312aa47c995e87ff51252a38a"
SAMPLES=[(0,60),(7650,60),(7810,60)]
def norm(text):return re.findall(r"[а-яa-z0-9]+",text.lower().replace("ё","е"))
def distance(a,b):
 p=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  q=[i]
  for j,y in enumerate(b,1):q.append(min(p[j]+1,q[-1]+1,p[j-1]+(x!=y)))
  p=q
 return p[-1]
def score(ref,hyp):
 return distance(ref,hyp)/max(1,len(ref))
def main():
 account=os.environ["CLOUDFLARE_ACCOUNT_ID"];token=os.environ["CLOUDFLARE_API_TOKEN"]
 key=urllib.parse.quote("native/youtube/"+VIDEO+"/fta-v1.json",safe="")
 url=f"https://api.cloudflare.com/client/v4/accounts/{account}/storage/kv/namespaces/{NS}/values/{key}"
 with urllib.request.urlopen(urllib.request.Request(url,headers={"Authorization":"Bearer "+token}),timeout=30) as r:raw=r.read(4*1024*1024)
 assert hashlib.sha256(raw).hexdigest()=="5a669f4c623e43fb4eb6453f5bc755b1363a456b69cb022325b63f2ab54842bd"
 captions=json.loads(raw)["response"]["transcript"]
 with urllib.request.urlopen(FEED,timeout=20) as r:root=ET.fromstring(r.read(12000000))
 item=next(e for e in root.findall("./channel/item") if e.findtext("guid")==GUID)
 audio=item.find("enclosure").get("url")
 assert urllib.parse.urlparse(audio).scheme=="https"
 model=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=2,num_workers=1)
 for start,duration in SAMPLES:
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"sample.wav"
   r=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-nostdin","-v","error","-ss",str(start),"-i",audio,"-t",str(duration),"-vn","-ac","1","-ar","16000",str(path)],capture_output=True,timeout=120)
   if r.returncode:print("ASR_COMPARE "+json.dumps({"start":start,"status":"decode_failed"}),flush=True);continue
   with wave.open(str(path),"rb") as w:
    length=w.getnframes()/16000
    x=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").astype(np.float32)/32768
   if length<duration-2:print("ASR_COMPARE "+json.dumps({"start":start,"status":"short_audio","duration":length}),flush=True);continue
   t=time.monotonic();it,_=model.transcribe(x,language="ru",beam_size=3,vad_filter=True);segs=list(it);elapsed=time.monotonic()-t
   hyp=norm(" ".join(s.text for s in segs))
   results=[]
   # Allow small alignment offsets; report the best and zero-offset agreement.
   # This is exploratory and does not establish absolute ASR accuracy.
   for offset in range(-20,21,2):
    ref=norm(" ".join(c["text"] for c in captions if start+offset<=c["start"]<start+offset+duration))
    if not ref:continue
    results.append((score(ref,hyp),offset,len(ref),ref))
   if not results:continue
   best=min(results,key=lambda z:z[0]);zero=next((x[0] for x in results if x[1]==0),None)
   nref=[w for w in best[3] if w.isdigit()];nhyp=[w for w in hyp if w.isdigit()]
   print("ASR_COMPARE "+json.dumps({"start":start,"duration":length,"status":"compared","asr_words":len(hyp),"ref_words":best[2],"best_offset_s":best[1],"word_disagreement":round(best[0],4),"zero_offset_disagreement":round(zero,4) if zero is not None else None,"numeric_token_reference_count":len(nref),"numeric_token_asr_count":len(nhyp),"numeric_sequence_disagreement":round(score(nref,nhyp),4) if nref else None,"recognition_seconds":round(elapsed,2)},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
