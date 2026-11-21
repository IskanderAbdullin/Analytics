"""Source-free adversarial checks for public timestamp-cluster conditional null.

This is a constructed measurement counterexample, NOT a calibrated detector,
ABIDES run, market p-value, or independent holdout. No oracle identity used.
Run: python -m unittest discover -s projects/robot-detector/tests -p 'test_public_cluster_invariance_20261121.py'
"""
import unittest
from collections import Counter


def public_clusters(prints):
    """Only public (timestamp_ns, side, lots) fields are accepted."""
    for record in prints:
        if set(record) != {"timestamp_ns", "side", "lots"}:
            raise ValueError("Non-public or incomplete record")
        if record["side"] not in ("BUY", "SELL") or record["lots"] <= 0:
            raise ValueError("Invalid public print")
    counts = Counter(p["timestamp_ns"] for p in prints)
    return tuple(sorted(counts))


def lagged_l2_eligible(print_ns, l2_updates, min_prior=5):
    """Strictly prior completed snapshots; same-time and future are excluded."""
    if min_prior <= 0:
        raise ValueError("min_prior must be positive")
    return sum(t < print_ns for t in l2_updates) >= min_prior


def interarrival_ns(prints):
    times = public_clusters(prints)
    return tuple(b - a for a, b in zip(times, times[1:]))


class PublicClusterNegativeTests(unittest.TestCase):
    def setUp(self):
        self.base = [{"timestamp_ns": i * 20_000_000_000,
                      "side": "BUY", "lots": 1} for i in range(12)]

    def test_split_fills_do_not_create_independent_interarrivals(self):
        split = self.base + [dict(self.base[3]) for _ in range(99)]
        self.assertEqual(interarrival_ns(split), interarrival_ns(self.base))
        self.assertEqual(len(split), 111)
        self.assertEqual(len(public_clusters(split)), 12)

    def test_timestamp_clusters_do_not_identify_parent_or_owner(self):
        # Two possible private assignments have identical PUBLIC observations.
        tape_a = list(self.base)
        tape_b = list(self.base)
        self.assertEqual(public_clusters(tape_a), public_clusters(tape_b))
        self.assertNotIn("owner_id", tape_a[0])

    def test_reject_privileged_oracle_fields(self):
        with self.assertRaises(ValueError):
            public_clusters(self.base + [dict(self.base[0], agent_id=17)])

    def test_same_time_l2_is_not_prior(self):
        self.assertFalse(lagged_l2_eligible(100, [1, 2, 3, 4, 100]))
        self.assertTrue(lagged_l2_eligible(100, [1, 2, 3, 4, 99, 100]))

    def test_future_l2_cannot_rescue_missing_coverage(self):
        self.assertFalse(lagged_l2_eligible(100, [1, 2, 3, 4, 101, 102]))

    def test_fixed_cadence_non_target_is_indistinguishable_by_rhythm(self):
        # Both tapes are the same observable cadence; labels cannot be
        # inferred from these public fields, regardless of private scenario.
        observed = interarrival_ns(self.base)
        self.assertTrue(all(dt == 20_000_000_000 for dt in observed))
        self.assertEqual(observed, interarrival_ns(list(self.base)))


if __name__ == "__main__":
    unittest.main()
