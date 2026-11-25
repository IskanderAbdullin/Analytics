const ROOT = "https://www.googleapis.com/youtube/v3/";
const tools = [
 {name:"youtube_owner_channels",description:"List YouTube channels belonging to the authenticated Google user, including uploads playlist IDs.",inputSchema:{type:"object",properties:{pageToken:{type:"string"}},additionalProperties:false}},
 {name:"youtube_owner_uploads",description:"List one page of uploads for an owned channel; includes private uploads when authorized.",inputSchema:{type:"object",properties:{channelId:{type:"string"},pageToken:{type:"string"}},required:["channelId"],additionalProperties:false}},
 {name:"youtube_owner_captions",description:"List caption tracks of one video owned by the authenticated channel. Does not modify the video.",inputSchema:{type:"object",properties:{videoId:{type:"string"}},required:["videoId"],additionalProperties:false}},
 {name:"youtube_owner_caption_download",description:"Download a single existing owned caption track in SRT format. No audio transcription is performed.",inputSchema:{type:"object",properties:{videoId:{type:"string"},captionId:{type:"string"}},required:["videoId","captionId"],additionalProperties:false}}
].map(t=>({...t,annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:true}}));
const headers = {"cache-control":"no-store","content-type":"application/json; charset=utf-8","x-content-type-options":"nosniff"};
const json=(v,status=200)=>new Response(JSON.stringify(v),{status,headers});
const id=(v,kind)=>{if(typeof v!=="string"||!((kind==="video"?/^[A-Za-z0-9_-]{11}$/:kind==="channel"?/^UC[A-Za-z0-9_-]{22}$/:/^[A-Za-z0-9_-]{1,200}$/).test(v)))throw new Error("Invalid "+kind+" ID");return v};
const page=v=>{if(v===undefined)return undefined;if(typeof v!=="string"||v.length>2048)throw new Error("Invalid page token");return v};
async function api(token,path,params,text=false){
 const u=new URL(path,ROOT);for(const [k,v] of Object.entries(params))if(v!==undefined)u.searchParams.set(k,String(v));
 const res=await fetch(u,{method:"GET",headers:{authorization:token,accept:text?"*/*":"application/json"},redirect:"error"});
 if(!res.ok){let reason="";try{const e=await res.json();reason=e?.error?.errors?.[0]?.reason??""}catch{};throw new Error("YouTube HTTP "+res.status+(reason?" ("+String(reason).replace(/[^a-zA-Z0-9_-]/g,"").slice(0,80)+")":""))}
 if(text){const n=Number(res.headers.get("content-length"));if(n>4000000)throw new Error("Caption exceeds 4 MB output limit");const reader=res.body.getReader();let len=0,parts=[];for(;;){const {done,value}=await reader.read();if(done)break;len+=value.length;if(len>4000000){await reader.cancel();throw new Error("Caption exceeds 4 MB output limit")}parts.push(value)}const all=new Uint8Array(len);let offset=0;for(const v of parts){all.set(v,offset);offset+=v.length}return new TextDecoder().decode(all)}
 return res.json();
}
const mine=(token,pt)=>api(token,"channels",{part:"id,contentDetails",mine:"true",maxResults:50,pageToken:pt});
async function ownedChannel(token,channel){
 let pt;for(let i=0;i<20;i++){const a=await mine(token,pt);const match=a.items?.find(v=>v.id===channel);if(match)return match;pt=a.nextPageToken;if(!pt)break}throw new Error("Channel not owned by this authorization");
}
async function ownedVideo(token,video){const a=await api(token,"videos",{part:"snippet,status",id:video});const v=a.items?.find(v=>v.id===video);if(!v)throw new Error("Video unavailable to this authorization");await ownedChannel(token,v.snippet.channelId);return v}
const tracks=(token,video)=>api(token,"captions",{part:"snippet",videoId:video});
async function call(name,args,token){
 if(name==="youtube_owner_channels")return mine(token,page(args.pageToken));
 if(name==="youtube_owner_uploads"){const ch=await ownedChannel(token,id(args.channelId,"channel"));const playlist=ch.contentDetails?.relatedPlaylists?.uploads;if(!playlist)throw new Error("Uploads playlist unavailable");return api(token,"playlistItems",{part:"snippet,contentDetails,status",playlistId:playlist,maxResults:50,pageToken:page(args.pageToken)})}
 if(name==="youtube_owner_captions"){const v=id(args.videoId,"video");await ownedVideo(token,v);return tracks(token,v)}
 if(name==="youtube_owner_caption_download"){const v=id(args.videoId,"video"),c=id(args.captionId,"caption");await ownedVideo(token,v);const a=await tracks(token,v);if(!a.items?.some(x=>x.id===c&&x.snippet?.videoId===v))throw new Error("Caption does not belong to the requested video");const s=await api(token,"captions/"+encodeURIComponent(c),{tfmt:"srt"},true);return {videoId:v,captionId:c,format:"srt",text:s}}
 throw new Error("Unknown tool");
}
const rpc=(id,result)=>json({jsonrpc:"2.0",id,result});
const error=(id,code,message)=>json({jsonrpc:"2.0",id,error:{code,message}});
export default {async fetch(req){
 const url=new URL(req.url);
 if(url.pathname==="/healthz"&&req.method==="GET")return json({ok:true,service:"youtube-archive",mode:"owner-token-read-only",googleOAuth:"caller-provided; not yet provisioned"});
 if(url.pathname!=="/mcp")return json({error:"not_found"},404);
 if(req.method!=="POST")return json({error:"method_not_allowed"},405);
 let msg;try{const body=await req.text();if(body.length>16384)return json({error:"body_too_large"},413);msg=JSON.parse(body)}catch{return error(null,-32700,"Parse error")}
 if(!msg||Array.isArray(msg)||msg.jsonrpc!=="2.0")return error(null,-32600,"Invalid request");
 if(msg.method==="initialize")return rpc(msg.id,{protocolVersion:["2024-11-05","2025-03-26","2025-06-18","2025-11-25"].includes(msg.params?.protocolVersion)?msg.params.protocolVersion:"2025-06-18",capabilities:{tools:{}},serverInfo:{name:"youtube-archive",version:"0.1.0"}});
 if(msg.method==="notifications/initialized")return new Response(null,{status:202,headers:{"cache-control":"no-store"}});
 if(msg.method==="ping")return rpc(msg.id,{});
 if(msg.method==="tools/list")return rpc(msg.id,{tools});
 if(msg.method!=="tools/call")return error(msg.id,-32601,"Method not found");
 const token=req.headers.get("authorization")??"";
 if(!/^Bearer [A-Za-z0-9._~+\/=-]{10,4096}$/i.test(token))return json({error:"Google OAuth bearer token required"},401);
 try{const name=msg.params?.name,args=msg.params?.arguments??{};if(!args||typeof args!=="object"||Array.isArray(args))throw new Error("Invalid arguments");const result=await call(name,args,token);return rpc(msg.id,{content:[{type:"text",text:JSON.stringify(result)}]})}
 catch(e){return rpc(msg.id,{isError:true,content:[{type:"text",text:e instanceof Error?e.message:"YouTube request failed"}]})}
}};
