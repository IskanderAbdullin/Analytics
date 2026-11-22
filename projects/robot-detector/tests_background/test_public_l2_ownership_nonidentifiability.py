#!/usr/bin/env python3
"""Source-free oracle truth tests: owner IDs must never leak to public L2."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from public_l2_ownership_nonidentifiability import (
    OracleWorld, PUBLIC_EVENT_KEYS, make_public_demo_case,
    make_oracle_world, validate_public_events, public_projection,
    source_visible_fingerprint, public_only_descriptor,
    private_oracle_owner_count, demonstrate_owner_nonidentifiability,
)


class PublicL2OwnerIdentifiabilityCounterexample(unittest.TestCase):
    def test_same_exact_market_view_can_have_one_or_three_private_owners(self):
        data=make_public_demo_case()
        a=make_oracle_world(data,{10:"A",11:"A",12:"A"})
        b=make_oracle_world(data,{10:"A",11:"B",12:"C"})
        self.assertEqual(private_oracle_owner_count(a),1)
        self.assertEqual(private_oracle_owner_count(b),3)
        pa,pb=public_projection(a),public_projection(b)
        self.assertEqual(pa,pb)
        self.assertEqual(source_visible_fingerprint(pa),
                         source_visible_fingerprint(pb))
        self.assertEqual(public_only_descriptor(pa),public_only_descriptor(pb))
        self.assertEqual(public_only_descriptor(pa)[
            "distinct_exchange_order_references"],3)
        self.assertFalse(public_only_descriptor(pa)[
            "physical_owner_count_identifiable"])
        for public_deterministic_guess in range(0,8):
            self.assertFalse(public_deterministic_guess in (
                {private_oracle_owner_count(a)} &
                {private_oracle_owner_count(b)}
            ))
        self.assertEqual([item["event_type"] for item in data],
                         [1,1,4,1,4,3])
        self.assertEqual(data[0]["public_order_reference"],
                         data[2]["public_order_reference"])
        self.assertEqual(data[1]["exchange_local_microseconds"],
                         data[2]["exchange_local_microseconds"])

    def test_source_visible_contract_has_no_actor_and_cannot_accept_oracle_key(self):
        public=make_public_demo_case()
        self.assertEqual(set(public[0]),PUBLIC_EVENT_KEYS)
        for bad_field in ("owner","agent_id","physical_bot_identity",
                          "ground_truth","parent_owner_id","private_oracle"):
            injected=deepcopy(public[0])
            injected[bad_field]="PRIVATE"
            with self.subTest(field=bad_field),self.assertRaises(ValueError):
                validate_public_events((injected,)+public[1:])
        injected=deepcopy(public[0])
        del injected["public_order_reference"]
        with self.assertRaises(ValueError):
            validate_public_events((injected,)+public[1:])

    def test_altering_market_visible_order_reference_changes_public_fingerprint(self):
        public=make_public_demo_case()
        altered=[dict(e) for e in public]
        altered[0]["public_order_reference"]=9999
        base=source_visible_fingerprint(public)
        new=source_visible_fingerprint(tuple(altered))
        self.assertNotEqual(base,new)
        self.assertEqual(base,source_visible_fingerprint(public))

    def test_strict_ordered_timestamp_and_ten_level_ladder_validation(self):
        original=make_public_demo_case()
        for key,value in (
            ("exchange_local_microseconds",False),
            ("event_type",8),
            ("size_shares",0),
            ("limit_price_x10000",-1),
            ("resting_limit_side",2),
            ("public_order_reference",0),
            ("post_event_book_10levels",tuple([1]*40)),
            ("post_event_book_10levels",tuple([1]*39)),
            ("post_event_book_10levels","N/A"),
        ):
            altered=[dict(x) for x in original]
            altered[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_public_events(tuple(altered))
        altered=[dict(x) for x in original]
        altered[3]["exchange_local_microseconds"]=original[0][
            "exchange_local_microseconds"]-1
        with self.assertRaises(ValueError):
            validate_public_events(tuple(altered))

    def test_world_must_assign_exactly_each_public_order_reference(self):
        original=make_public_demo_case()
        for mapping in (
            {},{10:"A",11:"B"},{10:"A",11:"B",12:"C",999:"D"},
            {10:"A",11:None,12:"C"},{10:"A",11:"",12:"C"},
            {10:"A",11:"B",True:"C"}
        ):
            with self.subTest(mapping=str(mapping)),self.assertRaises(ValueError):
                make_oracle_world(original,mapping)
        with self.assertRaises(ValueError):
            public_projection("not an oracle world")
        with self.assertRaises(ValueError):
            private_oracle_owner_count("not an oracle world")

    def test_oracle_copy_prevents_later_mutation_of_input_mapping(self):
        d=make_public_demo_case()
        ownership={10:"A",11:"B",12:"C"}
        w=make_oracle_world(d,ownership)
        ownership[12]="A"
        self.assertEqual(private_oracle_owner_count(w),3)

    def test_constructive_result_contains_only_aggregates_and_limits(self):
        result=demonstrate_owner_nonidentifiability()
        self.assertEqual(result["schema_version"],
                         "synthetic-public-l2-owner-nonidentifiability-v1")
        self.assertEqual(result["synthetic_public_messages"],6)
        self.assertEqual(result["synthetic_unique_order_references"],3)
        self.assertEqual(result["synthetic_private_owner_count_world_a"],1)
        self.assertEqual(result["synthetic_private_owner_count_world_b"],3)
        self.assertTrue(result["identical_full_10level_post_event_public_tapes"])
        self.assertTrue(result["identical_public_only_estimator_result"])
        self.assertTrue(result["public_order_reference_is_not_an_owner_identifier"])
        self.assertTrue(result[
            "not_a_claim_that_observable_algorithmic_patterns_cannot_be_detected"])
        for unsupported in (
            "true_owner_count_recoverable_in_both_worlds_from_public_view",
            "synthetic_private_owner_labels_exported",
            "real_market_actor_identification_or_FDR_calibrated",
            "real_vendor_event_rows_used","actual_live_trading_enabled",
        ):
            self.assertFalse(result[unsupported],unsupported)
        self.assertEqual(len(result["identical_public_sha256"]),64)
        self.assertNotIn("private_owner_of_order_reference",result)
        self.assertNotIn("agent_id",result)

if __name__=="__main__":
    unittest.main(verbosity=2)
