const id="aLM-8X7VRyo";
export default {async fetch(request){
 if (new URL(request.url).pathname!=="/probe" || request.method!=="GET") return new Response("Not found",{status:404});
 const result={};
 for(const [name,url] of [["oembed","https://www.youtube.com/oembed?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D"+id+"&format=json"],["watch","https://www.youtube.com/watch?v="+id]]){
  try { const r=await fetch(url,{redirect:"follow"}); const body=await r.text(); result[name]={status:r.status,body_length:body.length,caption_tracks:name==="watch"&&body.includes('"captionTracks"'),bot_message:/confirm you.re not a bot|unusual traffic/i.test(body)}; }
  catch(e){ result[name]={error:"fetch_failed"}; }
 }
 return Response.json(result,{headers:{"Cache-Control":"no-store"}});
}};