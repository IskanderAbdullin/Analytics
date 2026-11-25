// Fixed-batch collector; only documented FreeTranscriptAPI endpoint; no proxy.
const CASES = [{"id":"GIrQV9wMNbg","duration":10774},{"id":"EHQ-x9o_du0","duration":11431},{"id":"eR50OM6pJ0w","duration":7972},{"id":"mxjn-YS4Xmk","duration":8325},{"id":"bzYnZmxx7DU","duration":7590},{"id":"Uk8NcpRDJQo","duration":8058},{"id":"op9ecP91oRM","duration":9993},{"id":"s2fkkIUbZ1U","duration":13686},{"id":"-0UN91Y3gDw","duration":7076},{"id":"tdxriMnhuzQ","duration":10641},{"id":"tdE-yYnduTg","duration":12765},{"id":"O2lfVD8TYjs","duration":8353}];
const API = "https://api.freetranscriptapi.com/v1/transcript";
const encoder = new TextEncoder();
const reply = (body,status=200) => Response.json(body,{status,headers:{"Cache-Control":"no-store"}});
const digest = async body => [...new Uint8Array(await crypto.subtle.digest("SHA-256",encoder.encode(body)))].map(x=>x.toString(16).padStart(2,"0")).join("");
async function collect(id0,env){
  const item=CASES.find(x=>x.id===id0);
  if(!item)return reply({status:"invalid_id"},400);
  const id=item.id, key="native/youtube/"+id+"/fta-v1.json";
  const old=await env.CORPUS.get(key);
  if(old!==null) return reply({video_id:id,status:"already_exists",key,sha256:await digest(old),bytes:encoder.encode(old).length});
  const url=new URL(API);url.searchParams.set("video_url",id);url.searchParams.set("lang","ru");url.searchParams.set("format","json");
  const res=await fetch(url,{headers:{"Accept":"application/json"},redirect:"error"});
  const remaining=res.headers.get("X-RateLimit-Remaining");
  if(!res.ok) { let err="unknown";try{err=(await res.json()).error?.code??"unknown"}catch{};return reply({video_id:id,status:"provider_error",http:res.status,error_code:err,remaining}); }
  const raw=await res.text();if(raw.length>4000000)return reply({video_id:id,status:"size_limit"});
  let obj;try{obj=JSON.parse(raw)}catch{return reply({video_id:id,status:"invalid_json"})}
  const lines=obj.transcript;
  if(!["ru","ru-RU"].includes(obj.language)||!Array.isArray(lines)||!lines.length)return reply({video_id:id,status:"wrong_language_or_empty",language:obj.language,remaining});
  let chars=0,last=0,prev=-1;for(const x of lines){const start=x.start,end=start+x.duration;if(typeof x.text!=="string"||!Number.isFinite(start)||!Number.isFinite(end)||start<0||start<prev||end<start)return reply({video_id:id,status:"invalid_timing"});prev=start;last=Math.max(last,end);chars+=x.text.length;}
  if(!chars)return reply({video_id:id,status:"empty_text"});
  const first=lines[0].start,ratio=last/item.duration;
  const coverage=(ratio>=0.95&&ratio<=1.05&&first<60)?"coverage_ok_unreviewed":"coverage_review";
  const record={schema_version:1,source:"FreeTranscriptAPI public native captions",video_id:id,expected_duration_s:item.duration,retrieved_utc:new Date().toISOString(),language:obj.language,first_s:first,last_s:last,review_status:coverage,response:obj};
  const payload=JSON.stringify(record),bytes=encoder.encode(payload).length,sha256=await digest(payload);
  await env.CORPUS.put(key,payload);
  return reply({video_id:id,status:"stored_pending_readback",key,sha256,bytes,segments:lines.length,chars,first,last,expected_duration_s:item.duration,coverage,coverage_fraction:ratio,language:obj.language,remaining});
}
export default {async queue(batch,env){for(const message of batch.messages){const d=message.body;if(!d||typeof d.run_id!=="string"||!/^\d+$/.test(d.run_id)||!CASES.some(x=>x.id===d.video_id)){message.ack();continue;}const receipt="receipt/queue/"+d.run_id+"/"+d.video_id;try{const result=await collect(d.video_id,env);await env.CORPUS.put(receipt,await result.text());}catch(e){await env.CORPUS.put(receipt,JSON.stringify({video_id:d.video_id,status:"worker_error",error:e.name}));}message.ack();}}};