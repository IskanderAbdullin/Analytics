#!/usr/bin/env python3
"""Create only the declared independent Worker; never print secrets or private responses."""
import os, json, urllib.request, urllib.error, pathlib, uuid, re
NAME="youtube-archive-owner"
ROOT="https://api.cloudflare.com/client/v4"
account=os.environ["CLOUDFLARE_ACCOUNT_ID"]
token=os.environ["CLOUDFLARE_API_TOKEN"]
if not account or not token: raise SystemExit("Missing Cloudflare credentials")
def api(method,path,body=None,ctype="application/json"):
    req=urllib.request.Request(ROOT+"/accounts/"+account+path,data=body,method=method,headers={"Authorization":"Bearer "+token,"Content-Type":ctype})
    try:
        with urllib.request.urlopen(req,timeout=40) as r: out=json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit("Cloudflare API HTTP "+str(e.code)+" for "+method) from None
    if not out.get("success"): raise SystemExit("Cloudflare API reported failure")
    return out.get("result")
scripts=api("GET","/workers/scripts")
if any(x.get("id")==NAME for x in scripts): raise SystemExit("Worker already exists: refusing overwrite")
code=pathlib.Path(__file__).with_name("worker.mjs").read_bytes()
boundary=uuid.uuid4().hex
def part(name,filename,mime,content):
    return ("--"+boundary+"\r\nContent-Disposition: form-data; name=\""+name+"\""+("; filename=\""+filename+"\"" if filename else "")+"\r\nContent-Type: "+mime+"\r\n\r\n").encode()+content+b"\r\n"
metadata=json.dumps({"main_module":"worker.mjs","compatibility_date":"2026-11-25","observability":{"enabled":False}}).encode()
body=part("metadata",None,"application/json",metadata)+part("worker.mjs","worker.mjs","application/javascript+module",code)+("--"+boundary+"--\r\n").encode()
api("PUT","/workers/scripts/"+NAME,body,"multipart/form-data; boundary="+boundary)
print("Worker script uploaded:",NAME,flush=True)
sub=api("GET","/workers/subdomain")["subdomain"]
if not re.fullmatch(r"[a-z0-9-]+",sub): raise SystemExit("Unexpected subdomain")
api("POST","/workers/scripts/"+NAME+"/subdomain",json.dumps({"enabled":True,"previews_enabled":False}).encode())
base="https://"+NAME+"."+sub+".workers.dev"
print("Worker URL:",base,flush=True)
import time
for attempt in range(8):
    try:
        with urllib.request.urlopen(base+"/healthz",timeout=15) as f: health=json.load(f)
        assert health["service"]=="youtube-archive"
        break
    except Exception:
        if attempt==7: raise
        time.sleep(3)
def rpc(method,params=None):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or {}}).encode()
    req=urllib.request.Request(base+"/mcp",data=body,headers={"Content-Type":"application/json","Accept":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=20) as f: return f.status,json.load(f)
    except urllib.error.HTTPError as e: return e.code,None
assert rpc("tools/list")[1]["result"]["tools"][0]["name"]=="youtube_owner_channels"
assert rpc("tools/call",{"name":"youtube_owner_channels"})[0]==401
print("Smoke: health, tool discovery, unauthenticated request denied",flush=True)
