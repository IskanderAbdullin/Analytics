import json,urllib.request,urllib.error
id="aLM-8X7VRyo"
out={}
for label,url in [("oembed","https://www.youtube.com/oembed?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D"+id+"&format=json"),("watch","https://www.youtube.com/watch?v="+id)]:
 try:
  with urllib.request.urlopen(url,timeout=15) as r:
   body=r.read(4000000).decode("utf-8","replace")
   out[label]={"status":r.status,"caption_tracks":'"captionTracks"' in body,"length":len(body),"bot_message":"confirm you're not a bot" in body.lower()}
 except Exception as e: out[label]={"error":type(e).__name__,"status":getattr(e,"code",None)}
try:
 from youtube_transcript_api import YouTubeTranscriptApi
 tr=YouTubeTranscriptApi().fetch(id,languages=["ru"])
 out["captions"]={"segments":len(tr),"last_end":max((s.start+s.duration for s in tr),default=0)}
except Exception as e: out["captions"]={"error":type(e).__name__}
print(json.dumps(out))
