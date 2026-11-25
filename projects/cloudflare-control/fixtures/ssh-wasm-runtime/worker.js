// Isolated library initialization check. No network, actual host, keys or shell.
import { initWasmSshClient, SshClient } from "wasm-ssh-client";
export default { async fetch() {
  const stages=[];
  try {
    if(typeof initWasmSshClient!=="function" || typeof SshClient!=="function") throw new Error("missing_exports");
    stages.push("exports");
    await initWasmSshClient();
    stages.push("wasm_init");
    return Response.json({ok:true,stages});
  } catch(e) {
    return Response.json({ok:false,stages,error:String(e?.message||e).slice(0,300)},{status:500});
  }
}};
