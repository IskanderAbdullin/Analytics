import unittest
import pc_vpc_close_reasons as m

class CloseReasonTests(unittest.TestCase):
    def test_only_aggregate(self):
        self.assertEqual(m.summary({"success":True,"result":[{"reason":"ORIGIN_UNREACHABLE","n":2,"secret":"not emitted"}]}),{"result":"ok","reasons":{"ORIGIN_UNREACHABLE":2}})
    def test_unknown_redacted(self):
        self.assertEqual(m.summary({"success":True,"result":[{"reason":"private-data","n":1}]}),{"result":"ok","reasons":{"UNRECOGNIZED":1}})
    def test_empty_not_negative_proof(self):
        self.assertEqual(m.summary({"success":True,"result":[]})["result"],"no_matching_records")
    def test_rejected(self):
        self.assertEqual(m.summary({"success":False,"errors":[{"message":"private"}]}),{"result":"query_rejected"})
    def test_fixed_scope(self):
        self.assertIn("OnrampType = 'WORKERS_VPC'",m.SQL)
        self.assertIn("pc-vpc-status-%",m.SQL)
        self.assertIn("pc-vpc-tcp-%",m.SQL)
        self.assertNotIn("SELECT *",m.SQL)

if __name__=="__main__":
    unittest.main()
