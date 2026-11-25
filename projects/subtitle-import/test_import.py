import unittest,tempfile
from pathlib import Path
from subtitle_import import normalize,import_file
VID="aLM-8X7VRyo"
VTT=b"WEBVTT\nKind: captions\n\nNOTE note\nignored\n\n00:00:01.000 --> 00:00:04.000 align:start\n<c>sample</c> &amp; test\n\n00:00:03.000 --> 00:00:09.000\nsecond line\n"
SRT=b"1\r\n00:00:01,000 --> 00:00:09,000\r\nsample\r\n"
def run(raw,fmt):return normalize(raw,fmt,VID,10,"ru","authorized synthetic")
class Tests(unittest.TestCase):
 def test_vtt(self):
  r=run(VTT,"vtt");self.assertEqual(len(r["segments"]),2);self.assertEqual(r["segments"][0]["text"],"sample & test");self.assertEqual(r["metrics"]["interval_coverage"],.8);self.assertEqual(r["metrics"]["overlaps"],1)
 def test_srt(self):self.assertEqual(run(SRT,"srt")["segments"][0]["end"],9)
 def test_line_start_only(self):
  r=run(b"[0:01] sample\ncontinuation\n[0:09] end","txt");self.assertIsNone(r["segments"][0]["end"]);self.assertIsNone(r["metrics"]["interval_coverage"])
 def test_bad_order(self):
  with self.assertRaises(ValueError):run(b"[0:09] end\n[0:01] sample","txt")
 def test_bad_range(self):
  with self.assertRaises(ValueError):run(b"1\n00:00:09,000 --> 00:00:01,000\nsample","srt")
 def test_empty(self):
  with self.assertRaises(ValueError):run(b"WEBVTT\n\n","vtt")
 def test_idempotence(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);file=root/"sample.vtt";file.write_bytes(VTT);dst=root/"private"
   a=import_file(file,dst,VID,10,"ru","authorized synthetic");b=import_file(file,dst,VID,10,"ru","authorized synthetic")
   self.assertEqual(a,b);self.assertEqual((dst/VID/a["source_sha256"]/"original.vtt").read_bytes(),VTT)
 def test_invalid_component(self):
  with self.assertRaises(ValueError):run(b"[0:99] invalid","txt")
if __name__=="__main__":unittest.main()
