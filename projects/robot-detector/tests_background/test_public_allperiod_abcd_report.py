"""Guard full all-period A/B/C/D comparison and non-target interpretation."""
import unittest
from public_allperiod_abcd_report import report


class AllPeriodABCDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.r=report()

    def test_all_scenarios_periods_methods_and_64_replicates_without_best_only(self):
        self.assertEqual(set(self.r['scenarios']),
                         {'poisson_like_quantized','momentum_like_bursts','unrelated_periodic_20s'})
        self.assertEqual(self.r['periods_ms'],[5000,10000,15000,20000,30000,45000,60000])
        for row in self.r['scenarios'].values():
            self.assertEqual(len(row['candidates']),4)
            self.assertEqual(set(row['observed']),set(map(str,self.r['periods_ms'])))
            for model in row['candidates'].values():
                self.assertEqual(set(model),set(map(str,self.r['periods_ms'])))
                for stats in model.values():
                    self.assertEqual(len(stats['all_replicate_hits']),64)
                    self.assertEqual(stats['min_hits'],min(stats['all_replicate_hits']))
                    self.assertEqual(stats['max_hits'],max(stats['all_replicate_hits']))

    def test_non_target_periodic_and_momentum_are_not_owner_truth(self):
        periodic=self.r['scenarios']['unrelated_periodic_20s']['observed']
        self.assertTrue(all(periodic[str(p)]['hits']==5 for p in (5000,10000,20000)))
        self.assertTrue(all(periodic[str(p)]['hits']==0 for p in (15000,30000,45000,60000)))
        self.assertEqual(self.r['scenarios']['momentum_like_bursts']['observed']['5000']['hits'],23)
        for key in ('calibrated_p_values','physical_owner_id_known','real_market_fdr_known'):
            self.assertFalse(self.r[key])

    def test_D_gaps_and_determinism_not_fake_new_source(self):
        x=self.r['scenarios']['unrelated_periodic_20s']['candidates']['D_microburst_blocks_10ms']['20000']
        self.assertEqual(len(x['all_replicate_hits']),64)
        self.assertEqual(self.r['fresh_market_or_ABIDES_sources'],0)
        self.assertEqual(report(),self.r)


if __name__=='__main__':unittest.main()
