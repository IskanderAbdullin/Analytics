const id="aLM-8X7VRyo";
function extractArray(s,key){let i=s.indexOf('"'+key+'"');if(i<0)return null;i=s.indexOf('[',i);if(i<0)return null;let depth=0,q=false,esc=false;for(let j=i;j<s.length;j++){let c=s[j];if(q){if(esc)esc=false;else if(c==='\\')esc=true;else if(c==='"')q=false;continue}if(c==='"'){q=true;continue}if(c==='[')depth++;if(c===']'&&!--depth){try{return JSON.parse(s.slice(i,j+1))}catch{return null}}}return null}
export default {async fetch(req){
 if(new URL(req.url).pathname!=="/probe"||req.method!=="GET")return new Response("Not found",{status:404});
 let out={};
 try{
 const r=await fetch("https://www.youtube.com/watch?v="+id);const html=await r.text();out.watch={status:r.status,length:html.length,caption_tracks:html.includes('"captionTracks"')};
 if(!r.ok||/confirm you.re not a bot|unusual traffic/i.test(html))return Response.json({...out,stop:"watch_blocked"});
 const tracks=extractArray(html,"captionTracks");out.tracks=Array.isArray(tracks)?tracks.map(x=>({language:x.languageCode,kind:x.kind||"manual"})):null;
 const track=tracks?.find(x=>x.languageCode==="ru"||x.languageCode==="ru-orig");if(!track?.baseUrl)return Response.json({...out,stop:"no_russian_public_track"});
 const u=new URL(track.baseUrl);if(!["youtube.com","www.youtube.com"].includes(u.hostname)||u.protocol!=="https:"||u.pathname!=="/api/timedtext")return Response.json({...out,stop:"unexpected_track_url"});
 const cap=await fetch(u,{redirect:"error"});const text=await cap.text();out.captions={status:cap.status,chars:text.length,content_type:cap.headers.get("content-type")};
 if(cap.ok&&text.length){try{const j=JSON.parse(text);out.captions.events=j.events?.length??null;out.captions.last_end_ms=Math.max(0,...(j.events||[]).map(e=>(e.tStartMs||0)+(e.dDurationMs||0)))}catch{const all=[...text.matchAll(/<text\b[^>]*\bstart="([\d.]+)"[^>]*\bdur="([\d.]+)"/g)];out.captions.xml_segments=all.length;out.captions.last_end_seconds=Math.max(0,...all.map(m=>Number(m[1])+Number(m[2])));out.captions.xml_root=/<transcript\b/.test(text);out.captions.srv3_root=/<timedtext\b/.test(text)}}
 }catch(e){out.error="fetch_or_parse_failed"}
 return Response.json(out,{headers:{"Cache-Control":"no-store"}});
}};