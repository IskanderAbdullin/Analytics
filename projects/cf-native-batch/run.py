"""One bounded Cloudflare collector run; public repo logs metadata only."""
import json, os, secrets, hashlib, urllib.request, urllib.error, urllib.parse, time, sys
from pathlib import Path
ACCOUNT=os.environ["CLOUDFLARE_ACCOUNT_ID"]
TOKEN=os.environ["CLOUDFLARE_API_TOKEN"]
NS="1468098312aa47c995e87ff51252a38a"
NAME="dns-native-pilot-"+os.environ["GITHUB_RUN_ID"]
BASE="https://api.cloudflare.com/client/v4/accounts/"+ACCOUNT
AUTH={"Authorization":"Bearer "+TOKEN}
CASES=["GIrQV9wMNbg","EHQ-x9o_du0","eR50OM6pJ0w","mxjn-YS4Xmk","bzYnZmxx7DU","Uk8NcpRDJQo","op9ecP91oRM","s2fkkIUbZ1U","-0UN91Y3gDw","tdxriMnhuzQ","tdE-yYnduTg","O2lfVD8TYjs"]
SECRET=secrets.token_urlsafe(32)
def req(method,url,body=None,headers=None,timeout=90):
 try:
  with urllib.request.urlopen(urllib.request.Request(url,data=body,headers=headers or {},method=method),timeout=timeout) as r:return r.status,r.read(8*1024*1024)
 except urllib.error.HTTPError as e:return e.code,e.read(4096)
def log(**kw):print("CF_NATIVE_BATCH "+json.dumps(kw,ensure_ascii=False),flush=True)
def cf(method,path,body=None,headers=None):
 return req(method,BASE+path,body,{**AUTH,**(headers or {})})
def main():
 path="/workers/scripts/"+NAME
 code,_=cf("GET",path)
 if code!=404:log(status="worker_name_not_free",http=code);return
 b="Boundary"+secrets.token_hex(16)
 meta={"main_module":"worker.mjs","compatibility_date":"2026-11-01","bindings":[{"type":"kv_namespace","name":"CORPUS","namespace_id":NS},{"type":"secret_text","name":"BATCH_TOKEN","text":SECRET}]}
 body=(f"--{b}\r\nContent-Disposition: form-data; name=\"metadata\"\r\nContent-Type: application/json\r\n\r\n"+json.dumps(meta)+f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"worker.mjs\"; filename=\"worker.mjs\"\r\nContent-Type: application/javascript+module\r\n\r\n").encode()+Path(__file__).with_name("worker.mjs").read_bytes()+f"\r\n--{b}--\r\n".encode()
 code,_=cf("PUT",path,body,{"Content-Type":"multipart/form-data; boundary="+b})
 log(status="worker_deploy",http=code)
 if code not in (200,201):return
 try:
  code,data=cf("POST",path+"/subdomain",b'{"enabled":true}',{"Content-Type":"application/json"})
  if code!=200:log(status="subdomain_enable_failed",http=code);return
  code,data=cf("GET","/workers/subdomain")
  if code!=200:log(status="account_subdomain_failed",http=code);return
  sub=json.loads(data)["result"]["subdomain"]
  url="https://"+NAME+"."+sub+".workers.dev/collect"
  time.sleep(6)
  for vid in CASES:
   code,b=req("POST",url,json.dumps({"video_id":vid}).encode(),{"Authorization":"Bearer "+SECRET,"Content-Type":"application/json"},timeout=90)
   if code!=200:log(video_id=vid,status="worker_http_error",http=code);break
   try:d=json.loads(b)
   except Exception:log(video_id=vid,status="worker_invalid_response");break
   if d.get("status") in ("stored_pending_readback","already_exists"):
    key=d["key"];status,contents=cf("GET","/storage/kv/namespaces/"+NS+"/values/"+urllib.parse.quote(key,safe=""))
    if status!=200 or hashlib.sha256(contents).hexdigest()!=d["sha256"]:log(video_id=vid,status="kv_readback_failed",http=status);break
    d["status"]="archived_verified" if d["status"]=="stored_pending_readback" else "already_verified"
   log(**d)
   if d.get("status")=="provider_error" and (d.get("http") in (401,402,403,429) or d.get("http",0)>=500):break
   if d.get("remaining")=="0":break
   time.sleep(5)
 finally:
  code,_=cf("DELETE",path);log(status="worker_cleanup",http=code)
if __name__=="__main__":main()
