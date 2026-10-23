import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_public_stage335_aggregate import audit_report

class Stage335PublicAggregateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads((ROOT / "docs" / "stage335_public_aggregate.json").read_text(encoding="utf-8"))

    def test_public_aggregate_passes(self):
        result = audit_report(copy.deepcopy(self.baseline))
        self.assertEqual(result["direct_load_store_pairs"], 506)
        self.assertEqual(result["second_write_live_ram_matches"], 253)
        self.assertFalse(result["raw_trace_committed"])

    def test_rejects_private_source_hash(self):
        report = copy.deepcopy(self.baseline)
        report["rom_sha256"] = "must-not-be-published"
        with self.assertRaises(ValueError):
            audit_report(report)

    def test_rejects_unmatched_ppu_write(self):
        report = copy.deepcopy(self.baseline)
        report["ppu_2005"]["unmatched_writes"] = 1
        with self.assertRaises(ValueError):
            audit_report(report)

    def test_rejects_dataflow_mismatch(self):
        report = copy.deepcopy(self.baseline)
        report["dataflow"]["ram_0d_load_to_second_2005_store"]["matches"] = 252
        with self.assertRaises(ValueError):
            audit_report(report)

    def test_rejects_wrong_latch_phase(self):
        report = copy.deepcopy(self.baseline)
        report["ppu_latch"]["second_write_toggle_before"] = 0
        with self.assertRaises(ValueError):
            audit_report(report)

    def test_rejects_semantic_overclaim(self):
        report = copy.deepcopy(self.baseline)
        report["interpretation"]["effective_raster_scroll_proven"] = True
        with self.assertRaises(ValueError):
            audit_report(report)

    def test_rejects_raw_source_values(self):
        report = copy.deepcopy(self.baseline)
        report["source_values"] = {"pc": "private"}
        with self.assertRaises(ValueError):
            audit_report(report)

if __name__ == "__main__":
    unittest.main()
