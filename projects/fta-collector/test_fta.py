import unittest,datetime,tempfile,json,urllib.parse
from pathlib import Path
from unittest.mock import patch
from fta_collector import build_url,validate,count_recent,run
from archive_reader import read_window
class T(unittest.TestCase):
 def fixture(self):return {"language":"ru","transcript":[{"text":"synthetic","start":1,"duration":2},{"text":"test","start":97,"duration":2}]}
 def test_native(self):
  q=urllib.parse.parse_qs(urllib.parse.urlsplit(build_url("aLM-8X7VRyo")).query)
  self.assertEqual(q,{"video_url":["aLM-8X7VRyo"],"lang":["ru"],"format":["json"]})
 def test_invalid_id(self):
  with self.assertRaises(ValueError):build_url("http://example.com")
 def test_coverage(self):
  self.assertEqual(validate(self.fixture(),100)["status"],"coverage_ok_unreviewed")
  self.assertEqual(validate(self.fixture(),200)["status"],"coverage_review")
 def test_language(self):
  self.assertEqual(validate({**self.fixture(),"language":"en"},100)["status"],"wrong_language")
 def test_invalid_timestamps(self):
  d=self.fixture();d["transcript"][1]["start"]=0
  self.assertEqual(validate(d,100)["status"],"invalid_segments")
 def test_recent(self):
  at=datetime.datetime(2026,11,25,11,30,tzinfo=datetime.timezone.utc)
  r=[{"provider_attempt":True,"utc":"2026-11-25T11:00:00+00:00"},{"provider_attempt":True,"utc":"2026-11-25T10:00:00+00:00"},{"provider_attempt":False,"utc":"2026-11-25T11:15:00+00:00"}]
  self.assertEqual(count_recent(r,at),1)
 def test_dry_run(self):
  with tempfile.TemporaryDirectory() as temp,patch("fta_collector.request") as req:
   root=Path(temp);q=root/"q.jsonl";q.write_text(json.dumps({"youtube_id":"aLM-8X7VRyo","duration_s":100,"transcript_status":"not_archived"})+"\n")
   run(q,root/"ledger.jsonl",3,0,False);req.assert_not_called()
 def test_reader_window(self):
  rows=read_window({"response":self.fixture()},95,100)
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]["start"],97)
if __name__=="__main__":unittest.main()
