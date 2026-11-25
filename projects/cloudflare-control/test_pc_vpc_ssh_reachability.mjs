import test from "node:test";
import assert from "node:assert/strict";
import {probe,classify} from "./pc_vpc_ssh_reachability.mjs";
test("fixed destination and success with documented socket", async()=>{
  let closes=0;
  assert.equal(await probe({connect:async a=>{assert.equal(a,"127.0.0.1:22");return {readable:{},writable:{},close(){closes++}}}}),"tcp_open");
  assert.equal(closes,1);
});
test("specific code",async()=>assert.equal(await probe({connect:async()=>{throw new Error("ProxyError: connection_refused")}}),"connection_refused"));
test("type failure",async()=>assert.equal(await probe({connect:()=>{throw new TypeError("private text")}}),"connect_type_error"));
test("unknown code redacted",()=>assert.equal(classify(new Error("ProxyError: sensitive_string"),"connect",false),"unknown_proxy_error"));
test("missing method",async()=>assert.equal(await probe({}),"missing_connect_method"));
test("invalid socket",async()=>assert.equal(await probe({connect:async()=>({})}),"invalid_socket_shape"));
test("timeout",async()=>assert.equal(await probe({connect:()=>new Promise(()=>{})},5),"timeout"));
test("generic failure redacted",async()=>assert.equal(await probe({connect:()=>{throw new Error("secret details")}}),"connect_other_error"));
