// Local-only workerd fixture. No real host, socket, keys, command or cloud binding.
import ssh2 from "ssh2";
import { Duplex } from "node:stream";
import { generateKeyPairSync, createHash } from "node:crypto";
const { Client, utils } = ssh2;
export default {
  async fetch() {
    const stages = [];
    try {
      if (typeof Client !== "function") throw new Error("client_missing");
      stages.push("import");
      if (typeof Duplex.fromWeb !== "function") throw new Error("stream_adapter_missing");
      const input = new TransformStream(), output = new TransformStream();
      const duplex = Duplex.fromWeb({readable:input.readable,writable:output.writable});
      duplex.on("error",()=>{});
      const read = output.readable.getReader();
      const result = read.read();
      duplex.write(Buffer.from([0,1,127,255]));
      const value = await result;
      if (Buffer.from(value.value).toString("hex") !== "00017fff") throw new Error("stream_mismatch");
      duplex.destroy();
      await read.cancel().catch(()=>{});
      stages.push("stream");
      const pair=generateKeyPairSync("ed25519");
      const pem=pair.privateKey.export({type:"pkcs8",format:"pem"});
      const parsed=utils.parseKey(pem);
      if (parsed instanceof Error) throw new Error("parse_key");
      const payload=Buffer.from("synthetic-fixture-only");
      const signature=parsed.sign(payload);
      if (signature instanceof Error || parsed.verify(payload,signature)!==true) throw new Error("verify");
      const digest=createHash("sha256").update(parsed.getPublicSSH()).digest("hex");
      if(!/^[0-9a-f]{64}$/.test(digest)) throw new Error("fingerprint");
      stages.push("key-sign-verify");
      new Client();
      stages.push("client-constructor");
      return Response.json({ok:true,stages});
    } catch(e) {
      // Fixture errors only; no production credentials or identifiers exist.
      return Response.json({ok:false,stages,error:String(e?.message||e).slice(0,300)},{status:500});
    }
  }
};
