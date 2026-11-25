import { connect } from "cloudflare:sockets";
export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST" || new URL(request.url).pathname !== "/probe" ||
        request.headers.get("Authorization") !== "Bearer " + env.PROBE_TOKEN ||
        Date.now() > Number(env.EXPIRES_MS)) return new Response(null, {status: 404});
    let socket;
    let timer;
    let result = "connection_failed";
    try {
      socket = connect({hostname: env.TARGET_HOST, port: 22});
      socket.closed.catch(() => {});
      result = await Promise.race([
        socket.opened.then(() => "tcp_open", () => "connection_failed"),
        new Promise(resolve => {timer = setTimeout(() => resolve("timeout"), 8000);})
      ]);
    } catch {
      result = "connection_failed";
    } finally {
      clearTimeout(timer);
      if (socket) ctx.waitUntil(socket.close().catch(() => {}));
    }
    return Response.json({result}, {headers: {"Cache-Control": "no-store"}});
  }
};
