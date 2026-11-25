export default {
  async fetch() { return new Response(null,{status:404}); },
  async queue(batch, env) {
    for (const msg of batch.messages) {
      if (msg.body?.probe !== env.NONCE || Date.now() > Number(env.EXPIRES_MS)) {
        msg.ack(); continue;
      }
      if (await env.RESULT.get("result")) { msg.ack(); continue; }
      let socket, result = "connection_failed", timer, expired = false;
      try {
        const pending = env.PRIVATE_TUNNEL.connect({hostname:"127.0.0.1",port:22});
        pending.then(s=>{if(expired) return s.close().catch(()=>{});}).catch(()=>{});
        socket = await Promise.race([pending,new Promise((_,reject)=>{
          timer=setTimeout(()=>{expired=true;reject(new Error("probe_deadline"));},8000);
        })]);
        socket.closed.catch(()=>{});
        await socket.opened;
        result = "tcp_open";
      } catch (e) {
        const allowed = ["connection_refused","connection_timeout","destination_unavailable",
          "destination_not_found","destination_ip_prohibited","destination_ip_unroutable",
          "dns_error","http_request_denied","proxy_internal_error"];
        const code = allowed.find(x=>String(e?.message||"").includes("ProxyError: "+x));
        result = expired ? "timeout" : code || "connection_failed";
      } finally {
        clearTimeout(timer);
        if(socket) { try { await socket.close(); } catch {} }
      }
      await env.RESULT.put("result",JSON.stringify({result,port:22,nonce:env.NONCE}),{expirationTtl:300});
      msg.ack();
    }
  }
};
