import unittest,json,hashlib
from corpus_reader import normalize,metrics,read_window
VID="aLM-8X7VRyo";GUID="f0699e9e-ba27-452a-aa5d-8a34ab028ffe"
def fixture(asr=False):
    if asr:doc={"youtube_id_candidate":VID,"podcast_guid":GUID,"language":"ru","audio_duration_s":10,"segments":[{"start":1,"end":4,"text":"synthetic"},{"start":3,"end":9,"text":"sample"}]}
    else:doc={"video_id":VID,"language":"ru","expected_duration_s":10,"response":{"transcript":[{"start":1,"duration":3,"text":"synthetic"},{"start":3,"duration":6,"text":"sample"}]}}
    raw=json.dumps(doc).encode();receipt={"video_id":VID,"source":"asr" if asr else "native","expected_duration_s":10,"sha256":hashlib.sha256(raw).hexdigest(),"podcast_guid":GUID}
    return raw,receipt
class Tests(unittest.TestCase):
    def test_native(self):
        r=normalize(*fixture());self.assertEqual(r["timeline"],"youtube");self.assertEqual(r["segments"][0]["end"],4)
    def test_asr(self):
        r=normalize(*fixture(True));self.assertEqual(r["timeline"],"podcast_audio_not_verified_equal_to_youtube")
    def test_union(self):
        m=metrics(normalize(*fixture()));self.assertEqual(m["coverage_fraction"],.8);self.assertEqual(m["overlapping_segments"],1)
    def test_window(self):self.assertEqual(len(read_window(normalize(*fixture()),4,5)),1)
    def test_checksum(self):
        raw,receipt=fixture();receipt["sha256"]="0"*64
        with self.assertRaises(ValueError):normalize(raw,receipt)
    def test_guid(self):
        raw,receipt=fixture(True);receipt["podcast_guid"]="different"
        with self.assertRaises(ValueError):normalize(raw,receipt)
    def test_invalid_window(self):
        with self.assertRaises(ValueError):read_window(normalize(*fixture()),5,3)
if __name__=="__main__":unittest.main()
