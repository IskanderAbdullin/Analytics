"""Source-free prospective original-market-run split integrity gate, no allocations.

Frozen design: docs/CONDITIONAL_SOURCE_RUN_ALLOCATION_INTEGRITY_PREREG_20261122.md
Cannot certify globally novel seeds or source independence from labels/digests alone.
"""
import json
import re
from pathlib import Path

from tools.public_intensity_rescaling import Abstain

SCENARIOS = frozenset({
    'poisson_noise_null', 'fixed_20s_noise_hard_negative',
    'momentum_noise_hard_negative', 'twap_45s_positive',
})
SPLITS = ('train', 'calibration', 'evaluation')
RECORD_FIELDS = frozenset({'source_run_id', 'seed', 'scenario', 'tape_fingerprint'})
LEDGER_PATH = Path(__file__).resolve().parents[1] / 'research' / 'seed_registry.json'


def load_local_spent_seeds(path=None):
    """Fail closed if registry absent/malformed; local history is NOT global novelty proof."""
    try:
        ledger = json.loads(Path(path or LEDGER_PATH).read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise Abstain('MISSING_OR_MALFORMED_SEED_REGISTRY') from exc
    if type(ledger) is not dict or type(ledger.get('studies')) is not list or not ledger['studies']:
        raise Abstain('MISSING_OR_MALFORMED_SEED_REGISTRY')
    if type(ledger.get('replays', [])) is not list:
        raise Abstain('MISSING_OR_MALFORMED_SEED_REGISTRY')
    spent = set()
    for item in ledger['studies'] + ledger.get('replays', []):
        if type(item) is not dict or type(item.get('seeds')) is not list or not item['seeds']:
            raise Abstain('MISSING_OR_MALFORMED_SEED_REGISTRY')
        for seed in item['seeds']:
            if type(seed) is not int or seed <= 0:
                raise Abstain('MISSING_OR_MALFORMED_SEED_REGISTRY')
            spent.add(seed)
    return frozenset(spent)


def audit_prospective_allocation(allocation, *, registry_path=None):
    """No test/holdout data consumed; returns structural metadata only."""
    if type(allocation) is not dict or set(allocation) != set(SPLITS):
        raise Abstain('INVALID_SPLIT_MANIFEST')
    spent = load_local_spent_seeds(registry_path)
    seed_split = {}
    seen_source_ids = set()
    seen_fingerprints = set()
    summary = {}
    for split in SPLITS:
        records = allocation[split]
        if type(records) not in (list, tuple) or not records:
            raise Abstain('EMPTY_OR_INVALID_SPLIT')
        cohorts = {}
        for record in records:
            if type(record) is not dict or set(record) != RECORD_FIELDS:
                raise Abstain('FORBIDDEN_OR_MISSING_PUBLIC_ALLOCATION_FIELD')
            rid, seed = record['source_run_id'], record['seed']
            cohort, fp = record['scenario'], record['tape_fingerprint']
            if type(rid) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', rid):
                raise Abstain('INVALID_OR_SENSITIVE_SOURCE_RUN_LABEL')
            if type(seed) is not int or seed <= 0:
                raise Abstain('INVALID_SEED')
            if type(cohort) is not str or cohort not in SCENARIOS:
                raise Abstain('INVALID_HARD_NEGATIVE_COHORT')
            if type(fp) is not str or re.fullmatch(r'[0-9a-f]{64}', fp) is None:
                raise Abstain('INVALID_PUBLIC_TAPE_FINGERPRINT')
            if seed in spent:
                raise Abstain('PREVIOUSLY_SPENT_LOCAL_SEED')
            if seed in seed_split and seed_split[seed] != split:
                raise Abstain('SEED_LEAK_ACROSS_PARTITIONS')
            seed_split[seed] = split
            if rid in seen_source_ids or fp in seen_fingerprints:
                raise Abstain('SOURCE_REPLAY_OR_DEPENDENT_PHASE_ALIAS')
            seen_source_ids.add(rid)
            seen_fingerprints.add(fp)
            units = cohorts.setdefault(seed, set())
            if cohort in units:
                raise Abstain('DUPLICATED_SOURCE_COHORT')
            units.add(cohort)
        if any(units != SCENARIOS for units in cohorts.values()):
            raise Abstain('MISSING_MANDATORY_HARD_NEGATIVE_COHORT')
        summary[split] = {'unique_source_seeds': len(cohorts), 'original_source_runs': len(records)}
    return {'status': 'STRUCTURAL_ONLY_NOT_GENUINE_INDEPENDENCE_OR_HOLDOUT',
            'splits': summary, 'source_label_count': len(seen_source_ids),
            'globally_unseen_seeds_verified': False, 'real_market_fdr_known': False}
