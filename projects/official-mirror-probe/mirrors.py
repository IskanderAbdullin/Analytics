import json,urllib.request,urllib.parse,xml.etree.ElementTree as ET,subprocess,sys
try:
 with urllib.request.urlopen("https://itunes.apple.com/lookup?id=1844555056&country=ru",timeout=20) as r:d=json.load(r)
 feed=d["results"][0]["feedUrl"];u=urllib.parse.urlparse(feed)
 if u.scheme!="https" or not (u.hostname=="mave.digital" or u.hostname.endswith(".mave.digital")):raise ValueError("unexpected feed host")
 with urllib.request.urlopen(feed,timeout=20) as r:root=ET.fromstring(r.read(12000000))
 items=root.findall("./channel/item")
 for e in items:
  enc=e.find("enclosure");tags=[x for x in e if x.tag.endswith("}transcript")]
  print("PODCAST_ROW "+json.dumps({"title":e.findtext("title"),"date":e.findtext("pubDate"),"guid":e.findtext("guid"),"episode_link":e.findtext("link"),"has_audio_enclosure":enc is not None,"audio_type":enc.get("type") if enc is not None else None,"transcript_tags":len(tags)},ensure_ascii=False),flush=True)
 print("PODCAST_COUNT",len(items),"FEED",feed,flush=True)
except Exception as e:print("PODCAST_ERROR",type(e).__name__,flush=True)
try:
 p=subprocess.run([sys.executable,"-m","yt_dlp","--flat-playlist","--dump-single-json","--no-warnings","--skip-download","https://rutube.ru/plst/817584/"],capture_output=True,text=True,timeout=100)
 if p.returncode:print("RUTUBE_ERROR",p.returncode,p.stderr[:500].replace("\n"," "),flush=True)
 else:
  rows=json.loads(p.stdout).get("entries",[])
  for e in rows:
   if e and e.get("id"):print("RUTUBE_ROW "+json.dumps({k:e.get(k) for k in ("id","title","duration","timestamp","upload_date","url")},ensure_ascii=False),flush=True)
  print("RUTUBE_COUNT",len(rows),flush=True)
except Exception as e:print("RUTUBE_ERROR",type(e).__name__,flush=True)
try:
 p=subprocess.run([sys.executable,"-m","yt_dlp","--skip-download","--dump-single-json","--no-warnings","https://rutube.ru/video/ec36e038f1101c660af7d615d23dd36e/"],capture_output=True,text=True,timeout=45)
 if p.returncode:print("RUTUBE_CAPTIONS_ERROR",p.returncode,p.stderr[:400].replace("\n"," "),flush=True)
 else:
  d=json.loads(p.stdout)
  print("RUTUBE_CAPTIONS",json.dumps({"id":d.get("id"),"duration":d.get("duration"),"subtitles":list((d.get("subtitles") or {}).keys()),"automatic_captions":list((d.get("automatic_captions") or {}).keys())}),flush=True)
except Exception as e:print("RUTUBE_CAPTIONS_ERROR",type(e).__name__,flush=True)
