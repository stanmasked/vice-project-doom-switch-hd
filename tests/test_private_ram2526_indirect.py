import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_private_ram2526_indirect import analyze, extract_sites, verify_stage325_baseline

FIELDS = ["frame", "cycle", "event", "pc", "opcode", "operand", "address", "value",
          "old_value", "pointer_low", "pointer_high", "y", "effective_address", "bank_context"]


class PrivateRam2526IndirectTests(unittest.TestCase):
    def write_trace(self, root, rows):
        path = root / "trace.tsv"
        with path.open("w", encoding="ascii", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def base_rows(self):
        return [
            {"frame": 600, "cycle": 80, "event": "write", "pc": "E100", "opcode": "85", "operand": "25", "address": "0025", "value": "10", "old_value": "00", "bank_context": "R6:03"},
            {"frame": 600, "cycle": 84, "event": "write", "pc": "E102", "opcode": "85", "operand": "26", "address": "0026", "value": "80", "old_value": "00", "bank_context": "R6:03"},
            {"frame": 600, "cycle": 100, "event": "indirect", "pc": "8123", "opcode": "B1", "operand": "25", "pointer_low": "10", "pointer_high": "80", "y": "02", "effective_address": "8012", "bank_context": "R6:03"},
            {"frame": 600, "cycle": 105, "event": "write", "pc": "E110", "opcode": "85", "operand": "25", "address": "0025", "value": "20", "old_value": "10", "bank_context": "R7:02"},
            {"frame": 600, "cycle": 120, "event": "indirect", "pc": "8123", "opcode": "B1", "operand": "25", "pointer_low": "20", "pointer_high": "80", "y": "02", "effective_address": "8022", "bank_context": "R6:03"},
            {"frame": 600, "cycle": 130, "event": "indirect", "pc": "9000", "opcode": "71", "operand": "25", "pointer_low": "20", "pointer_high": "80", "y": "02", "effective_address": "8022", "bank_context": "R7:02"},
            {"frame": 600, "cycle": 135, "event": "indirect", "pc": "9010", "opcode": "B1", "operand": "AA", "pointer_low": "40", "pointer_high": "90", "y": "01", "effective_address": "9041", "bank_context": "R7:02"},
            {"frame": 600, "cycle": 140, "event": "write", "pc": "E120", "opcode": "85", "operand": "0D", "address": "000D", "value": "01", "old_value": "00", "bank_context": "R7:02"},
        ]

    def test_aggregates_site_bank_and_pointer_updates_without_raw_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = analyze(self.write_trace(root, self.base_rows()))
        self.assertEqual(result["pointer_write_counts"], {"$25": 2, "$26": 1})
        self.assertEqual(result["indirect_access_counts"]["$25"], 3)
        self.assertEqual(result["indirect_access_counts"]["$AA"], 1)
        self.assertEqual(result["indirect_access_counts"]["lda"], 3)
        self.assertEqual(result["indirect_access_counts"]["adc"], 1)
        self.assertEqual(result["pointer_update_classes_since_previous_$25_access"], {
            "both_bytes_written": 1, "low_only_written": 1, "no_pointer_write": 1,
        })
        self.assertEqual(result["pointer_value_change_classes_between_$25_accesses"], {
            "low_only_changed": 1, "pointer_unchanged": 1,
        })
        self.assertTrue(result["bank_context_available"])
        self.assertEqual(result["distinct_bank_contexts"], 2)
        self.assertEqual(result["ram_0b_0c_0d_write_counts"]["$0D"], 1)
        self.assertEqual(result["frames_with_$25_access_and_any_$0b_0c_0d_write"], 1)
        self.assertFalse(result["semantics_confirmed"])
        self.assertFalse(result["raw_values_disclosed"])
        serialized = json.dumps(result)
        for raw in ("8123", "9010", "8012", "8022", "9041", "R6:03", "R7:02", "pointer_low"):
            self.assertNotIn(raw, serialized)

    def test_extracts_only_observed_instruction_sites(self):
        rows = self.base_rows()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace = self.write_trace(root, rows)
            output = root / "sites.tsv"
            self.assertEqual(extract_sites(trace, output), 3)
            content = output.read_text(encoding="ascii")
            self.assertEqual(content.splitlines()[0], "pc\topcode\toperand")
            self.assertIn("8123\tB1\t25", content)
            self.assertIn("9010\tB1\tAA", content)
            self.assertNotIn("8012", content)

    def test_stage325_baseline_guard_rejects_unrelated_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = analyze(self.write_trace(Path(tmp), self.base_rows()))
        with self.assertRaisesRegex(ValueError, "Stage 325 aggregate baseline"):
            verify_stage325_baseline(result)

    def test_effective_address_mismatch_is_rejected(self):
        rows = self.base_rows()
        rows[2]["effective_address"] = "8013"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "effective address"):
                analyze(self.write_trace(Path(tmp), rows))

    def test_event_order_is_not_silently_repaired(self):
        rows = self.base_rows()
        rows[0], rows[1] = rows[1], rows[0]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "chronological order"):
                analyze(self.write_trace(Path(tmp), rows))

    def test_effective_address_wraps_at_16_bits(self):
        rows = self.base_rows()[:3]
        rows[2]["pointer_low"] = "FF"
        rows[2]["pointer_high"] = "FF"
        rows[2]["y"] = "02"
        rows[2]["effective_address"] = "0001"
        with tempfile.TemporaryDirectory() as tmp:
            result = analyze(self.write_trace(Path(tmp), rows))
        self.assertEqual(result["indirect_access_counts"]["$25"], 1)

    def test_out_of_window_event_is_rejected(self):
        rows = self.base_rows()
        rows[0]["frame"] = 599
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "frame/cycle"):
                analyze(self.write_trace(Path(tmp), rows))

    def test_bad_byte_is_rejected(self):
        rows = self.base_rows()
        rows[0]["value"] = "100"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "byte"):
                analyze(self.write_trace(Path(tmp), rows))

    def test_missing_bank_context_is_not_fabricated(self):
        rows = self.base_rows()
        for row in rows:
            row.pop("bank_context", None)
        with tempfile.TemporaryDirectory() as tmp:
            result = analyze(self.write_trace(Path(tmp), rows))
        self.assertFalse(result["bank_context_available"])
        self.assertEqual(result["distinct_bank_contexts"], 0)
        self.assertTrue(all(site["bank_context_id"] == "unknown" for site in result["top_access_sites"]))


    def test_instruction_markers_are_not_misclassified_as_ram_writes(self):
        rows = [
            {"frame": 388, "cycle": 100, "event": "writer_instruction", "pc": "C90B",
             "opcode": "84", "operand": "0C", "address": "000C", "value": "",
             "old_value": "", "pointer_low": "", "pointer_high": "", "y": "",
             "effective_address": "", "bank_context": "PRG:0C-0D-0E-0F"},
            {"frame": 388, "cycle": 100, "event": "write", "pc": "C90B",
             "opcode": "84", "operand": "0C", "address": "000C", "value": "00",
             "old_value": "00", "pointer_low": "", "pointer_high": "", "y": "",
             "effective_address": "", "bank_context": "PRG:0C-0D-0E-0F"},
            {"frame": 388, "cycle": 110, "event": "indirect", "pc": "C90D",
             "opcode": "B1", "operand": "AA", "address": "", "value": "",
             "old_value": "", "pointer_low": "8B", "pointer_high": "83", "y": "00",
             "effective_address": "838B", "bank_context": "PRG:0C-0D-0E-0F"},
            {"frame": 388, "cycle": 120, "event": "decoder_store_0b", "pc": "C922",
             "opcode": "85", "operand": "0B", "address": "", "value": "",
             "old_value": "", "pointer_low": "", "pointer_high": "", "y": "",
             "effective_address": "", "bank_context": "PRG:0C-0D-0E-0F"},
            {"frame": 388, "cycle": 120, "event": "write", "pc": "C922",
             "opcode": "85", "operand": "0B", "address": "000B", "value": "40",
             "old_value": "00", "pointer_low": "", "pointer_high": "", "y": "",
             "effective_address": "", "bank_context": "PRG:0C-0D-0E-0F"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace = self.write_trace(root, rows)
            result = analyze(trace, 388, 388)
            sites = root / "sites.tsv"
            self.assertEqual(extract_sites(trace, sites, 388, 388), 1)
        self.assertEqual(result["indirect_access_counts"]["$AA"], 1)
        self.assertEqual(result["ram_0b_0c_0d_write_counts"]["$0B"], 1)
        self.assertEqual(result["ram_0b_0c_0d_write_counts"]["$0C"], 1)
        self.assertEqual(result["frames_with_$AA_access_and_any_$0b_0c_0d_write"], 1)
        self.assertEqual(sites.read_text(encoding="ascii").splitlines(),
                         ["pc\\topcode\\toperand", "C90D\\tB1\\tAA"])
        self.assertFalse(result["semantics_confirmed"])
        self.assertFalse(result["raw_values_disclosed"])


if __name__ == "__main__":
    unittest.main()
