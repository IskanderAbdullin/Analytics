"""Import authorized subtitle exports into a private, lossless corpus staging area.
No network, credentials, or publishing. Original bytes remain unchanged.
"""
import argparse, hashlib, html, json, math, re
from pathlib import Path

ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
STAMP = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})")
TIMING = re.compile(r"^\s*(\S+)\s+-->\s+(\S+)(?:\s+.*)?$")
LINE = re.compile(r"^\[(\d+(?::\d{2}){1,2})\]\s*(.*)$")
TAG = re.compile(r"<(?:/?(?:c(?:\.[^>]+)?|v(?:\s+[^>]+)?|i|b|u|ruby|rt|lang(?:\s+[^>]+)?)|\d{2}:\d{2}(?::\d{2})?\.\d{3})>")

def seconds(s):
    m = STAMP.fullmatch(s)
    if not m: raise ValueError("bad subtitle timestamp: " + s)
    h, minute, sec, ms = m.groups()
    if int(sec) >= 60 or (h is not None and int(minute) >= 60):
        raise ValueError("bad time component")
    return int(h or 0)*3600 + int(minute)*60 + int(sec) + int(ms)/1000

def plain(s):
    return html.unescape(TAG.sub("", s)).strip()

def parse_timed(text, fmt):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if fmt == "vtt":
        if not lines[0].startswith("WEBVTT"): raise ValueError("missing WEBVTT header")
        # Header metadata belongs to the original file; do not parse as a cue.
        i = 1
        while i < len(lines) and lines[i].strip(): i += 1
    else: i = 0
    out = []
    while i < len(lines):
        if not lines[i].strip(): i += 1; continue
        if fmt == "vtt" and re.match(r"^(NOTE(?:\s|$)|STYLE$|REGION$)", lines[i]):
            while i < len(lines) and lines[i].strip(): i += 1
            continue
        cue_id = None
        m = TIMING.match(lines[i])
        if not m:
            cue_id = lines[i]; i += 1
            if i >= len(lines): raise ValueError("orphan cue identifier")
            m = TIMING.match(lines[i])
        if not m: raise ValueError("malformed cue")
        a,b = map(seconds,m.groups())
        i += 1; body=[]
        while i < len(lines) and lines[i].strip():
            if TIMING.match(lines[i]): raise ValueError("missing cue separator")
            body.append(lines[i]); i += 1
        if b < a: raise ValueError("negative cue duration")
        raw = "\n".join(body)
        out.append({"start":a,"end":b,"text":plain(raw),"raw_text":raw,"cue_id":cue_id})
    return out

def parse_timestamped(text):
    out=[]
    for line in text.splitlines():
        m=LINE.match(line)
        if m:
            parts=[int(x) for x in m[1].split(":")]
            if any(x>=60 for x in parts[1:]): raise ValueError("bad timestamp component")
            start=0
            for x in parts: start=start*60+x
            out.append({"start":start,"end":None,"text":m[2],"raw_text":m[2],"cue_id":None})
        elif line.strip():
            if not out: raise ValueError("text precedes first timestamp")
            out[-1]["raw_text"]+="\n"+line
            out[-1]["text"]+="\n"+line
    return out

def normalize(raw,fmt,video_id,duration,language,source):
    if not ID.fullmatch(video_id): raise ValueError("invalid video ID")
    if not math.isfinite(duration) or duration<=0: raise ValueError("invalid duration")
    if language not in ("ru","ru-RU"): raise ValueError("expected original Russian captions")
    text=raw.decode("utf-8-sig")
    segments=parse_timestamped(text) if fmt=="txt" else parse_timed(text,fmt)
    if not segments or not any(x["text"].strip() for x in segments): raise ValueError("empty")
    if any(b["start"]<a["start"] for a,b in zip(segments,segments[1:])): raise ValueError("nonmonotonic")
    for i,s in enumerate(segments): s["index"]=i
    known=[s for s in segments if s["end"] is not None]
    last=max((s["end"] if s["end"] is not None else s["start"] for s in segments))
    first=segments[0]["start"]
    union=0.; end=0.; overlaps=0
    for s in known:
        a,b=s["start"],s["end"]
        if a<end: overlaps+=1
        union+=max(0.,min(b,duration)-max(a,end));end=max(end,b)
    return {"schema_version":1,"video_id":video_id,"source":source,"format":fmt,"language":language,
            "source_sha256":hashlib.sha256(raw).hexdigest(),"source_bytes":len(raw),
            "duration_s":duration,"timeline":"source_caption_timeline_unverified",
            "segments":segments,"metrics":{"segments":len(segments),"first_s":first,"last_s":last,
            "end_fraction":last/duration,"interval_coverage":union/duration if known else None,
            "overlaps":overlaps,"end_times_known":len(known)==len(segments),
            "review_status":"coverage_ok_unreviewed" if first<60 and .95<=last/duration<=1.05 else "coverage_review"}}

def import_file(source_file,private_dir,video_id,duration,language,source):
    if not private_dir.is_absolute(): raise ValueError("private output directory must be absolute")
    fmt=source_file.suffix.lower().lstrip(".")
    if fmt not in ("vtt","srt","txt"): raise ValueError("unsupported subtitle format")
    raw=source_file.read_bytes()
    if len(raw)>16*1024*1024: raise ValueError("source too large")
    record=normalize(raw,fmt,video_id,duration,language,source)
    # Content addressed and non-overwriting, safe to repeat after interruption.
    target=private_dir/video_id/record["source_sha256"]
    target.mkdir(parents=True,exist_ok=True)
    original=target/("original."+fmt)
    normalized=target/"normalized.json"
    payload=json.dumps(record,ensure_ascii=False,separators=(",",":")).encode()
    for path,data in ((original,raw),(normalized,payload)):
        try:
            with path.open("xb") as f: f.write(data)
        except FileExistsError:
            if path.read_bytes()!=data: raise ValueError("existing archive conflicts")
        if path.read_bytes()!=data: raise ValueError("readback mismatch")
    return {"video_id":video_id,"source_sha256":record["source_sha256"],"normalized_sha256":hashlib.sha256(payload).hexdigest(),**record["metrics"]}

def main():
    p=argparse.ArgumentParser();p.add_argument("file",type=Path);p.add_argument("private_dir",type=Path)
    p.add_argument("--video-id",required=True);p.add_argument("--duration",type=float,required=True)
    p.add_argument("--language",default="ru");p.add_argument("--source",required=True)
    a=p.parse_args();print(json.dumps(import_file(a.file,a.private_dir,a.video_id,a.duration,a.language,a.source)))
if __name__=="__main__":main()
