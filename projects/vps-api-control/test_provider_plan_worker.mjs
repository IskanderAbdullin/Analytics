import {test} from "node:test";
import assert from "node:assert/strict";
import {ServerspacePowerPlanEntrypoint} from "./provider-plan-worker-fixture.mjs";

const endpoint="http://private/internal/serverspace/power-plan";
const env={SERVERSPACE_API_ENABLED:"true",SERVERSPACE_API_KEY:"dummy-rehearsal-key-1234567"};
const server={id:"l1s234",is_power_on:true,name:"HOST_SECRET",login:"root",
  password:"PASSWORD_SECRET",nics:[{ip_address:"192.0.2.1"}]};
const response=(body,status=200)=>new Response(JSON.stringify(body),{
  status,headers:{"Content-Type":"application/json"}});
const request=(action="reboot",mode="plan")=>new Request(endpoint,{
  method:"POST",headers:{"Content-Type":"application/json"},
  body:JSON.stringify({mode,target:"sole",action})});

test("real service candidate requests only provider GET for a ready reboot plan",async()=>{
  let n=0;
  const original=globalThis.fetch;
  globalThis.fetch=async (url,opt)=>{
    n++;assert.equal(String(url),"https://api.serverspace.ru/api/v1/servers");
    assert.equal(opt.method,"GET");
    assert.equal(opt.redirect,"manual");
    assert.ok(!("body" in opt));
    return response({servers:[server]});
  };
  try{
    const r=await new ServerspacePowerPlanEntrypoint(env).fetch(request());
    assert.equal(r.status,200);
    const raw=await r.text();
    assert.deepEqual(JSON.parse(raw),{state:"ready",action:"reboot",
      method_if_authorized:"POST",hard_power:false,execution_enabled:false});
    for(const sensitive of ["HOST_SECRET","PASSWORD_SECRET","192.0.2.1","l1s234"])
      assert.ok(!raw.includes(sensitive));
    assert.equal(n,1);
  } finally {globalThis.fetch=original;}
});
test("already-on is a no-change plan",async()=>{
  const original=globalThis.fetch;let n=0;
  globalThis.fetch=async()=>{n++;return response({servers:[server]});};
  try{
    const r=await new ServerspacePowerPlanEntrypoint(env).fetch(request("on"));
    assert.deepEqual(await r.json(),{state:"no_change",action:"on",execution_enabled:false});
    assert.equal(n,1);
  }finally{globalThis.fetch=original;}
});
test("hard-power reset is only a plan, no operation",async()=>{
  const original=globalThis.fetch;let n=0;
  globalThis.fetch=async(_,opt)=>{n++;assert.equal(opt.method,"GET");return response({servers:[server]});};
  try{
    const r=await new ServerspacePowerPlanEntrypoint(env).fetch(request("reset"));
    const p=await r.json();
    assert.equal(p.hard_power,true);assert.equal(p.execution_enabled,false);
    assert.equal(n,1);
  }finally{globalThis.fetch=original;}
});
test("execute mode, invalid actions and extra fields are refused before network",async()=>{
  const original=globalThis.fetch;let n=0;
  globalThis.fetch=async()=>{n++;throw Error("MUST_NOT_FETCH");};
  try{
    const inst=new ServerspacePowerPlanEntrypoint(env);
    for(const req of [
      request("reboot","execute"),request("delete"),request("../reset"),
      new Request(endpoint,{method:"POST",body:JSON.stringify({
        mode:"plan",target:"sole",action:"reboot",url:"https://evil.invalid"})})
    ]) assert.equal((await inst.fetch(req)).status,400);
    assert.equal(n,0);
  } finally {globalThis.fetch=original;}
});
test("missing enablement refuses even provider GET",async()=>{
  const original=globalThis.fetch;let n=0;
  globalThis.fetch=async()=>{n++;throw Error("MUST_NOT_FETCH");};
  try{
    const r=await new ServerspacePowerPlanEntrypoint({
      ...env,SERVERSPACE_API_ENABLED:"false"}).fetch(request());
    assert.equal(r.status,503);assert.equal(n,0);
  }finally{globalThis.fetch=original;}
});
test("multiple target servers fail closed and disclose no identifiers",async()=>{
  const original=globalThis.fetch;let n=0;
  globalThis.fetch=async()=>{n++;return response({servers:[server,{...server,id:"l1s235"}]});};
  try{
    const r=await new ServerspacePowerPlanEntrypoint(env).fetch(request());
    assert.equal(r.status,409);
    assert.equal(n,1);
    assert.ok(!(await r.text()).includes("HOST_SECRET"));
  }finally{globalThis.fetch=original;}
});
test("redacts provider failures and does not follow HTTP redirect",async()=>{
  const original=globalThis.fetch;let n=0;
  globalThis.fetch=async(_,opt)=>{
    n++;assert.equal(opt.redirect,"manual");
    return response({password:"PASSWORD_SECRET"},403);
  };
  try{
    const r=await new ServerspacePowerPlanEntrypoint(env).fetch(request());
    assert.equal(r.status,502);assert.equal(n,1);
    assert.ok(!(await r.text()).includes("PASSWORD_SECRET"));
  }finally{globalThis.fetch=original;}
});
test("public route, extra query and wrong method fail closed",async()=>{
  const original=globalThis.fetch;let n=0;
  globalThis.fetch=async()=>{n++;throw Error("MUST_NOT_FETCH");};
  try{
    const inst=new ServerspacePowerPlanEntrypoint(env);
    assert.equal((await inst.fetch(new Request("http://private/"))).status,404);
    assert.equal((await inst.fetch(new Request(endpoint+"?id=1"))).status,404);
    assert.equal((await inst.fetch(new Request(endpoint,{method:"GET"}))).status,405);
    assert.equal(n,0);
  }finally{globalThis.fetch=original;}
});
