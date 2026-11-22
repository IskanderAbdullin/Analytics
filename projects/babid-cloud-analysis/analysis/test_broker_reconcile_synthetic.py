"""All fixtures fictional. No connected broker, trade, or real identifier."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from broker_reconcile_synthetic import TradeFact, reconcile_facts


def fact(**overrides):
    data = dict(account="fictional", instrument="FAKE", side="Sell", lots=2,
                price=Decimal("99.50"), executed_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
                trade_id_namespace="orders", trade_id="synthetic-trade")
    data.update(overrides)
    return TradeFact(**data)


class BrokerReconcileTests(unittest.TestCase):
    def test_exact_trade_id_same_namespace_is_confirmed(self):
        r = reconcile_facts([fact()], [fact()])
        self.assertEqual(r[0].status, "confirmed_id")
        self.assertEqual(r[0].broker_index, 0)

    def test_cross_namespace_never_confirmed(self):
        r = reconcile_facts([fact()], [fact(trade_id_namespace="operations", trade_id="other")])
        self.assertEqual(r[0].status, "candidate")

    def test_missing_trade_id_is_only_candidate(self):
        r = reconcile_facts([fact(trade_id="")], [fact(trade_id="")])
        self.assertEqual(r[0].status, "candidate")

    def test_duplicate_broker_matches_are_ambiguous(self):
        r = reconcile_facts([fact()], [fact(), fact()])
        self.assertEqual(r[0].status, "ambiguous")
        self.assertIsNone(r[0].broker_index)

    def test_two_local_records_compete_for_broker(self):
        r = reconcile_facts([fact(), fact()], [fact()])
        self.assertTrue(all(x.status == "ambiguous" for x in r))

    def test_same_namespace_different_id_is_not_a_match(self):
        r = reconcile_facts([fact()], [fact(trade_id="different")])
        self.assertEqual(r[0].status, "unmatched")

    def test_different_identity_direction_lots_price_rejected(self):
        for patch in (dict(account="another"), dict(instrument="OTHER"),
                      dict(side="Buy"), dict(lots=3), dict(price=Decimal("99.51"))):
            with self.subTest(patch=patch):
                self.assertEqual(reconcile_facts([fact()], [fact(**patch)])[0].status, "unmatched")

    def test_time_tolerance_explicit(self):
        later = fact(executed_utc=datetime(2026, 1, 1, tzinfo=timezone.utc)
                     + timedelta(milliseconds=1500))
        self.assertEqual(reconcile_facts([fact()], [later])[0].status, "unmatched")
        self.assertEqual(reconcile_facts([fact()], [later], tolerance_ms=1500)[0].status, "confirmed_id")

    def test_no_broker_rows_is_not_evidence(self):
        self.assertEqual(reconcile_facts([fact()], [])[0].status, "unmatched")

    def test_naive_or_non_utc_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            fact(executed_utc=datetime(2026, 1, 1))
        with self.assertRaises(ValueError):
            fact(executed_utc=datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=3))))

    def test_invalid_amount_and_tolerance(self):
        with self.assertRaises(ValueError):
            fact(lots=0)
        with self.assertRaises(ValueError):
            reconcile_facts([fact()], [fact()], tolerance_ms=-1)

    def test_reused_local_object_rejected(self):
        one = fact()
        with self.assertRaises(ValueError):
            reconcile_facts([one, one], [fact()])


if __name__ == "__main__":
    unittest.main()
