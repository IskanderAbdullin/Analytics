import {test} from "node:test";
import assert from "node:assert/strict";
import {VpsAgentRelay,VpsSocketHealthEntrypoint} from "./vps-socket-wrapper-fixture.mjs";

const url="http://private.internal/internal/vps/socket-health";
const sockets=[
 {readyState:1,token:"SECRET"},{readyState:1,url:"wss://SENSITIVE"},
 {readyState:2},{readyState:3},{readyState:0}
];
let closeCalls=0;
for(const ws of sockets)ws.close=()=>{closeCalls++;throw Error("no close allowed");};
const state={getWebSockets(tag){assert.equal(tag,"device");return sockets;}};
const relay=new VpsAgentRelay(state);
const binding={idFromName(x){assert.equal(x,"dummy-fixed-id");return "internal";},
               get(id){assert.equal(id,"internal");return {
                 fetch(request){return relay.fetch(request);}
               }}};
const env={VPS_AGENT_ENABLED:"true",VPS_AGENT_DEVICE_ID:"dummy-fixed-id",
           VPS_AGENT_RELAY:binding};

test("original Device WSS request path continues to old fetch method",async()=>{
  const r=await relay.fetch(new Request("http://internal/vps-agent/device"));
  assert.equal(r.status,200);
  assert.equal(await r.text(),"original");
  assert.equal(relay.original_calls,1);
  assert.equal(closeCalls,0);
});
test("private socket GET returns strictly numeric counts, nothing identifying",async()=>{
  const admin=new VpsSocketHealthEntrypoint(env);
  const r=await admin.fetch(new Request(url,{method:"GET"}));
  assert.equal(r.status,200);
  assert.equal(r.headers.get("cache-control"),"no-store");
  const raw=await r.text();
  assert.deepEqual(JSON.parse(raw),{open:2,closing:1,closed:1,other:1,total:5});
  for(const x of ["SECRET","SENSITIVE","dummy-fixed-id","wss://"])
    assert.ok(!raw.includes(x));
  assert.equal(closeCalls,0);
});
test("public and mutation attempts cannot access socket counts",async()=>{
  const admin=new VpsSocketHealthEntrypoint(env);
  assert.equal((await admin.fetch(new Request("http://private.internal/vps-agent/device"))).status,404);
  assert.equal((await admin.fetch(new Request(url,{method:"POST"}))).status,405);
  assert.equal((await admin.fetch(new Request(url+"?device=123"))).status,404);
  assert.equal(relay.original_calls,1);
});
test("private entrypoint fails closed when existing device config is absent",async()=>{
  const admin=new VpsSocketHealthEntrypoint({...env,VPS_AGENT_ENABLED:"false"});
  assert.equal((await admin.fetch(new Request(url))).status,503);
  assert.equal(closeCalls,0);
});
