import {test} from "node:test";
import assert from "node:assert/strict";
import {registered,calls,setAuthorized,setFakeState,setFakeStatus} from "./oauth-plan-fixture.mjs";

test("registers a single owner-only tool with raw Zod action schema shape",()=>{
 assert.equal(registered.length,1);
 assert.equal(registered[0].name,"serverspace_plan_power");
 const fields=registered[0].config.inputSchema;
 assert.deepEqual(Object.keys(fields),["action"]);
 assert.equal(fields.action.kind,"enum");
 assert.deepEqual(fields.action.values,["on","shutdown","reboot","off","reset"]);
});
test("authorized reboot preview sends only fixed private Service request",async()=>{
 setAuthorized(true);setFakeStatus(200);setFakeState("ready");
 const r=await registered[0].handler({action:"reboot"});
 assert.equal(r.isError,undefined);
 assert.deepEqual(JSON.parse(r.content[0].text),{
   action:"reboot",state:"ready",execution_enabled:false,
   hard_power:false,method_if_authorized:"POST"
 });
 assert.equal(calls.length,1);
 assert.deepEqual(calls[0],[
   "http://serverspace.internal/internal/serverspace/power-plan","POST",
   {mode:"plan",target:"sole",action:"reboot"}
 ]);
});
test("non-owner is rejected and cannot reach private Service binding",async()=>{
 const before=calls.length;setAuthorized(false);
 const r=await registered[0].handler({action:"reset"});
 assert.equal(r.isError,true);
 assert.equal(r.content[0].text,"SERVERSPACE_PLAN_UNAVAILABLE");
 assert.equal(calls.length,before);
 setAuthorized(true);
});
test("unexpected upstream state cannot be shown as an executable plan",async()=>{
 setFakeState("submitted");
 const r=await registered[0].handler({action:"reboot"});
 assert.equal(r.isError,true);
 assert.equal(r.content[0].text,"SERVERSPACE_PLAN_UNAVAILABLE");
 setFakeState("ready");
});
test("provider error returns fixed code without error payload",async()=>{
 setFakeStatus(503);
 const r=await registered[0].handler({action:"on"});
 assert.equal(r.isError,true);
 assert.equal(r.content[0].text,"SERVERSPACE_PLAN_UNAVAILABLE");
 setFakeStatus(200);
});
