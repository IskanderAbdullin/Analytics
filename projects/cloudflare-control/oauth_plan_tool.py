"""Add owner-only read-only Serverspace power-plan MCP tool to EXISTING OAuth.

Dry-run by default. Does not execute power commands, does not expose
the provider API, and never changes broker/PC/VPS OAuth tool registrations.
All existing Cloudflare bindings inherited and verified on deploy.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from oauth_rollout import (ROOT,TARGET,REQUIRED,call,active,settings,unpack,
                          mime_body,syntax_check,Halt,emit)

REQUEST=Path(__file__).with_name("oauth_plan_request.json")
TOOL="serverspace_plan_power"
BINDING="SERVERSPACE_POWER_PLAN_SERVICE"
ENTRY="ServerspacePowerPlanEntrypoint"
SNIPPET=r'''
  // Owner-only read-only plan. NEVER submits an actual VPS power operation.
  // This tool has one fixed Cloudflare private named Service binding.
  if(env.SERVERSPACE_ENABLED==="true"){
    server.registerTool("serverspace_plan_power",{
      description:"Preview whether the sole Serverspace RU VPS could be powered on/off or rebooted. Read-only provider GET. Does not execute any command.",
      inputSchema:z.object({action:z.enum(["on","shutdown","reboot","off","reset"])})
    },async ({action})=>{
      try{
        requireUser();
        if(!env.SERVERSPACE_POWER_PLAN_SERVICE ||
           typeof env.SERVERSPACE_POWER_PLAN_SERVICE.fetch!=="function")
          throw new Error("SERVERSPACE_PLAN_NOT_CONFIGURED");
        const response=await env.SERVERSPACE_POWER_PLAN_SERVICE.fetch(
          "http://serverspace.internal/internal/serverspace/power-plan",
          {method:"POST",redirect:"manual",
           body:JSON.stringify({mode:"plan",target:"sole",action}),
           headers:{"Content-Type":"application/json"},
           signal:AbortSignal.timeout(12000)});
        if(!response.ok)
          throw new Error("SERVERSPACE_PLAN_HTTP_"+response.status);
        if(!response.headers.get("content-type")?.toLowerCase().includes("application/json"))
          throw new Error("SERVERSPACE_PLAN_SCHEMA");
        const raw=await response.text();
        if(raw.length>4000)throw new Error("SERVERSPACE_PLAN_SCHEMA");
        const data=JSON.parse(raw);
        if(!data||data.action!==action||data.execution_enabled!==false||
           !["ready","no_change"].includes(data.state))
          throw new Error("SERVERSPACE_PLAN_SCHEMA");
        const plan={action,state:data.state,execution_enabled:false,
          hard_power:data.hard_power===true,
          method_if_authorized:data.state==="ready"?"POST":null};
        return {content:[{type:"text",text:JSON.stringify(plan)}]};
      }catch(_){
        return {content:[{type:"text",text:"SERVERSPACE_PLAN_UNAVAILABLE"}],
                isError:true};
      }
    });
  }
'''
def request():
    c=json.loads(REQUEST.read_text("utf-8"))
    if(not isinstance(c,dict) or set(c)!={"schema_version","nonce","operation"}
       or c["schema_version"]!=1 or type(c["nonce"]) is not int
       or not 0<=c["nonce"]<=2147483647
       or c["operation"] not in ("dry_run","activate")):
       raise Halt("INVALID_REQUEST")
    from os import environ
    account=environ.get("CLOUDFLARE_ACCOUNT_ID","")
    token=environ.get("CLOUDFLARE_API_TOKEN","")
    if not re.fullmatch(r"[a-fA-F0-9]{32}",account) or len(token)<12:
        raise Halt("SECRETS_UNAVAILABLE")
    return c["operation"],ROOT+"/"+account,token

def patch(root,token):
    modules,source,_=unpack(root,token)
    present=TOOL in source
    if present:
        if "SERVERSPACE_POWER_PLAN_SERVICE" not in source:
            raise Halt("TOOL_PARTIAL_SOURCE")
        return modules,source,False
    if (len(re.findall(r"function createServer\(\)\s*\{",source))!=1 or
        len(re.findall(r"\breturn server;",source))!=1):
        raise Halt("CREATE_SERVER_LAYOUT_UNEXPECTED")
    for marker in ("serverspace_list_servers","server.registerTool(",
                   "requireUser()","SERVERSPACE_ENABLED","z.object("):
        if marker not in source:
            raise Halt("EXISTING_OAUTH_MARKER_MISSING")
    a=source.index("function createServer()")
    b=source.index("return server;",a)
    if b-a>120000:
        raise Halt("SERVER_FACTORY_LAYOUT_UNEXPECTED")
    changed=source[:b]+SNIPPET+"\n  "+source[b:]
    modules=[(name,ctype,changed.encode("utf-8") if name=="index.js" else data)
             for name,ctype,data in modules]
    return modules,changed,True

def service_ready(bindings):
    matches=[b for b in bindings if b.get("name")==BINDING]
    return (len(matches)==1 and matches[0].get("type")=="service"
      and matches[0].get("service")=="babit-vps-bridge"
      and matches[0].get("entrypoint")==ENTRY)

def main():
    op,root,token=request()
    baseline=active(root,token)
    _,bindings,names=settings(root,token)
    if BINDING in names and not service_ready(bindings):
        raise Halt("PLAN_BINDING_CONFLICT")
    if not REQUIRED.issubset(names) or "SERVERSPACE_SERVICE" not in names:
        raise Halt("PREVIOUS_BINDING_MISSING")
    originals={b.get("name"):(b.get("text") or b.get("value"))
               for b in bindings if b.get("name") in ("VPS_AGENT_ENABLED","PC_AGENT_ENABLED","SERVERSPACE_ENABLED")}
    if any(v!="true" for v in originals.values()):
        raise Halt("PREVIOUS_FLAGS_NOT_TRUE")
    modules,source,need_patch=patch(root,token)
    syntax_check(source)
    emit("preflight","passed",existing_bindings=len(names),
      code_patch_needed=need_patch,binding_needed=BINDING not in names,
      pc_vps_oauth_preserved=True,read_only=True)
    if op=="dry_run":
        return 0
    if not need_patch and service_ready(bindings):
        emit("activation","already_live")
        return 0
    if active(root,token)!=baseline:
        raise Halt("CONCURRENT_OAUTH_DEPLOYMENT")
    if need_patch:
        body,ctype=mime_body({"main_module":"index.js"},modules)
        call(root,token,"PUT",TARGET+"/content",body,ctype)
        emit("code_upload","accepted")
        _,code,patch_needed=patch(root,token)
        if patch_needed or TOOL not in code:
            raise Halt("CONTENT_NOT_LIVE")
    _,now_bindings,now_names=settings(root,token)
    if not names.issubset(now_names):
        raise Halt("OLD_BINDINGS_LOST")
    if not service_ready(now_bindings):
        inherited=[{"type":"inherit","name":n} for n in sorted(now_names) if n!=BINDING]
        inherited.append({"type":"service","name":BINDING,
          "service":"babit-vps-bridge","entrypoint":ENTRY})
        body,ctype=mime_body({"bindings":inherited},[])
        body=body.replace(b'name="metadata"',b'name="settings"',1)
        call(root,token,"PATCH",TARGET+"/settings",body,ctype)
        emit("binding_patch","accepted")
    _,final_bindings,after=settings(root,token)
    if not names.issubset(after) or not service_ready(final_bindings):
        raise Halt("BINDING_NOT_LIVE")
    for key,value in originals.items():
        item=next((b for b in final_bindings if b.get("name")==key),{})
        if (item.get("text") or item.get("value"))!=value:
            raise Halt("EXISTING_FLAG_CHANGED")
    _,final_code,need=patch(root,token)
    if need or TOOL not in final_code:
        raise Halt("TOOL_NOT_LIVE")
    emit("activation","verified_live",owner_only_tool=True,
         only_private_readonly_service=True,old_bindings_preserved=True,
         prior_pc_vps_broker_unmodified=True)
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except Halt as e:
        code=str(e)
        if not re.fullmatch(r"[A-Z0-9_]{3,80}",code):
            code="OAUTH_PLAN_BLOCKED"
        emit("halt","blocked",code=code)
        sys.exit(3)
    except Exception:
        emit("halt","blocked",code="UNEXPECTED_FAILURE")
        sys.exit(3)
