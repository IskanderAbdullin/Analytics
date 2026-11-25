const CODES = new Set(["connection_refused","connection_timeout","destination_unavailable","destination_not_found","destination_ip_prohibited","destination_ip_unroutable","dns_error","http_request_denied","proxy_internal_error","connection_read_timeout","connection_write_timeout","rate_limited","connection_failed","connection_reset","tls_error"]);
export function classify(e, phase, expired) {
  if (expired) return "timeout";
  const msg = typeof e?.message === "string" ? e.message : "";
  const code = /ProxyError:\s*([a-z_]+)/i.exec(msg)?.[1]?.toLowerCase();
  if (code && CODES.has(code)) return code;
  if (code) return "unknown_proxy_error";
  if (e?.name === "TypeError") return phase === "connect" ? "connect_type_error" : "socket_type_error";
  if (e?.name === "AbortError" || e?.name === "TimeoutError") return "timeout";
  return phase === "connect" ? "connect_other_error" : "socket_other_error";
}
export async function probe(binding, deadline = 8000) {
  if (typeof binding?.connect !== "function") return "missing_connect_method";
  let socket, timer, expired = false, phase = "connect";
  try {
    // Promise.resolve handles documented Promise<Socket> and synchronous test mocks.
    const pending = Promise.resolve(binding.connect("127.0.0.1:22"));
    pending.then(s => { if (expired) return Promise.resolve(s.close()).catch(()=>{}); }).catch(()=>{});
    socket = await Promise.race([pending, new Promise((_, reject) => {
      timer = setTimeout(()=> { expired = true; reject(new Error("deadline")); },deadline);
    })]);
    // VPC connect resolves once established; opened/closed are not prerequisites.
    phase = "socket";
    if (typeof socket?.close !== "function" || !socket.readable || !socket.writable) return "invalid_socket_shape";
    if (socket.closed && typeof socket.closed.catch === "function") socket.closed.catch(()=>{});
    return "tcp_open";
  } catch(e) {
    return classify(e, phase, expired);
  } finally {
    clearTimeout(timer);
    if (socket && typeof socket.close === "function") {
      try { await Promise.resolve(socket.close()); } catch {}
    }
  }
}
export default {
  async fetch() { return new Response(null, {status:404}); },
  async queue(batch, env) {
    for (const msg of batch.messages) {
      if (msg.body?.probe !== env.NONCE || Date.now() > Number(env.EXPIRES_MS)) { msg.ack(); continue; }
      if (await env.RESULT.get("result")) { msg.ack(); continue; }
      const result = await probe(env.PRIVATE_TUNNEL);
      await env.RESULT.put("result",JSON.stringify({result,port:22,nonce:env.NONCE}),{expirationTtl:300});
      msg.ack();
    }
  }
};
