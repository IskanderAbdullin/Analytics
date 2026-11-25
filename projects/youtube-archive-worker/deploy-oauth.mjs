import fs from "node:fs/promises";
const NAME="youtube-archive-owner",TITLE="youtube-archive-owner-oauth",account=process.env.CLOUDFLARE_ACCOUNT_ID,token=process.env.CLOUDFLARE_API_TOKEN;
if(!account||!token)throw Error("Cloudflare credentials missing");
const root="https://api.cloudflare.com/client/v4/accounts/"+account;
async function cf(method,path,body){
 const headers={authorization:"Bearer "+token};
 if(body&&!(body instanceof FormData)){headers["content-type"]="application/json";body=JSON.stringify(body)}
 const res=await fetch(root+path,{method,headers,body,redirect:"error"});
 let data;try{data=await res.json()}catch{throw Error("Cloudflare response unreadable")}
 if(!res.ok||!data.success)throw Error("Cloudflare request failed: "+method+" "+res.status+" codes "+(data.errors??[]).map(e=>e.code).join(","));
 return data.result;
}
const scripts=await cf("GET","/workers/scripts");
if(!scripts.some(s=>s.id===NAME))throw Error("Dedicated Worker not found");
const sub=await cf("GET","/workers/subdomain");
if(sub.subdomain!=="videns42")throw Error("Unexpected Worker account subdomain");
const bindings=await cf("GET","/workers/scripts/"+NAME+"/settings");
const permitted=new Set(["OAUTH_KV","GOOGLE_CLIENT_ID","GOOGLE_CLIENT_SECRET","YOUTUBE_OWNER_CHANNEL_ID"]);
if((bindings.bindings??[]).some(b=>!permitted.has(b.name)))throw Error("Unexpected bindings; refusing update");
const existing=await cf("GET","/storage/kv/namespaces?per_page=100");
const matches=existing.filter(n=>n.title===TITLE);
if(matches.length>1)throw Error("Ambiguous namespace");
const ns=matches[0]??await cf("POST","/storage/kv/namespaces",{title:TITLE});
if(!ns?.id)throw Error("OAuth KV unavailable");
const code=await fs.readFile(process.argv[2]);
const metadata={main_module:"oauth.mjs",compatibility_date:"2026-11-25",compatibility_flags:["global_fetch_strictly_public"],observability:{enabled:false},keep_bindings:["secret_text","plain_text"],bindings:[{type:"kv_namespace",name:"OAUTH_KV",namespace_id:ns.id}]};
const form=new FormData();form.set("metadata",new Blob([JSON.stringify(metadata)],{type:"application/json"}));form.set("oauth.mjs",new Blob([code],{type:"application/javascript+module"}),"oauth.mjs");
await cf("PUT","/workers/scripts/"+NAME,form);
console.log("Dedicated OAuth Worker updated; KV bound; no Google credentials written.");
const base="https://"+NAME+"."+sub.subdomain+".workers.dev";
for(let i=0;i<12;i++){
 try{
  const res=await fetch(base+"/healthz",{redirect:"manual"});if(res.ok&&(await res.json()).version==="0.2.0")break;
 }catch{}
 if(i===11)throw Error("New Worker health did not become ready");
 await new Promise(resolve=>setTimeout(resolve,3000));
}
const h=await (await fetch(base+"/healthz")).json();
const protectedRes=await fetch(base+"/mcp",{method:"POST",headers:{"content-type":"application/json",accept:"application/json"},body:JSON.stringify({jsonrpc:"2.0",id:1,method:"tools/list"})});
if(protectedRes.status!==401)throw Error("Unauthenticated MCP unexpectedly accessible: "+protectedRes.status);
const challenge=protectedRes.headers.get("www-authenticate")??"";
const resourceUrl=challenge.match(/resource_metadata="([^"]+)"/)?.[1]??base+"/.well-known/oauth-protected-resource/mcp";
if(!resourceUrl.startsWith(base+"/"))throw Error("Unexpected resource metadata URL");
const resource=await fetch(resourceUrl);if(!resource.ok)throw Error("Protected resource metadata unavailable "+resource.status);
const meta=await resource.json();if(meta.resource!==base+"/mcp")throw Error("Wrong audience");
const issuer=await fetch(base+"/.well-known/oauth-authorization-server");if(!issuer.ok)throw Error("Authorization metadata unavailable "+issuer.status);
const auth=await issuer.json();if(auth.authorization_endpoint!==base+"/authorize"||!auth.code_challenge_methods_supported?.includes("S256"))throw Error("OAuth metadata mismatch");
if(!h.googleOAuthConfigured){const a=await fetch(base+"/authorize");if(a.status!==503)throw Error("Missing Google config should block login");}
console.log(JSON.stringify({health:200,version:h.version,googleOAuthConfigured:h.googleOAuthConfigured,unauthenticatedMcp:protectedRes.status,resourceMetadata:resource.status,issuerMetadata:issuer.status,pkce:true,cimd:auth.client_id_metadata_document_supported===true,callback:base+"/callback"}));
