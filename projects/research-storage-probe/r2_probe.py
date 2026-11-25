import os,json,hashlib,urllib.request,urllib.error
BASE="https://api.cloudflare.com/client/v4/accounts/"+os.environ["CLOUDFLARE_ACCOUNT_ID"]+"/r2/buckets"
TOKEN=os.environ["CLOUDFLARE_API_TOKEN"]
BUCKET="dns-research-corpus-20261125"
def request(method,path,data=None,content_type=None):
 h={"Authorization":"Bearer "+TOKEN}
 if content_type:h["Content-Type"]=content_type
 try:
  with urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=h,method=method),timeout=20) as r:return r.status,r.read(2000000)
 except urllib.error.HTTPError as e:return e.code,e.read(2000000)
def report(label,code,body):
 try:
  j=json.loads(body);print("R2_RESULT",label,code,json.dumps({"success":j.get("success"),"error_codes":[x.get("code") for x in j.get("errors",[])]}),flush=True)
 except Exception:print("R2_RESULT",label,code,flush=True)
def main():
 code,b=request("GET","");report("list_buckets",code,b)
 if code!=200:return
 # A new dedicated bucket only; do not alter any existing bucket.
 code,b=request("GET","/"+BUCKET)
 if code==404:
  code,b=request("POST","",json.dumps({"name":BUCKET,"storage_class":"Standard"}).encode(),"application/json");report("create_private_standard_bucket",code,b)
  if code not in (200,201):return
 elif code==200:report("bucket_already_exists",code,b);return
 else:report("bucket_lookup",code,b);return
 # Test only a synthetic object, then delete the test object.
 path="/"+BUCKET+"/objects/probe-20261125.json"
 fixture=b'{"test":"synthetic","version":1}'
 code,b=request("PUT",path,fixture,"application/octet-stream");report("put",code,b)
 if code in (200,201):
  code,b=request("GET",path);print("R2_RESULT read",code,"sha256_match",hashlib.sha256(b).digest()==hashlib.sha256(fixture).digest(),flush=True)
  code,b=request("DELETE",path);report("delete_fixture",code,b)
if __name__=="__main__":main()
