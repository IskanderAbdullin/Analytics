"""Targeted Serverspace MCP extension of the existing production OAuth Worker.

Runs on public Analytics Actions, with production content in runner memory only.
Never prints source, account IDs, token values, server list or raw API JSON.
Dry run by default. Changes code only and bindings only via distinct Cloudflare APIs.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from email.parser import BytesParser
from email.policy import default as email_policy
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = "https://api.cloudflare.com/client/v4/accounts"
TARGET = "/workers/scripts/t-invest-mcp-proxy"
CHECK_PATH = Path(__file__).with_name("oauth_rollout_request.json")
ENTRY = "ServerspaceReadOnlyEntrypoint"
TOOL = "serverspace_list_servers"
BINDING = "SERVERSPACE_SERVICE"
FLAG = "SERVERSPACE_ENABLED"
REQUIRED = {"OAUTH_KV", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
            "COOKIE_ENCRYPTION_KEY", "ALLOWED_GOOGLE_EMAIL", "TINVEST_TOKEN",
            "PC_AGENT_RELAY", "VPS_AGENT_RELAY"}
MAX_SCRIPT = 160_000_000
SNIPPET = r'''
  // Owner-only Serverspace control-plane inventory, independent of VPS Agent/WSS.
  if (env.SERVERSPACE_ENABLED === "true") {
    server.registerTool("serverspace_list_servers", {
      description: "Read-only Serverspace RU VPS inventory through a private same-account binding. No power commands or shell."
    }, async () => {
      try {
        requireUser();
        if (!env.SERVERSPACE_SERVICE || typeof env.SERVERSPACE_SERVICE.fetch !== "function")
          throw new Error("SERVERSPACE_NOT_CONFIGURED");
        const response = await env.SERVERSPACE_SERVICE.fetch(
          "http://serverspace.internal/internal/serverspace/list-servers",
          {method:"POST",redirect:"manual",signal:AbortSignal.timeout(12000)}
        );
        if (!response.ok) throw new Error("SERVERSPACE_BRIDGE_HTTP_" + response.status);
        if (!response.headers.get("content-type")?.toLowerCase().includes("application/json"))
          throw new Error("SERVERSPACE_BAD_CONTENT_TYPE");
        const raw = await response.text();
        if (raw.length > 128000) throw new Error("SERVERSPACE_RESPONSE_TOO_LARGE");
        const payload = JSON.parse(raw);
        if (!payload || !Array.isArray(payload.servers) || payload.servers.length > 250)
          throw new Error("SERVERSPACE_INVALID_SCHEMA");
        const field = (v, max) => {
          if (typeof v === "string" && v.length <= max) return v;
          if (typeof v === "number" && Number.isSafeInteger(v)) return String(v);
          return null;
        };
        const servers = payload.servers.map(item => {
          if (!item || typeof item !== "object") throw new Error("SERVERSPACE_INVALID_SCHEMA");
          const id = field(item.id, 80);
          if (!id) throw new Error("SERVERSPACE_INVALID_SCHEMA");
          return {
            id, name:field(item.name,150), state:field(item.state,64),
            location_id:field(item.location_id,64),
            is_power_on:typeof item.is_power_on === "boolean" ? item.is_power_on : null
          };
        });
        return {content:[{type:"text",text:JSON.stringify({servers,count:servers.length})}]};
      } catch (e) {
        const msg = e instanceof Error ? e.message : "";
        return {content:[{type:"text",text:/^SERVERSPACE_[A-Z0-9_]+$/.test(msg)
          ? msg : "SERVERSPACE_BRIDGE_UNAVAILABLE"}],isError:true};
      }
    });
  }
'''
class Halt(Exception):
    pass

def emit(phase, outcome, **kw):
    print(json.dumps({"stage":"oauth_serverspace_rollout","phase":phase,"outcome":outcome,**kw},
                     sort_keys=True),flush=True)

def conf():
    obj=json.loads(CHECK_PATH.read_text(encoding="utf-8"))
    if (not isinstance(obj,dict) or set(obj)!={"schema_version","nonce","operation"}
        or obj["schema_version"]!=1 or type(obj["nonce"]) is not int
        or not 0<=obj["nonce"]<=2147483647
        or obj["operation"] not in ("dry_run","activate")):
        raise Halt("INVALID_REQUEST")
    account=os.environ.get("CLOUDFLARE_ACCOUNT_ID","")
    token=os.environ.get("CLOUDFLARE_API_TOKEN","")
    if not re.fullmatch(r"[0-9a-fA-F]{32}",account) or len(token)<12:
        raise Halt("SECRETS_UNAVAILABLE")
    return obj["operation"],ROOT+"/"+account,token

def call(root,token,method,path,data=None,ctype=None,raw=False):
    if not path.startswith("/") or ".." in path or "//" in path:
        raise Halt("INVALID_ENDPOINT")
    headers={"Authorization":"Bearer "+token,"Accept":"application/json"}
    if ctype: headers["Content-Type"]=ctype
    try:
        with urlopen(Request(root+path,data=data,method=method,headers=headers),timeout=35) as res:
            chunk=res.read(MAX_SCRIPT+1 if raw else 2_000_001)
            if len(chunk)>(MAX_SCRIPT if raw else 2_000_000):raise Halt("API_BODY_TOO_LARGE")
            if raw:return chunk,res.headers.get("Content-Type",""),res.headers.get("CF-Worker-Main-Module-Part","")
            payload=json.loads(chunk)
            if not isinstance(payload,dict) or payload.get("success") is not True:
                raise Halt("CLOUDFLARE_REJECTED")
            return payload.get("result")
    except HTTPError as exc:
        raise Halt("HTTP_"+str(exc.code)) from None
    except (URLError,TimeoutError,OSError):
        raise Halt("NETWORK_UNAVAILABLE") from None
    except (ValueError,UnicodeError):
        raise Halt("INVALID_API_JSON") from None

def active(root,token):
    obj=call(root,token,"GET",TARGET+"/deployments")
    deployments=obj.get("deployments") if isinstance(obj,dict) else obj
    if not isinstance(deployments,list) or not deployments:raise Halt("NO_DEPLOYMENT")
    versions=deployments[0].get("versions") or []
    found=[v.get("version_id") for v in versions if v.get("percentage")==100]
    if len(found)!=1 or not isinstance(found[0],str):raise Halt("ACTIVE_VERSION_UNKNOWN")
    return found[0]

def settings(root,token):
    obj=call(root,token,"GET",TARGET+"/settings")
    bindings=obj.get("bindings") if isinstance(obj,dict) else None
    if not isinstance(bindings,list) or not bindings:raise Halt("BINDINGS_MISSING")
    names={x.get("name") for x in bindings if isinstance(x,dict)}
    if None in names or len(names)!=len(bindings) or not REQUIRED.issubset(names):
        raise Halt("BINDINGS_UNEXPECTED")
    return obj,bindings,names

def unpack(root,token):
    raw,mime,main_head=call(root,token,"GET",TARGET+"/content/v2",raw=True)
    if not mime.lower().startswith("multipart/"):raise Halt("MULTIPART_EXPECTED")
    message=BytesParser(policy=email_policy).parsebytes(
        b"MIME-Version: 1.0\r\nContent-Type: "+mime.encode("ascii")+b"\r\n\r\n"+raw
    )
    modules=[]
    for part in message.iter_parts():
        name=part.get_param("name",header="content-disposition")
        if not isinstance(name,str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}",name):
            raise Halt("MODULE_NAME_UNEXPECTED")
        modules.append((name,part.get_content_type(),part.get_payload(decode=True) or b""))
    names=sorted(name for name,_,_ in modules)
    if names not in (["index.js"],["index.js","index.js.map"]):
        raise Halt("MODULE_LAYOUT_UNEXPECTED")
    js=next(payload for name,_,payload in modules if name=="index.js")
    source=js.decode("utf-8")
    if "SERVERSPACE_SERVICE" in source or TOOL in source:
        if TOOL not in source or BINDING not in source:raise Halt("PARTIAL_SOURCE_UNEXPECTED")
        return modules,source,False
    if len(re.findall(r"function createServer\(\)\s*\{",source))!=1:
        raise Halt("CREATE_SERVER_ANCHOR_MISSING")
    if len(re.findall(r"\breturn server;",source))!=1:
        raise Halt("RETURN_SERVER_ANCHOR_AMBIGUOUS")
    if not all(x in source for x in ('requireUser()', 'server.registerTool(', 'list_allowed_market_tools','vps_status')):
        raise Halt("INCOMPATIBLE_PRODUCTION_BUNDLE")
    a=source.index("function createServer()")
    b=source.index("return server;",a)
    if b-a>100_000:raise Halt("CREATE_SERVER_LAYOUT_UNEXPECTED")
    updated=source[:b]+SNIPPET+"\n  "+source[b:]
    patched=[(name,ctype,updated.encode("utf-8") if name=="index.js" else payload)
             for name,ctype,payload in modules]
    return patched,updated,True

def mime_body(metadata,files):
    boundary="----OauthServerspace"+uuid.uuid4().hex
    chunks=[]
    def part(name,content,ctype,filename=None):
        chunks.extend([("--"+boundary+"\r\n").encode(),
            ('Content-Disposition: form-data; name="'+name+'"'+
             ('; filename="'+filename+'"' if filename else '')+"\r\n").encode(),
            ("Content-Type: "+ctype+"\r\n\r\n").encode(),content,b"\r\n"])
    part("metadata",json.dumps(metadata,separators=(",",":")).encode(),"application/json")
    for name,ctype,payload in files:
        part(name,payload,ctype,name)
    chunks.append(("--"+boundary+"--\r\n").encode())
    return b"".join(chunks),"multipart/form-data; boundary="+boundary

def syntax_check(source):
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/"index.mjs"
        path.write_text(source,encoding="utf-8")
        p=subprocess.run(["node","--check",str(path)],stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,timeout=40,check=False)
        if p.returncode:raise Halt("SYNTAX_CHECK_FAILED")

def flag_status(bindings):
    match=[x for x in bindings if x.get("name")==FLAG]
    return (match[0].get("text") or match[0].get("value")) if len(match)==1 else None

def ready_binding(bindings):
    matches=[x for x in bindings if x.get("name")==BINDING]
    if not matches:return False
    return (len(matches)==1 and matches[0].get("type")=="service" and
            matches[0].get("service")=="babit-vps-bridge" and
            matches[0].get("entrypoint")==ENTRY)

def main():
    operation,root,token=conf()
    baseline=active(root,token)
    _,oldbindings,names=settings(root,token)
    if BINDING in names and not ready_binding(oldbindings):
        raise Halt("SERVICE_BINDING_CONFLICT")
    if FLAG in names and flag_status(oldbindings) not in ("true","false"):
        raise Halt("FLAG_UNEXPECTED")
    mods,new_source,needs_code=unpack(root,token)
    syntax_check(new_source)
    emit("preflight","passed",module_count=len(mods),
         code_patch_needed=needs_code,binding_needed=BINDING not in names,
         existing_bindings=len(oldbindings),existing_pc_vps_flags_preserved=True)
    if operation=="dry_run":return
    if not needs_code and ready_binding(oldbindings) and flag_status(oldbindings)=="true":
        emit("activation","already_live");return
    if active(root,token)!=baseline:raise Halt("CONCURRENT_DEPLOYMENT")
    if needs_code:
        # Official content endpoint leaves all current configuration untouched.
        upload,ctype=mime_body({"main_module":"index.js"},mods)
        call(root,token,"PUT",TARGET+"/content",upload,ctype)
        emit("content","accepted")
        check_modules,check_source,still_needs_code=unpack(root,token)
        if still_needs_code or TOOL not in check_source:raise Halt("CONTENT_NOT_CONFIRMED")
    newer,bindings,names2=settings(root,token)
    if not names.issubset(names2):raise Halt("EXISTING_BINDINGS_LOST")
    if not (ready_binding(bindings) and flag_status(bindings)=="true"):
        inherited=[{"type":"inherit","name":n} for n in sorted(names2) if n not in (BINDING,FLAG)]
        inherited.append({"type":"service","name":BINDING,
              "service":"babit-vps-bridge","entrypoint":ENTRY})
        inherited.append({"type":"plain_text","name":FLAG,"text":"true"})
        # Only bindings changed; API retains current script code and DO classes.
        body,ctype=mime_body({"bindings":inherited},[])
        # Patch /settings expects 'settings' part, not 'metadata'.
        body=body.replace(b'name="metadata"',b'name="settings"',1)
        call(root,token,"PATCH",TARGET+"/settings",body,ctype)
        emit("binding_patch","accepted")
    _,final_bindings,after=settings(root,token)
    if not names.issubset(after) or not ready_binding(final_bindings) or flag_status(final_bindings)!="true":
        raise Halt("BINDING_VERIFY_FAILED")
    if not REQUIRED.issubset(after):raise Halt("REQUIRED_BINDING_LOST")
    _,after_source,_=unpack(root,token)
    if TOOL not in after_source:raise Halt("TOOL_VERIFY_FAILED")
    emit("activation","settings_and_code_live",
         existing_binding_names_preserved=True,
         owner_only_tool_present=True,
         service_binding_present=True,
         pc_vps_flags_preserved=True)

if __name__=="__main__":
    try:
        main()
    except Halt as exc:
        code=str(exc)
        if not re.fullmatch(r"[A-Z0-9_]{3,72}",code):code="ROLLOUT_FAILED"
        emit("halt","blocked",code=code)
        sys.exit(3)
    except Exception:
        emit("halt","blocked",code="UNEXPECTED_FAILURE")
        sys.exit(3)
