import unittest,urllib.parse,tempfile
from pathlib import Path
from collector import build_url,validate,run
from unittest.mock import patch
class Tests(unittest.TestCase):
 def test_native(self):
  q=urllib.parse.parse_qs(urllib.parse.urlsplit(build_url("aLM-8X7VRyo")).query)
  self.assertEqual(q["mode"],["native"]);self.assertEqual(q["text"],["false"])
 def test_bad_id(self):
  with self.assertRaises(ValueError):build_url("https://elsewhere.example")
 def test_coverage(self):
  d={"lang":"ru","content":[{"text":"sample","offset":0,"duration":1000},{"text":"test","offset":98000,"duration":1000}]}
  self.assertEqual(validate(d,100)["status"],"coverage_ok_unreviewed")
  self.assertEqual(validate(d,200)["status"],"coverage_review")
  self.assertEqual(validate({**d,"lang":"en"},100)["status"],"wrong_language")
 def test_empty(self):self.assertEqual(validate({"lang":"ru","content":[]},100)["status"],"invalid_or_empty")
 def test_no_network_dry_run(self):
  with tempfile.TemporaryDirectory() as tmp,patch("collector.http") as h:
   run(Path(tmp)/"missing.csv",Path(tmp)/"private",3,95,False);h.assert_not_called()
if __name__=="__main__":unittest.main()
