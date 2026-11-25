const base="https://youtube-archive-owner.videns42.workers.dev";
async function req(path,body){
 const res=await fetch(base+path,{redirect:"manual",headers:{"cache-control":"no-cache",accept:"application/json","content-type":"application/json"},...(body?{method:"POST",body:JSON.stringify(body)}:{})});
 let value={};try{value=await res.json()}catch{}
 return {res,value};
}
const h=await req("/healthz");
console.log("health",h.res.status,"version",h.value.version??"legacy","googleConfigured",h.value.googleOAuthConfigured??false);
const d=await req("/mcp",{jsonrpc:"2.0",id:1,method:"tools/list"});
console.log("tools/list",d.res.status,"count",d.value.result?.tools?.length??0,"rpcError",!!d.value.error,"challenge",!!d.res.headers.get("www-authenticate"));
for(const name of ["youtube_owner_channels","youtube_owner_caption_download"]){
 const c=await req("/mcp",{jsonrpc:"2.0",id:2,method:"tools/call",params:{name,arguments:{}}});
 const granted=!!c.value.result&&!c.value.result.isError;
 console.log("tools/call",name,"status",c.res.status,"granted",granted,"challenge",!!c.res.headers.get("www-authenticate"));
 if(granted)throw Error("Unauthenticated data call returned a result");
}
for(const path of ["/.well-known/oauth-protected-resource/mcp","/.well-known/oauth-protected-resource","/.well-known/oauth-authorization-server","/authorize"]){
 const x=await req(path);
 console.log(path,"status",x.res.status,"resourceMatch",x.value.resource===base+"/mcp","issuerMatch",x.value.issuer===base,"pkce",x.value.code_challenge_methods_supported?.includes("S256")??false,"cimd",x.value.client_id_metadata_document_supported??false);
}
