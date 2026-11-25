// Synthetic loopback SSH authentication only. No external server, commands,
// forwarding, production credentials, or Cloudflare resources.
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { connect } from 'node:net';
import { Duplex } from 'node:stream';
import { once } from 'node:events';
import ssh2 from 'ssh2';
const {Client,Server,utils}=ssh2;
const dir=mkdtempSync(join(tmpdir(),'ssh-auth-fixture-'));
let server;
let accepted=0;
try {
  const host=join(dir,'host'), user=join(dir,'client');
  for(const path of [host,user]) execFileSync('ssh-keygen',['-q','-t','ed25519','-N','','-f',path],{stdio:'ignore'});
  const hostPub=utils.parseKey(readFileSync(host+'.pub'));
  const userPub=utils.parseKey(readFileSync(user+'.pub'));
  assert(!(hostPub instanceof Error)); assert(!(userPub instanceof Error));
  const fingerprint=createHash('sha256').update(hostPub.getPublicSSH()).digest('hex');
  server=new Server({hostKeys:[readFileSync(host)]}, peer=>{
    peer.on('error',()=>{});
    peer.on('authentication',ctx=>{
      if(ctx.method!=='publickey'||ctx.username!=='fixture'||ctx.key.algo!==userPub.type||
         !ctx.key.data.equals(userPub.getPublicSSH())) return ctx.reject(['publickey']);
      if(!ctx.signature) return ctx.accept();
      if(userPub.verify(ctx.blob,ctx.signature,ctx.hashAlgo)!==true) return ctx.reject(['publickey']);
      accepted++;
      ctx.accept();
    });
    peer.on('session',(_accept,reject)=>reject());
  });
  server.listen(0,'127.0.0.1'); await once(server,'listening');
  const port=server.address().port;
  async function login(pin){
    const tcp=connect({host:'127.0.0.1',port}); await once(tcp,'connect');
    const stream=Duplex.fromWeb(Duplex.toWeb(tcp));
    const client=new Client();
    let verified=false;
    const state=await new Promise(resolve=>{
      const timer=setTimeout(()=>{client.destroy();stream.destroy();resolve('timeout')},8000);
      const finish=out=>{clearTimeout(timer);resolve(out)};
      client.on('error',()=>finish('rejected'));
      client.on('ready',()=>finish('ready'));
      client.on('close',()=>finish('closed'));
      client.connect({sock:stream,username:'fixture',privateKey:readFileSync(user),hostHash:'sha256',
        hostVerifier:key=>{verified=key===pin;return verified},readyTimeout:5000});
    });
    client.end(); stream.destroy(); tcp.destroy();
    return {state,verified};
  }
  assert.deepEqual(await login(fingerprint),{state:'ready',verified:true});
  assert.equal(accepted,1);
  console.log('PASS synthetic SSH key authentication through Web/Node stream adapter');
  const wrong=await login('0'.repeat(64));
  assert.notEqual(wrong.state,'ready');assert.equal(wrong.verified,false);
  assert.equal(accepted,1);
  console.log('PASS wrong server host key rejected before authentication');
}finally{
  if(server){server.close()}
  rmSync(dir,{recursive:true,force:true});
}
