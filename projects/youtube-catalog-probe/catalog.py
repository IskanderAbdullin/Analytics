import json,subprocess,sys
channel="https://www.youtube.com/channel/UCo1RPtO57Izwy2wjBmPMjCw"
for tab in ("streams","videos"):
 try:
  p=subprocess.run([sys.executable,"-m","yt_dlp","--flat-playlist","--extractor-args","youtubetab:approximate_date","--dump-single-json","--no-warnings","--skip-download",channel+"/"+tab],capture_output=True,text=True,timeout=100)
  if p.returncode:
   print("CATALOG_ERROR",tab,p.returncode,p.stderr[:500].replace("\n"," "),flush=True);continue
  d=json.loads(p.stdout); rows=d.get("entries",[])
  for e in rows:
   if e and e.get("id"):
    print("CATALOG_ROW "+json.dumps({k:e.get(k) for k in ("id","title","duration","timestamp","upload_date","live_status")}|{"tab":tab},ensure_ascii=False),flush=True)
  print("CATALOG_COUNT",tab,len(rows),flush=True)
 except Exception as e: print("CATALOG_ERROR",tab,type(e).__name__,flush=True)
