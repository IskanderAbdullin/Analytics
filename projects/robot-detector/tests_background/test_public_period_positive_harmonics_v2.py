"""Frozen v1 zero-harmonic alias falsification and independent v2 contract."""
import unittest
from tools.public_period_scan import scan_public_timestamps
from tools.public_period_positive_harmonics_v2 import (
    scan_positive_harmonics_v2 as scan, positive_harmonic_hit,
)


class PositiveHarmonicV2Tests(unittest.TestCase):
    def test_short_gaps_v1_false_perfection_v2_all_zero(self):
        tape = [1000,1001,1002,1003]
        v1 = scan_public_timestamps(tape)
        v2 = scan(tape)
        self.assertEqual(len(v2['periods']),7)
        self.assertTrue(all(r['hits']==3 and r['denominator']==3 for r in v1['periods']))
        self.assertTrue(all(r['hits']==0 and r['denominator']==3 for r in v2['periods']))
        self.assertIn('zero-harmonic',v2['legacy_v1_warning'])

    def test_unrelated_20s_periodic_actor_preserves_positive_harmonic_alias(self):
        periods = {row['period_ms']:row for row in scan([1000+20000*k for k in range(6)])['periods']}
        for period in (5000,10000,20000):
            self.assertEqual(periods[period]['hits'],5)
        for period in (15000,30000,45000,60000):
            self.assertEqual(periods[period]['hits'],0)

    def test_45s_constructed_cadence_not_owner_truth(self):
        result = scan([0,45000,90000])
        self.assertEqual({r['period_ms'] for r in result['periods'] if r['hits']==2},
                         {5000,15000,45000})
        self.assertIn('NO_OWNER_ID',result['inference'])

    def test_tolerance_boundary_strict_and_positive_harmonic_only(self):
        self.assertTrue(positive_harmonic_hit(4950,5000))
        self.assertTrue(positive_harmonic_hit(5050,5000))
        self.assertFalse(positive_harmonic_hit(4949,5000))
        self.assertFalse(positive_harmonic_hit(5051,5000))
        self.assertFalse(positive_harmonic_hit(49,5000))
        self.assertTrue(positive_harmonic_hit(10000,5000))
        self.assertEqual(scan([0,4950,10000])['periods'][0]['hits'],2)
        self.assertEqual(scan([0,4949,10000])['periods'][0]['hits'],0)

    def test_split_fills_invariant_and_invalid_inputs_fail(self):
        a = scan([1000,6000,11000])
        b = scan([1000]*100+[6000,11000])
        self.assertEqual(a['periods'],b['periods'])
        for tape in ([2,1],[-1],[True],[1.5],['1']):
            with self.subTest(tape=tape), self.assertRaises(ValueError):
                scan(tape)
        self.assertEqual(scan([1000,1000])['status'],'ABSTAIN_NO_GAPS')
        self.assertTrue(all(r['fraction'] is None for r in scan([1000])['periods']))


if __name__=='__main__':
    unittest.main()
