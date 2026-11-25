import json,os,subprocess,sys,time,tempfile,urllib.request,urllib.parse,xml.etree.ElementTree as ET
from pathlib import Path
from faster_whisper import WhisperModel
import imageio_ffmpeg
FEED="https://cloud.mave.digital/66566"
GUID="533a5c34-eca2-4ff3-9689-9e0e7c758b8e"
with urllib.request.urlopen(FEED,timeout=20) as r:root=ET.fromstring(r.read(12000000))
item=next(e for e in root.findall("./channel/item") if e.findtext("guid")==GUID)
audio=item.find("enclosure").get("url")
if urllib.parse.urlparse(audio).scheme!="https":raise ValueError("unexpected enclosure")
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/"sample.wav"
 started=time.monotonic()
 r=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-nostdin","-v","error","-i",audio,"-t","90","-vn","-ac","1","-ar","16000",str(p)],capture_output=True,timeout=120)
 if r.returncode:print("ASR_PROBE "+json.dumps({"stage":"sample","error":"ffmpeg_failed","returncode":r.returncode}),flush=True);sys.exit(1)
 audio_time=time.monotonic()-started
 started=time.monotonic()
 model=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=2,num_workers=1)
 init_time=time.monotonic()-started
 started=time.monotonic()
 segments,info=model.transcribe(str(p),beam_size=3,vad_filter=True)
 seg=list(segments);sec=time.monotonic()-started
 chars=sum(len(s.text) for s in seg)
 print("ASR_PROBE "+json.dumps({"sample_seconds":90,"fetch_decode_seconds":round(audio_time,2),"model_load_seconds":round(init_time,2),"transcribe_seconds":round(sec,2),"rtf":round(sec/90,3),"language":info.language,"language_probability":round(info.language_probability,3),"segments":len(seg),"chars":chars,"last_end":round(max((s.end for s in seg),default=0),2),"cpu_threads":2,"model":"small/int8"}),flush=True)
