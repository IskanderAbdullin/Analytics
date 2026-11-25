import assert from 'node:assert/strict';
import { Miniflare } from 'miniflare';
const mf=new Miniflare({modules:true,scriptPath:"dist/worker.js",compatibilityDate:"2025-11-01",compatibilityFlags:["nodejs_compat"]});
try {
  const res=await mf.dispatchFetch("http://fixture.invalid/");
  const body=await res.json();
  console.log(JSON.stringify(body));
  assert.equal(res.status,200);
  assert.deepEqual(body.stages,["import","stream","key-sign-verify","client-constructor"]);
  console.log("PASS local workerd fixture");
} finally { await mf.dispose(); }
