export default {
  async fetch() { return new Response(null, {status:404}); },
  async queue(batch, env) {
    for (const msg of batch.messages) {
      if (msg.body?.probe !== env.NONCE || Date.now() > Number(env.EXPIRES_MS)) {
        msg.ack(); continue;
      }
      if (await env.RESULT.get("result")) { msg.ack(); continue; }
      let result = "network_error";
      try {
        const res = await env.PRIVATE_PC.fetch("http://localhost:8765/v1/status", {
          method:"POST", headers:{"Content-Type":"application/json"}, body:"{}",
          redirect:"manual", signal:AbortSignal.timeout(10000)
        });
        result = "http_" + res.status;
        if (res.body) await res.body.cancel();
      } catch (e) {
        result = e?.name === "TimeoutError" || e?.name === "AbortError" ? "timeout" : "network_error";
      }
      await env.RESULT.put("result", JSON.stringify({result, port:8765, nonce:env.NONCE}), {expirationTtl:300});
      msg.ack();
    }
  }
};
