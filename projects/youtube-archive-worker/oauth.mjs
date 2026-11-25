import {OAuthProvider,OAuthError,authorizationErrorRedirect} from "@cloudflare/workers-oauth-provider";
import core from "./worker.mjs";
import {ORIGIN,CALLBACK,READ,configured,permitted,escape,googleAuthorize,googleToken,checkOwner,refresh} from "./oauth-logic.mjs";
const reply=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{"content-type":"application/json","cache-control":"no-store","x-content-type-options":"nosniff"}});
const redirect=(headers,location)=>{headers.set("Location",location);return new Response(null,{status:302,headers})};
const errorPage=(text,status=400)=>new Response(text,{status,headers:{"content-type":"text/plain; charset=utf-8","cache-control":"no-store","x-frame-options":"DENY"}});
function denied(request,headers){return redirect(headers,authorizationErrorRedirect(request,"access_denied"))}
const defaultHandler={async fetch(req,env){
 const url=new URL(req.url);
 if(url.pathname==="/healthz"&&req.method==="GET")return reply({ok:true,service:"youtube-archive",version:"0.2.0",googleOAuthConfigured:configured(env)});
 if(url.pathname==="/authorize"||url.pathname==="/callback"){
  if(!configured(env))return errorPage("Google OAuth is not configured. Configure the owner channel and Google OAuth client in the Worker settings.",503);
  const helper=env.OAUTH_PROVIDER;
  try{
   if(url.pathname==="/authorize"&&req.method==="GET"){
    const request=await helper.parseAuthRequest(req);
    if(!permitted(request))return errorPage("Only the verified ChatGPT OAuth client is allowed.",403);
    const consent=await helper.beginConsent(request);
    consent.headers.set("content-type","text/html; charset=utf-8");
    return new Response('<!doctype html><html lang="ru"><meta charset="utf-8"><title>Архив стримов</title><h1>Подключить ChatGPT к архиву YouTube?</h1><p>Клиент и адрес возврата: chatgpt.com. Только чтение списка твоих видео и существующих субтитров. Google попросит разрешение youtube.force-ssl; этот сервер не содержит операций записи или удаления.</p><form method="post"><input type="hidden" name="handle" value="'+escape(consent.handle)+'"><button name="decision" value="approve">Продолжить в Google</button> <button name="decision" value="deny">Отмена</button></form></html>',{headers:consent.headers});
   }
   if(url.pathname==="/authorize"&&req.method==="POST"){
    const form=await req.formData(),handle=String(form.get("handle")??"");
    if(form.get("decision")!=="approve"){const result=await helper.denyConsent(req,handle);return new Response(null,{status:302,headers:result.headers})}
    const approved=await helper.approveConsent(req,handle,{scope:[READ,"offline_access"]});
    if(!permitted(approved.request))return errorPage("Client not allowed",403);
    const verifier=crypto.randomUUID()+crypto.randomUUID();
    const upstream=await helper.beginUpstream(approved.request,{data:{verifier},headers:approved.headers});
    return redirect(upstream.headers,await googleAuthorize(env,upstream.state,verifier));
   }
   if(url.pathname==="/callback"&&req.method==="GET"){
    const original=await helper.finishUpstream(req);
    const {request,data,headers}=original;
    if(!permitted(request))return errorPage("Client not allowed",403);
    const code=url.searchParams.get("code");
    if(!code||url.searchParams.has("error"))return denied(request,headers);
    let props;
    try{
     props=await googleToken(env,{grant_type:"authorization_code",code,code_verifier:data.verifier,redirect_uri:CALLBACK});
     if(!await checkOwner(env,props.accessToken))return denied(request,headers);
    }catch{return denied(request,headers)}
    const {redirectTo}=await helper.completeAuthorization({request,userId:props.channelId,metadata:{label:"YouTube archive owner"},scope:request.scope,props});
    return redirect(headers,redirectTo);
   }
   return errorPage("Method not allowed",405);
  }catch{return errorPage("Authorization could not be completed. Start again from ChatGPT.",400)}
 }
 return errorPage("Not found",404);
}};
const apiHandler={async fetch(req,env,ctx){
 if(!configured(env)||!ctx.props||ctx.props.channelId!==env.YOUTUBE_OWNER_CHANNEL_ID||!ctx.auth?.scope?.includes(READ))return reply({error:"access_denied"},403);
 let props=ctx.props;
 if(props.expiresAt<Date.now()+60000){try{props=await refresh(env,props)}catch{return reply({error:"reauthorization_required"},401)}}
 const headers=new Headers(req.headers);headers.set("authorization","Bearer "+props.accessToken);
 return core.fetch(new Request(req,{headers}),{allowedChannel:props.channelId});
}};
export default new OAuthProvider({
 apiRoute:"/mcp",apiHandler,defaultHandler,authorizeEndpoint:"/authorize",tokenEndpoint:"/oauth/token",
 resourceMetadata:{resource:ORIGIN+"/mcp",authorization_servers:[ORIGIN]},
 scopesSupported:[READ,"offline_access"],requiredScopes:[READ],clientIdMetadataDocumentEnabled:true,
 accessTokenTTL:1800,refreshTokenTTL:30*86400,refreshTokenIdleTTL:30*86400,
 async tokenExchangeCallback({grantType,props,env}){
  if(grantType!=="refresh_token")return;
  try{return {newProps:await refresh(env,props)}}catch(e){
   if(e.message==="invalid_grant")throw new OAuthError("invalid_grant",{description:"Google authorization expired or was revoked"});
   throw new OAuthError("temporarily_unavailable",{description:"Google authorization unavailable",statusCode:503});
  }
 }
});
