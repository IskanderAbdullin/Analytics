import os,json,hashlib,urllib.request,urllib.error
BASE="https://api.cloudflare.com/client/v4/accounts/"+os.environ["CLOUDFLARE_ACCOUNT_ID"]+"/storage/kv/namespaces"
TOKEN=os.environ["CLOUDFLARE_API_TOKEN"]; TITLE="dns-research-corpus-20261125"
def req(method,path,data=None,ctype=None):
 h={"Authorization":"Bearer "+TOKEN}
 if ctype:h["Content-Type"]=ctype
 try:
  with urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=h,method=method),timeout=20) as r:return r.status,r.read(2000000)
 except urllib.error.HTTPError as e:return e.code,e.read(2000000)
def status(label,code,b):
 try:
  j=json.loads(b);print("KV_RESULT",label,code,json.dumps({"success":j.get("success"),"error_codes":[x.get("code") for x in j.get("errors",[])]}),flush=True)
 except Exception:print("KV_RESULT",label,code,flush=True)
def main():
 code,b=req("GET","?per_page=100");status("list",code,b)
 if code!=200:return
 data=json.loads(b)
 if any(x.get("title")==TITLE for x in data.get("result",[])):print("KV_RESULT existing_namespace_no_change",flush=True);return
 if data.get("result_info",{}).get("total_pages",1)>1:print("KV_RESULT list_incomplete",flush=True);return
 code,b=req("POST","",json.dumps({"title":TITLE}).encode(),"application/json");status("create",code,b)
 if code not in (200,201):return
 ns=json.loads(b)["result"]["id"]
 # namespace identifier is not secret; report it as a stable resource reference in project.
 print("KV_RESULT namespace_id",ns,flush=True)
 path="/"+ns+"/values/probe-20261125";fixture=b'{"test":"synthetic","version":1}'
 code,b=req("PUT",path,fixture,"application/octet-stream");status("put",code,b)
 if code in (200,201):
  code,b=req("GET",path);print("KV_RESULT read",code,"sha256_match",hashlib.sha256(b).digest()==hashlib.sha256(fixture).digest(),flush=True)
  code,b=req("DELETE",path);status("delete_fixture",code,b)
if __name__=="__main__":main()
