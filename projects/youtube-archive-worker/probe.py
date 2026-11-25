#!/usr/bin/env python3
"""Read-only diagnosis of this Worker; no tokens, headers with credentials or private data in logs."""
import os,json,urllib.request,urllib.error,urllib.parse,fnmatch
NAME="youtube-archive-owner"
root="https://api.cloudflare.com/client/v4/accounts/"+os.environ["CLOUDFLARE_ACCOUNT_ID"]
token=os.environ["CLOUDFLARE_API_TOKEN"]
def cf(path):
    req=urllib.request.Request(root+path,headers={"Authorization":"Bearer "+token})
    try:
        with urllib.request.urlopen(req,timeout=20) as resp: result=json.load(resp)
        if not result.get("success"): return None,"api_failure"
        return result.get("result"),"ok"
    except urllib.error.HTTPError as e: return None,"http_"+str(e.code)
scripts,s=cf("/workers/scripts")
print("script_inventory:",s,"exact_match:",any(x.get("id")==NAME for x in (scripts or [])))
sub,s=cf("/workers/subdomain")
if not sub or not sub.get("subdomain"): raise SystemExit("Account subdomain unavailable")
host=NAME+"."+sub["subdomain"]+".workers.dev"
route,s=cf("/workers/scripts/"+NAME+"/subdomain")
print("worker_subdomain:",s,"enabled:",(route or {}).get("enabled"),"previews:",(route or {}).get("previews_enabled"))
apps,s=cf("/access/apps?per_page=100")
matches=0
if isinstance(apps,list):
    for app in apps:
        domains=[app.get("domain","")]+[d.get("uri","") for d in app.get("destinations",[]) if isinstance(d,dict)]
        if any(fnmatch.fnmatch(host, urllib.parse.urlsplit("https://"+d.removeprefix("https://").removeprefix("http://")).hostname or "") for d in domains if isinstance(d,str) and d): matches+=1
print("access_app_lookup:",s,"matching_host_count:",matches if s=="ok" else "unknown")
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None
opener=urllib.request.build_opener(NoRedirect)
def http(path,method="GET",payload=None):
    req=urllib.request.Request("https://"+host+path,data=json.dumps(payload).encode() if payload is not None else None,method=method,headers={"Accept":"application/json","Content-Type":"application/json","User-Agent":"YouTubeArchiveHealth/1.0"})
    try:
        with opener.open(req,timeout=15) as res: return res.status,res.headers,res.read(16384)
    except urllib.error.HTTPError as e: return e.code,e.headers,e.read(16384)
def report(label,resp):
    status,headers,body=resp
    lower=body.decode("utf-8","replace").lower()
    loc=urllib.parse.urlsplit(headers.get("location","")).hostname or ""
    signatures={"access": "cloudflareaccess.com" in loc or "cloudflare access" in lower,"challenge":headers.get("cf-mitigated")=="challenge" or "just a moment" in lower,"error_1020":"1020" in lower,"error_1015":"1015" in lower,"error_1101":"1101" in lower,"worker_health":'"service":"youtube-archive"' in lower}
    print(label,"status:",status,"content_type:",headers.get("content-type","").split(";")[0],"signatures:",json.dumps(signatures,sort_keys=True))
health=http("/healthz");report("health",health)
if health[0]==200:
    for name,method,params in [("discovery","tools/list",{}),("no_auth","tools/call",{"name":"youtube_owner_channels"})]:
        resp=http("/mcp","POST",{"jsonrpc":"2.0","id":1,"method":method,"params":params});report(name,resp)
        if name=="discovery": assert len(json.loads(resp[2])["result"]["tools"])==4
        else: assert resp[0]==401
else:
    print("Public health is blocked; no changes attempted.")
