import { connect } from "cloudflare:sockets";

export default {
  async fetch() { return new Response(null, {status:404}); },
  async queue(batch, env) {
    for (const msg of batch.messages) {
      if (msg.body?.probe !== env.NONCE || Date.now() > Number(env.EXPIRES_MS)) {
        msg.ack(); continue;
      }
      if (await env.RESULT.get("result")) { msg.ack(); continue; }
      let socket, timer;
      let result = "connection_failed";
      try {
        socket = connect({hostname: env.TARGET_HOST, port: 22});
        socket.closed.catch(() => {});
        result = await Promise.race([
          socket.opened.then(() => "tcp_open", () => "connection_failed"),
          new Promise(resolve => { timer = setTimeout(() => resolve("timeout"), 8000); })
        ]);
      } catch { result = "connection_failed"; }
      finally {
        clearTimeout(timer);
        if (socket) { try { await socket.close(); } catch {} }
      }
      await env.RESULT.put("result", JSON.stringify({result, port:22, nonce:env.NONCE}), {expirationTtl:300});
      msg.ack();
    }
  }
};
