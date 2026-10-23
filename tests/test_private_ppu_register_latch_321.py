import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_private_ppu_register_latch_321 import EVENT_FIELDS, validate_trace_bundle


class PrivatePpuRegisterLatchTests(unittest.TestCase):
    def write_bundle(self, root: Path, mutation: str | None = None) -> dict[int, list[int]]:
        events = []
        clocks = []
        expected = {frame: [0, frame % 256, 0, 0] for frame in range(600, 921)}

        def add(frame, kind, address, value, pc, cycle, opcode=0, a=0, x=0, y=0):
            events.append({
                "frame": frame, "seq": 0, "type": kind,
                "address": f"{address:04X}", "size": 1, "value": value,
                "pc": f"{pc:04X}", "opcode": f"{opcode:02X}",
                "a": f"{a:02X}", "x": f"{x:02X}", "y": f"{y:02X}",
                "cycle": cycle,
            })

        for frame in range(600, 921):
            begin = frame * 30000
            clocks.append({"frame": frame, "begin_cycle": begin, "end_cycle": begin + 30000})
            add(frame, "W2000", 0x2000, "88", 0xE69A, begin + 20, a=0x88)
            add(frame, "W2001", 0x2001, "1E", 0xE6A1, begin + 30, a=0x1E)
            indexed_bad = mutation == "indexed-status" and frame == 700
            add(
                frame, "R2002", 0x2002, "--", 0xE8E7, begin + 100,
                opcode=0x19 if indexed_bad else 0xAD, y=1 if indexed_bad else 0,
            )
            add(frame, "W2006", 0x2006, "23", 0xE6A2, begin + 200, a=0x23)
            add(frame, "W2006", 0x2006, "00", 0xE6A5, begin + 204)
            add(
                frame, "W2005", 0x2005,
                "01" if mutation == "bad-value" and frame == 700 else "00",
                0xE8EF, begin + 800,
            )
            if mutation == "status-between" and frame == 700:
                add(frame, "R2002", 0x2002, "--", 0xE8E7, begin + 803, opcode=0xAD)
            if mutation == "address-between" and frame == 700:
                add(frame, "W2006", 0x2006, "23", 0xE6A2, begin + 803)
            if not (mutation == "missing-scroll" and frame == 700):
                add(frame, "W2005", 0x2005, f"{frame % 256:02X}", 0xE8F4, begin + 807)
            add(frame, "W2005", 0x2005, "00", 0xE36C, begin + 24283)
            add(frame, "W2005", 0x2005, "00", 0xE36F, begin + 24287)
            add(frame, "W2006", 0x2006, "23", 0xE6A2, begin + 25000)
            add(frame, "W2006", 0x2006, "00", 0xE6A5, begin + 25004)

        for seq, event in enumerate(events, 1):
            event["seq"] = seq
            if mutation == "outside-clock" and event["frame"] == 700 and event["type"] == "W2005" and event["pc"] == "E8EF":
                event["cycle"] = event["frame"] * 30000 + 31000

        with (root / "ppu_register_events.tsv").open("w", encoding="ascii", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=EVENT_FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(events)
        with (root / "ppu_register_frame_clock.tsv").open("w", encoding="ascii", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["frame", "begin_cycle", "end_cycle"], delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(clocks)

        kinds = ("R2002", "W2000", "W2001", "W2002", "W2005", "W2006")
        counts = {kind: sum(event["type"] == kind for event in events) for kind in kinds}
        total = len(events)
        count_lines = [
            "frames=321", "first=600", "last=920",
            *(f"{kind}={counts[kind]}" for kind in kinds),
            "frame_clock_rows=321", f"total_events={total}", "source_values_disclosed=no",
        ]
        (root / "ppu_register_counts.tsv").write_text("\n".join(count_lines) + "\n", encoding="ascii")
        complete = [
            "format=private_ppu_latch_trace_v1", "frames=321",
            f"events={total}", "frame_clock_rows=321",
            "rom_identity_verified=yes", "movie_readonly_verified=yes",
        ]
        (root / "COMPLETE.txt").write_text("\n".join(complete) + "\n", encoding="ascii")
        return expected

    def run_bundle(self, mutation=None, expected_writer_values=None):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            expected = self.write_bundle(root, mutation)
            if expected_writer_values is None:
                expected_writer_values = expected
            return validate_trace_bundle(root, expected_writer_values)

    def test_valid_bundle_passes_and_matches_cpu_port_values(self):
        result = self.run_bundle()
        self.assertEqual(result["frames"], 321)
        self.assertEqual(result["events"], 3531)
        self.assertEqual(result["scroll_writes"], 1284)
        self.assertEqual(result["cpu_port_values_matched"], 1284)
        self.assertEqual(result["scroll_latch_roles_per_frame"], "0,1,0,1")
        self.assertEqual(result["interrupted_scroll_pairs"], 0)

    def test_status_read_between_scroll_pair_rejected(self):
        with self.assertRaises(ValueError):
            self.run_bundle("status-between")

    def test_ppu_address_write_between_scroll_pair_rejected(self):
        with self.assertRaises(ValueError):
            self.run_bundle("address-between")

    def test_missing_scroll_write_rejected(self):
        with self.assertRaises(ValueError):
            self.run_bundle("missing-scroll")

    def test_nonzero_indexed_status_candidate_rejected(self):
        with self.assertRaises(ValueError):
            self.run_bundle("indexed-status")

    def test_out_of_frame_event_rejected(self):
        with self.assertRaises(ValueError):
            self.run_bundle("outside-clock")

    def test_scroll_port_value_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            self.run_bundle("bad-value")

    def test_cpu_reference_value_mismatch_rejected(self):
        expected = {frame: [0, frame % 256, 0, 0] for frame in range(600, 921)}
        expected[700] = [0, (700 + 1) % 256, 0, 0]
        with self.assertRaises(ValueError):
            self.run_bundle(expected_writer_values=expected)


if __name__ == "__main__":
    unittest.main()
