"""Bounded private queue ingestion; public CI logs contain only receipts."""
import json,os,secrets,hashlib,urllib.request,urllib.error,urllib.parse,time
from pathlib import Path
ACCOUNT=os.environ["CLOUDFLARE_ACCOUNT_ID"];TOKEN=os.environ["CLOUDFLARE_API_TOKEN"]
NS="1468098312aa47c995e87ff51252a38a";RUN=os.environ["GITHUB_RUN_ID"];NAME="dns-native-queue-"+RUN
BASE="https://api.cloudflare.com/client/v4/accounts/"+ACCOUNT
AUTH={"Authorization":"Bearer "+TOKEN}
CASES=["GIrQV9wMNbg","EHQ-x9o_du0","eR50OM6pJ0w","mxjn-YS4Xmk","bzYnZmxx7DU","Uk8NcpRDJQo","op9ecP91oRM","s2fkkIUbZ1U","-0UN91Y3gDw","tdxriMnhuzQ","tdE-yYnduTg","O2lfVD8TYjs"]
def cf(method,path,data=None,ctype=None):
 h=dict(AUTH)
 if ctype:h["Content-Type"]=ctype
 try:
  with urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=h,method=method),timeout=30) as r:return r.status,r.read(8*1024*1024)
 except urllib.error.HTTPError as e:return e.code,e.read(4096)
def log(**kw):print("QUEUE_NATIVE "+json.dumps(kw,ensure_ascii=False),flush=True)
def j(method,path,obj):return cf(method,path,json.dumps(obj).encode(),"application/json")
def val(key):return "/storage/kv/namespaces/"+NS+"/values/"+urllib.parse.quote(key,safe="")
def main():
 path="/workers/scripts/"+NAME
 code,_=cf("GET",path)
 if code!=404:log(status="worker_name_not_free",http=code);return
 queue_id=None;worker_created=False
 try:
  code,b=j("POST","/queues",{"queue_name":NAME});log(status="queue_create",http=code)
  if code not in (200,201):return
  queue_id=json.loads(b)["result"]["queue_id"];q="/queues/"+queue_id
  bnd="Boundary"+secrets.token_hex(16)
  meta={"main_module":"worker.mjs","compatibility_date":"2026-11-01","bindings":[{"type":"kv_namespace","name":"CORPUS","namespace_id":NS}]}
  data=(f"--{bnd}\r\nContent-Disposition: form-data; name=\"metadata\"\r\nContent-Type: application/json\r\n\r\n"+json.dumps(meta)+f"\r\n--{bnd}\r\nContent-Disposition: form-data; name=\"worker.mjs\"; filename=\"worker.mjs\"\r\nContent-Type: application/javascript+module\r\n\r\n").encode()+Path(__file__).with_name("worker.mjs").read_bytes()+f"\r\n--{bnd}--\r\n".encode()
  code,_=cf("PUT",path,data,"multipart/form-data; boundary="+bnd);log(status="worker_deploy",http=code)
  if code not in (200,201):return
  worker_created=True
  code,_=j("POST",path+"/subdomain",{"enabled":False});log(status="public_endpoint_disabled",http=code)
  if code!=200:return
  code,_=j("POST",q+"/consumers",{"type":"worker","script_name":NAME,"settings":{"batch_size":1,"max_concurrency":1,"max_retries":0,"max_wait_time_ms":1000}});log(status="consumer_create",http=code)
  if code not in (200,201):return
  for vid in CASES:
   code,_=j("POST",q+"/messages",{"body":{"run_id":RUN,"video_id":vid},"content_type":"json"});log(status="message_sent",video_id=vid,http=code)
   if code not in (200,201):break
   receipt="receipt/queue/"+RUN+"/"+vid
   d=None
   for _ in range(18):
    time.sleep(3)
    code,raw=cf("GET",val(receipt))
    if code==200:
     d=json.loads(raw);break
    if code!=404:break
   if d is None:log(video_id=vid,status="receipt_not_observed",http=code);break
   if d.get("status") in ("stored_pending_readback","already_exists"):
    code,raw=cf("GET",val(d["key"]))
    if code!=200 or hashlib.sha256(raw).hexdigest()!=d["sha256"]:log(video_id=vid,status="readback_failure",http=code);break
    d["status"]="archived_verified" if d["status"]=="stored_pending_readback" else "already_verified"
   log(**d)
   cf("DELETE",val(receipt))
   if d.get("status")=="provider_error" and (d.get("http") in (401,402,403,429) or d.get("http",0)>=500):break
   if d.get("status")=="worker_error" or d.get("remaining")=="0":break
 finally:
  if queue_id:
   code,_=cf("DELETE","/queues/"+queue_id);log(status="queue_cleanup",http=code)
  if worker_created:
   code,_=cf("DELETE",path);log(status="worker_cleanup",http=code)
if __name__=="__main__":main()
