"""Source-free falsifications, no market p-values or actor labels."""
import unittest
from tools.public_intensity_rescaling import Abstain, Exposure, rescaled_cluster_gaps as run, validate_public_inputs

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
    def test_nonnumeric_hazard_abstains(self):
        for bad in ("1.0", None, True, [], {}):
            with self.subTest(rate=repr(bad)):
                with self.assertRaisesRegex(Abstain, "INVALID_OR_NONCAUSAL"):
                    run([0,1000],[Exposure(0,1000,bad)])
    def test_negative_hazard_abstains(self):
        with self.assertRaisesRegex(Abstain, "INVALID_OR_NONCAUSAL"):
            run([0,1000],[Exposure(0,1000,-1)])
    def test_public_owner_nonidentifiability(self):
        tape=[0,1000,2000]
        e=[Exposure(0,2000,1)]
        self.assertEqual(run(tape,e),run(tape,e))


class TestPublicInputGate(unittest.TestCase):
    def setUp(self):
        self.prints=[{"timestamp_ms":100},{"timestamp_ms":200}]
        self.books=[{"timestamp_ms":50,"complete":True}]
    def test_valid_previous_only(self):
        self.assertEqual(validate_public_inputs(self.prints,self.books,timestamp_resolution_ms=1),(100,200))
    def test_private_agent_id_rejected(self):
        with self.assertRaisesRegex(Abstain,"FORBIDDEN"):
            validate_public_inputs([dict(self.prints[0],agent_id=7),self.prints[1]],self.books,timestamp_resolution_ms=1)
    def test_same_time_l2_not_prior(self):
        with self.assertRaisesRegex(Abstain,"NO_COMPLETE"):
            validate_public_inputs(self.prints,[{"timestamp_ms":100,"complete":True}],timestamp_resolution_ms=1)
    def test_future_l2_not_prior(self):
        with self.assertRaisesRegex(Abstain,"NO_COMPLETE"):
            validate_public_inputs(self.prints,[{"timestamp_ms":300,"complete":True}],timestamp_resolution_ms=1)
    def test_coarse_precision_rejected(self):
        with self.assertRaisesRegex(Abstain,"COARSE"):
            validate_public_inputs(self.prints,self.books,timestamp_resolution_ms=10)
    def test_incomplete_previous_l2_rejected(self):
        with self.assertRaisesRegex(Abstain,"NO_COMPLETE"):
            validate_public_inputs(self.prints,[{"timestamp_ms":50,"complete":False}],timestamp_resolution_ms=1)
    def test_unsorted_l2_rejected(self):
        with self.assertRaisesRegex(Abstain,"UNSORTED"):
            validate_public_inputs(self.prints,[{"timestamp_ms":90,"complete":True},{"timestamp_ms":50,"complete":True}],timestamp_resolution_ms=1)
    def test_nonboolean_coverage_rejected(self):
        with self.assertRaisesRegex(Abstain,"COMPLETENESS"):
            validate_public_inputs(self.prints,[{"timestamp_ms":50,"complete":1}],timestamp_resolution_ms=1)
    def test_no_unique_cluster_rejected(self):
        with self.assertRaisesRegex(Abstain,"INSUFFICIENT_UNIQUE"):
            validate_public_inputs([self.prints[0],self.prints[0]],self.books,timestamp_resolution_ms=1)

if __name__=="__main__": unittest.main()

