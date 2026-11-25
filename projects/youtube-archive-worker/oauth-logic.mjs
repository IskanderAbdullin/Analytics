export const ORIGIN="https://youtube-archive-owner.videns42.workers.dev";
export const CALLBACK=ORIGIN+"/callback";
export const SCOPE="https://www.googleapis.com/auth/youtube.force-ssl";
export const READ="youtube:read";
export const configured=env=>typeof env.GOOGLE_CLIENT_ID==="string"&&env.GOOGLE_CLIENT_ID.endsWith(".apps.googleusercontent.com")&&typeof env.GOOGLE_CLIENT_SECRET==="string"&&env.GOOGLE_CLIENT_SECRET.length>0&&/^UC[A-Za-z0-9_-]{22}$/.test(env.YOUTUBE_OWNER_CHANNEL_ID??"");
export function permitted(req){
 try{
  const client=new URL(req.clientId),redirect=new URL(req.redirectUri);
  return client.origin==="https://chatgpt.com"&&!client.search&&!client.hash&&(/^\/oauth\/(?:[A-Za-z0-9_-]+\/)?client\.json$/.test(client.pathname))&&
  redirect.origin==="https://chatgpt.com"&&!redirect.search&&!redirect.hash&&(redirect.pathname==="/connector_platform_oauth_redirect"||/^\/connector\/oauth\/[A-Za-z0-9_-]+$/.test(redirect.pathname));
 }catch{return false}
}
export const escape=s=>String(s).replace(/[&<>"']/g,c=>"&#"+c.charCodeAt(0)+";");
export async function googleAuthorize(env,state,verifier){
 const raw=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(verifier));
 const challenge=btoa(String.fromCharCode(...new Uint8Array(raw))).replaceAll("+","-").replaceAll("/","_").replaceAll("=","");
 const url=new URL("https://accounts.google.com/o/oauth2/v2/auth");
 const params={client_id:env.GOOGLE_CLIENT_ID,redirect_uri:CALLBACK,response_type:"code",scope:SCOPE,state,code_challenge:challenge,code_challenge_method:"S256",access_type:"offline",prompt:"consent select_account"};
 for(const [k,v] of Object.entries(params))url.searchParams.set(k,v);
 return url.href;
}
export async function googleToken(env,params,old){
 const res=await fetch("https://oauth2.googleapis.com/token",{method:"POST",redirect:"error",headers:{"content-type":"application/x-www-form-urlencoded"},body:new URLSearchParams({client_id:env.GOOGLE_CLIENT_ID,client_secret:env.GOOGLE_CLIENT_SECRET,...params})});
 let result;try{result=await res.json()}catch{throw new Error("upstream_unavailable")}
 if(!res.ok)throw new Error(result.error==="invalid_grant"?"invalid_grant":"upstream_unavailable");
 if(typeof result.access_token!=="string"||!Number.isFinite(Number(result.expires_in))||Number(result.expires_in)<60||result.scope&&!result.scope.split(/\s+/).includes(SCOPE))throw new Error("invalid_grant");
 const refreshToken=result.refresh_token??old?.refreshToken;
 if(typeof refreshToken!=="string"||!refreshToken)throw new Error("invalid_grant");
 return {accessToken:result.access_token,refreshToken,expiresAt:Date.now()+Number(result.expires_in)*1000,channelId:env.YOUTUBE_OWNER_CHANNEL_ID};
}
export async function checkOwner(env,accessToken){
 let page;
 for(let i=0;i<20;i++){
  const url=new URL("https://www.googleapis.com/youtube/v3/channels");
  url.searchParams.set("part","id");url.searchParams.set("mine","true");url.searchParams.set("maxResults","50");if(page)url.searchParams.set("pageToken",page);
  const res=await fetch(url,{method:"GET",redirect:"error",headers:{authorization:"Bearer "+accessToken}});
  if(!res.ok)return false;
  const data=await res.json();if(data.items?.some(x=>x.id===env.YOUTUBE_OWNER_CHANNEL_ID))return true;
  page=data.nextPageToken;if(!page)break;
 }
 return false;
}
export async function refresh(env,props){
 if(!configured(env)||props.channelId!==env.YOUTUBE_OWNER_CHANNEL_ID)throw new Error("invalid_grant");
 return googleToken(env,{grant_type:"refresh_token",refresh_token:props.refreshToken},props);
}
