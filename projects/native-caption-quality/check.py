"""Quality checks of native archive, no source text in public logs."""
import os,hashlib,json,re,urllib.request,urllib.parse,unicodedata
NS="1468098312aa47c995e87ff51252a38a"
CASES=[
 {"id":"aLM-8X7VRyo","duration":10245,"title":"Новый обвал на рынках: что за паника в России и мире? / Продавать все? Акции, золото, крипта","anchors":[{"name":"no_add","time":7703,"window":35,"terms":[r"не\s+стал\s+увелич",r"не\s+увелич"]},{"name":"entry_7630","time":7720,"window":35,"terms":[r"7\s*630",r"семь\s+тысяч\s+шестьсот\s+тридцать",r"76\s*30"]},{"name":"target_6500","time":7835,"window":35,"terms":[r"6\s*500",r"шесть\s+тысяч\s+пятьсот"]}]},
 {"id":"Mz2iGw8Zcek","duration":9696,"title":"Эпидемия дефолтов, удары по дата-центрам и разгон инфляции: будет хуже? / ЖКХ, облигации, рубль","anchors":[{"name":"trigger_7600","time":8732,"window":60,"terms":[r"7\s*600",r"семь\s+тысяч\s+шестьсот",r"76\s*00"]}]},
 {"id":"Z3mNOytc-W4","duration":1502,"title":"Торговая война США и Китая, будущее Netflix и падение «Яндекса»","anchors":[]}
]
def norm(s):
 s=unicodedata.normalize("NFKC",s).lower().replace("ё","е")
 return " ".join(re.findall(r"[a-zа-я0-9]+",s))
def main():
 base="https://api.cloudflare.com/client/v4/accounts/"+os.environ["CLOUDFLARE_ACCOUNT_ID"]+"/storage/kv/namespaces/"+NS+"/values/"
 headers={"Authorization":"Bearer "+os.environ["CLOUDFLARE_API_TOKEN"]}
 for case in CASES:
  key="native/youtube/"+case["id"]+"/fta-v1.json"
  with urllib.request.urlopen(urllib.request.Request(base+urllib.parse.quote(key,safe=""),headers=headers),timeout=30) as r:raw=r.read(8*1024*1024)
  record=json.loads(raw);d=record["response"];lines=d["transcript"]
  text=" ".join(x["text"] for x in lines)
  title_a=set(norm(case["title"]).split());title_b=set(norm(d.get("title","")).split())
  gaps=[];overlaps=0;coverage=0;last=0
  for x in lines:
   a,b=x["start"],x["start"]+x["duration"]
   if a>last:gaps.append(a-last)
   else:overlaps+=1
   coverage+=max(0,b-max(a,last));last=max(last,b)
  anchors={}
  for a in case["anchors"]:
   window=" ".join(x["text"] for x in lines if abs(x["start"]-a["time"])<=a["window"])
   window=norm(window)
   anchors[a["name"]]=any(re.search(t,window) for t in a["terms"])
  cyr=sum("а"<=c.lower()<="я" or c.lower()=="ё" for c in text);letters=sum(c.isalpha() for c in text)
  duplicates=sum(norm(a["text"])==norm(b["text"]) for a,b in zip(lines,lines[1:]))
  result={"video_id":case["id"],"sha256":hashlib.sha256(raw).hexdigest(),"title_similarity":round(len(title_a&title_b)/max(1,len(title_a|title_b)),4),"segments":len(lines),"words":len(text.split()),"cyrillic_letter_fraction":round(cyr/max(1,letters),4),"covered_seconds":round(coverage,2),"speech_interval_fraction":round(coverage/case["duration"],4),"largest_gap_s":round(max(gaps,default=0),2),"overlap_segments":overlaps,"identical_adjacent_lines":duplicates,"anchors":anchors}
  print("QUALITY "+json.dumps(result,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
