"""Fake source-free manifest fixtures; no seeds reserved or source tapes read."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.public_intensity_rescaling import Abstain
from tools.public_run_allocation_gate import (SCENARIOS, SPLITS,
    audit_prospective_allocation, load_local_spent_seeds)


def fixture():
    data = {}
    for split, seed in zip(SPLITS, (81001, 82001, 83001)):
        data[split] = []
        for cohort in sorted(SCENARIOS):
            tag = f'fake.{split}.{seed}.{cohort}'
            data[split].append({'source_run_id': tag, 'seed': seed, 'scenario': cohort,
                                'tape_fingerprint': hashlib.sha256(tag.encode()).hexdigest()})
    return data


class ProspectiveSourceRunAllocationIntegrityTests(unittest.TestCase):
    def test_complete_fixture_structure_only_never_claims_new_holdout(self):
        a = audit_prospective_allocation(fixture())
        self.assertEqual(a['source_label_count'], 12)
        self.assertEqual(a['splits']['train']['unique_source_seeds'], 1)
        self.assertFalse(a['globally_unseen_seeds_verified'])
        self.assertFalse(a['real_market_fdr_known'])

    def test_same_seed_in_different_split_even_with_distinct_cohort_rejected(self):
        x = fixture(); x['evaluation'][0]['seed'] = 81001
        with self.assertRaisesRegex(Abstain, 'SEED_LEAK'):
            audit_prospective_allocation(x)

    def test_one_original_run_three_phase_aliases_rejected(self):
        x = fixture()
        alias = dict(x['train'][0], phase='10s')
        x['train'].append(alias)
        with self.assertRaisesRegex(Abstain, 'FORBIDDEN'):
            audit_prospective_allocation(x)

    def test_duplicate_source_id_and_tape_fingerprint_rejected(self):
        for key in ('source_run_id', 'tape_fingerprint'):
            x=fixture()
            x['evaluation'][0][key] = x['train'][0][key]
            with self.subTest(key=key), self.assertRaisesRegex(Abstain, 'REPLAY'):
                audit_prospective_allocation(x)

    def test_missing_and_duplicate_negative_cohort_rejected(self):
        x=fixture(); x['train'].pop()
        with self.assertRaisesRegex(Abstain, 'MISSING_MANDATORY'):
            audit_prospective_allocation(x)
        x=fixture(); x['train'][1]['scenario'] = x['train'][0]['scenario']
        with self.assertRaisesRegex(Abstain, 'DUPLICATED'):
            audit_prospective_allocation(x)

    def test_ledger_spent_3301_and_early_seeds_rejected(self):
        spent=load_local_spent_seeds()
        self.assertTrue({3301,3340,41,901,2701,3204}.issubset(spent))
        for seed in (3301, 3340, 41):
            x=fixture()
            for row in x['train']:
                row['seed']=seed
            with self.subTest(seed=seed), self.assertRaisesRegex(Abstain, 'PREVIOUSLY_SPENT'):
                audit_prospective_allocation(x)

    def test_private_oracle_fields_and_unknown_scenario_fail(self):
        x=fixture(); x['train'][0]['agent_id']=5
        with self.assertRaisesRegex(Abstain, 'FORBIDDEN'):
            audit_prospective_allocation(x)
        x=fixture(); x['train'][0]['scenario']='private_truth'
        with self.assertRaisesRegex(Abstain, 'INVALID_HARD_NEGATIVE'):
            audit_prospective_allocation(x)

    def test_bool_seed_invalid_digest_and_bad_split_key_fail(self):
        x=fixture(); x['train'][0]['seed']=True
        with self.assertRaisesRegex(Abstain, 'INVALID_SEED'):
            audit_prospective_allocation(x)
        x=fixture(); x['train'][0]['tape_fingerprint']='NOT_SHA256'
        with self.assertRaisesRegex(Abstain, 'INVALID_PUBLIC_TAPE'):
            audit_prospective_allocation(x)
        x=fixture(); x['holdout']=x.pop('evaluation')
        with self.assertRaisesRegex(Abstain, 'INVALID_SPLIT'):
            audit_prospective_allocation(x)

    def test_empty_calibration_not_silent_holdout(self):
        x=fixture(); x['calibration']=[]
        with self.assertRaisesRegex(Abstain, 'EMPTY_OR_INVALID'):
            audit_prospective_allocation(x)

    def test_missing_and_malformed_registry_fail_closed(self):
        x=fixture()
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'ledger.json'
            with self.assertRaisesRegex(Abstain, 'MISSING_OR_MALFORMED'):
                audit_prospective_allocation(x, registry_path=p)
            for invalid in ('{broken', '{"studies": []}', '{"studies":[{"seeds":[true]}]}'):
                p.write_text(invalid, encoding='utf-8')
                with self.subTest(invalid=invalid), self.assertRaisesRegex(Abstain,'MISSING_OR_MALFORMED'):
                    audit_prospective_allocation(x, registry_path=p)


if __name__ == '__main__': unittest.main()
