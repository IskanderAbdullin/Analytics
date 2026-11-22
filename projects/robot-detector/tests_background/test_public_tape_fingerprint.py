import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from public_tape_fingerprint import fingerprint_public_tape
from l2_trade_context import PublicExecution
from abides_l2_binphase_sensitivity import shift_public_clock

NS=1_000_000_000

def fixture():
    book=SimpleNamespace(
        times_ns=[25*NS,30*NS,30*NS,65*NS],
        bids=[[(100,3)],[(100,5)],[(101,6),(100,2)],[(100,4)]],
        asks=[[(102,3)],[(102,2)],[(103,2)],[(102,5)]])
    prints=(PublicExecution(31*NS,102,7,"BUY"),
            PublicExecution(31*NS,102,1,"BUY"),
            PublicExecution(66*NS,100,8,"SELL"))
    return book,prints

class FingerprintTests(unittest.TestCase):
    def test_phase_normalization_is_identical(self):
        book,prints=fixture()
        h=fingerprint_public_tape(book,prints)
        self.assertFalse(h["source_authenticity_verified"])
        for phase in (0,10,20):
            shifted,tape=shift_public_clock(book,prints,phase)
            self.assertEqual(
                fingerprint_public_tape(shifted,tape,restore_clock_ns=phase*NS),h)

    def test_tamper_book_payload_order_or_time_is_detected(self):
        book,prints=fixture()
        original=fingerprint_public_tape(book,prints)["public_tape_sha256"]
        for alternate in (
            SimpleNamespace(times_ns=book.times_ns,bids=[
                [(100,3)],[(100,5)],[(101,7),(100,2)],[(100,4)]],asks=book.asks),
            SimpleNamespace(times_ns=book.times_ns,bids=[
                book.bids[0],book.bids[2],book.bids[1],book.bids[3]],
                asks=[book.asks[0],book.asks[2],book.asks[1],book.asks[3]]),
            SimpleNamespace(times_ns=[25*NS,30*NS,30*NS,66*NS],
                            bids=book.bids,asks=book.asks),
        ):
            self.assertNotEqual(
                fingerprint_public_tape(alternate,prints)["public_tape_sha256"],
                original)

    def test_trades_tamper_is_detected(self):
        book,prints=fixture()
        original=fingerprint_public_tape(book,prints)["public_tape_sha256"]
        for trades in ((prints[1],prints[0],prints[2]),
                       (prints[0],replace(prints[1],quantity=2),prints[2]),
                       (prints[0],replace(prints[1],reported_aggressor_side="SELL"),
                        prints[2])):
            self.assertNotEqual(fingerprint_public_tape(book,trades)[
                "public_tape_sha256"],original)

    def test_book_changes_do_not_change_print_only_hash(self):
        book,prints=fixture()
        original=fingerprint_public_tape(book,prints)
        book.bids[0][0]=(100,99)
        modified=fingerprint_public_tape(book,prints)
        self.assertEqual(original["prints_sha256"],modified["prints_sha256"])
        self.assertNotEqual(original["l2_sha256"],modified["l2_sha256"])
        self.assertNotEqual(original["public_tape_sha256"],
                            modified["public_tape_sha256"])

    def test_rejects_noninteger_source_and_nonpublic_sides(self):
        book,prints=fixture()
        for wrong in (
            SimpleNamespace(times_ns=[25.0*NS]+book.times_ns[1:],
                            bids=book.bids,asks=book.asks),
            SimpleNamespace(times_ns=book.times_ns,bids=[
                [(100,True)]]+book.bids[1:],asks=book.asks),
        ):
            with self.assertRaises(ValueError):
                fingerprint_public_tape(wrong,prints)
        for invalid in (replace(prints[0],quantity=1.5),
                        replace(prints[0],reported_aggressor_side="UNKNOWN")):
            with self.assertRaises(ValueError):
                fingerprint_public_tape(book,(invalid,))
        for restore in (-1,True,1.0):
            with self.assertRaises(ValueError):
                fingerprint_public_tape(book,prints,restore_clock_ns=restore)

if __name__=="__main__":
    unittest.main(verbosity=2)
