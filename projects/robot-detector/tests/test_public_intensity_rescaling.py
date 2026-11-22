"""Source-free falsifications, no market p-values or actor labels."""
import unittest
from tools.public_intensity_rescaling import Abstain, Exposure, rescaled_cluster_gaps as run

class TestRescaling(unittest.TestCase):
    def test_constant_hazard(self):
        self.assertEqual(run([0,1000,3000],[Exposure(0,3000,2)]),(2.,4.))
    def test_split_fill(self):
        e=[Exposure(0,3000,1)]
        self.assertEqual(run([0,1000,3000],e),run([0,0,1000,1000,3000],e))
    def test_coarse_occupancy_does_not_fix_gap(self):
        e=[Exposure(0,10000,1)]
        self.assertNotEqual(run([100,5100],e),run([100,9900],e))
    def test_missing_feed(self):
        with self.assertRaisesRegex(Abstain,"INCOMPLETE_EXPOSURE"):
            run([0,3000],[Exposure(0,1000,1),Exposure(2000,3000,1)])
    def test_future_l2(self):
        with self.assertRaisesRegex(Abstain,"NONCAUSAL"):
            run([0,1000],[Exposure(0,1000,1,causal=False)])
    def test_zero_hazard(self):
        with self.assertRaisesRegex(Abstain,"ZERO_OR_INVALID"):
            run([0,1000],[Exposure(0,1000,0)])
    def test_single_cluster(self):
        with self.assertRaisesRegex(Abstain,"INSUFFICIENT_UNIQUE"):
            run([0,0,0],[Exposure(0,1000,1)])
    def test_overlap(self):
        with self.assertRaisesRegex(Abstain,"OVERLAPPING"):
            run([0,1000],[Exposure(0,800,1),Exposure(500,1000,1)])
    def test_unsorted(self):
        with self.assertRaisesRegex(Abstain,"UNSORTED"):
            run([1000,0],[Exposure(0,1000,1)])
    def test_periodic_non_target(self):
        self.assertEqual(run([0,20000,40000,60000],[Exposure(0,60000,1)]),(20.,20.,20.))
    def test_invalid_rate(self):
        with self.assertRaisesRegex(Abstain,"INVALID_OR_NONCAUSAL"):
            run([0,1000],[Exposure(0,1000,float("nan"))])
    def test_public_owner_nonidentifiability(self):
        tape=[0,1000,2000]
        e=[Exposure(0,2000,1)]
        self.assertEqual(run(tape,e),run(tape,e))

if __name__=="__main__": unittest.main()
