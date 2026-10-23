import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_private_ram0d_scroll_relation import validate_trace

DISTRIBUTION = [(0, 13), (1, 2), (2, 7), (3, 4), (4, 6), (5, 282), (6, 6), (8, 1)]


class PrivateRam0dScrollRelationTests(unittest.TestCase):
    def write_bundle(self, root: Path, mutation=None):
        clock_fields = ["frame", "begin_cycle", "end_cycle"]
        writer_fields = ["frame", "ordinal", "pc", "value", "cycle"]
        ram_fields = ["frame", "ram_0d", "ppu_2005_writes"]
        trace_fields = [
            "frame", "pc_after", "cycle", "old_value", "new_value",
            "a", "x", "y", "prev", "opcode", "operand",
        ]
        counts = []
        for count, repeat in DISTRIBUTION:
            counts.extend([count] * repeat)
        self.assertEqual(len(counts), 321)
        state = 80
        sta_remaining = 6
        did_bad_decrement = False
        clocks, writers, ram_rows, trace = [], [], [], []
        for index, frame in enumerate(range(600, 921)):
            begin = frame * 30000
            clocks.append({"frame": frame, "begin_cycle": begin, "end_cycle": begin + 30000})
            prewrite_state = state
            second = 77 if frame == 600 else (
                (prewrite_state + 1) % 256 if frame == 601 else prewrite_state
            )
            if mutation == "bad-lag" and frame == 700:
                second = (second + 1) % 256
            values = [0, second, 0, 0]
            pcs = ["E8EC", "E8F1", "E369", "E36C"]
            offsets = [800, 807, 24283, 24287]
            for ordinal in range(1, 5):
                writers.append({
                    "frame": frame, "ordinal": ordinal, "pc": pcs[ordinal-1],
                    "value": f"{values[ordinal-1]:02X}", "cycle": begin + offsets[ordinal-1],
                })

            for ordinal in range(counts[index]):
                old = state
                if sta_remaining:
                    new = (state + 10) % 256
                    opcode, pc, av, prev = "85", "D3CA", new, "F0"
                    sta_remaining -= 1
                else:
                    new = (state - 1) % 256
                    opcode, pc, av, prev = "C6", "D3CC", 0xAA, "0D"
                    if mutation == "bad-decrement" and not did_bad_decrement:
                        new = (new + 1) % 256
                        did_bad_decrement = True
                cycle = begin + 26000 + ordinal * 20
                trace.append({
                    "frame": frame, "pc_after": pc, "cycle": cycle,
                    "old_value": f"{old:02X}", "new_value": f"{new:02X}",
                    "a": f"{av:02X}", "x": "00", "y": "00",
                    "prev": prev, "opcode": opcode, "operand": "0D",
                })
                state = new
            if mutation == "bad-postframe" and frame == 700:
                state = (state + 1) % 256
            ram_rows.append({"frame": frame, "ram_0d": f"{state:02X}", "ppu_2005_writes": "4"})

        def write_tsv(name, fields, rows):
            with (root / name).open("w", encoding="ascii", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)

        write_tsv("source_frame_clock.tsv", clock_fields, clocks)
        write_tsv("road_321_writers.tsv", writer_fields, writers)
        write_tsv("road_321_postframe.tsv", ram_fields, ram_rows)
        if mutation == "missing-write":
            trace.pop()
        if mutation == "bad-cycle":
            trace[0]["cycle"] = int(trace[0]["cycle"]) + 40000
        if mutation == "bad-pc":
            trace[0]["pc_after"] = "D3CD"
        write_tsv("road_321_ram_writes.tsv", trace_fields, trace)
        marker = [
            "format=private_ram0d_scroll_writer_trace_v1",
            "frames=321",
            f"ram0d_write_events={len(trace)}",
            "ram0d_dec_events=1500",
            "ram0d_sta_events=6",
            "writer_prev_frame_comparisons=320",
            "writer_prev_frame_matches=319",
            "writer_prev_frame_mismatches=1",
            "writer_prev_frame_first_mismatch=601",
            "source_values_disclosed=no",
        ]
        if mutation == "bad-marker":
            marker[2] = "ram0d_write_events=1505"
        (root / "RAM0D_TRACE_COMPLETE.txt").write_text("\n".join(marker) + "\n", encoding="ascii")

    def audit(self, mutation=None):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_bundle(root, mutation)
            return validate_trace(root)

    def test_synthetic_trace_passes_and_emits_aggregate_only_summary(self):
        result = self.audit()
        self.assertEqual(result["frames"], 321)
        self.assertEqual(result["ram0d_write_events"], 1506)
        self.assertEqual(result["ram0d_dec_events"], 1500)
        self.assertEqual(result["ram0d_sta_events"], 6)
        self.assertEqual(result["writer_previous_frame_matches"], 319)
        self.assertEqual(result["writer_previous_frame_comparisons"], 320)
        self.assertFalse(result["ram0d_semantics_identified"])

    def test_bad_lag_relation_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("bad-lag")

    def test_bad_decrement_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("bad-decrement")

    def test_postframe_ram_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("bad-postframe")

    def test_missing_ram_write_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("missing-write")

    def test_bad_cycle_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("bad-cycle")

    def test_bad_live_instruction_pc_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("bad-pc")

    def test_bad_completion_marker_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("bad-marker")


if __name__ == "__main__":
    unittest.main()
