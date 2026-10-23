import csv
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_private_road_ppu_latch_rgb321 import EVENT_FIELDS, validate_capture


class SameSessionRoadPpuRgbTests(unittest.TestCase):
    def write_bundle(self, root: Path, mutation: str | None = None) -> None:
        events = []
        cpu_rows = []
        ram_rows = []
        clocks = []
        seq = 0

        def add(frame, kind, address, value, pc, cycle, opcode=0, a=0, x=0, y=0):
            events.append({
                "frame": frame, "seq": 0, "type": kind,
                "address": f"{address:04X}", "size": 1, "value": value,
                "pc": f"{pc:04X}", "opcode": f"{opcode:02X}",
                "a": f"{a:02X}", "x": f"{x:02X}", "y": f"{y:02X}",
                "cycle": cycle,
            })

        for index, frame in enumerate(range(600, 921)):
            begin = frame * 30000
            clock_begin = begin + (2 if mutation == "boundary-gap" and frame >= 601 else 0)
            clocks.append({"frame": frame, "begin_cycle": clock_begin, "end_cycle": clock_begin + 30000})
            frame_events = []

            def frame_add(*args, **kwargs):
                before = len(events)
                add(*args, **kwargs)
                frame_events.append(events.pop(before))

            for i in range(3 if index < 166 else 2):
                frame_add(frame, "W2000", 0x2000, "88", 0xE69A, begin + 20 + 2 * i, a=0x88)
            for i in range(2):
                frame_add(frame, "W2001", 0x2001, "1E", 0xE6A1, begin + 30 + 2 * i, a=0x1E)
            for i in range(3 if index < 203 else 2):
                frame_add(frame, "R2002", 0x2002, "--", 0xE8E7, begin + 100 + 2 * i, opcode=0xAD)
            for pair in range(11 if index < 102 else 10):
                frame_add(frame, "W2006", 0x2006, "23", 0xE6A2, begin + 200 + 4 * pair)
                frame_add(frame, "W2006", 0x2006, "00", 0xE6A5, begin + 202 + 4 * pair)
            values = [0, frame % 256, 0, 0]
            if mutation == "writer-mismatch" and frame == 700:
                values[1] = (values[1] + 1) % 256
            for ordinal, (pc, value, offset) in enumerate(zip(
                (0xE8EF, 0xE8F4, 0xE36C, 0xE36F),
                values, (800, 807, 24283, 24287),
            ), 1):
                frame_add(frame, "W2005", 0x2005, f"{value:02X}", pc, begin + offset)
                cpu_rows.append({
                    "frame": frame, "ordinal": ordinal,
                    "pc": f"{(0xE8EC, 0xE8F1, 0xE369, 0xE36C)[ordinal-1]:04X}",
                    "value": f"{(0, frame % 256, 0, 0)[ordinal-1]:02X}",
                    "cycle": begin + offset,
                })
            if mutation == "interrupt-pair" and frame == 700:
                candidates = [event for event in frame_events if event["type"] == "W2006"]
                candidates[-1]["cycle"] = begin + 803
            if mutation == "outside-clock" and frame == 700:
                frame_events[0]["cycle"] = begin + 31000
            frame_events.sort(key=lambda event: event["cycle"])
            for event in frame_events:
                seq += 1
                event["seq"] = seq
                events.append(event)
            ram_rows.append({"frame": frame, "ram_0d": f"{frame % 256:02X}", "ppu_2005_writes": "4"})

        with (root / "source_frame_clock.tsv").open("w", encoding="ascii", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["frame", "begin_cycle", "end_cycle"], delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(clocks)
        with (root / "ppu_register_events.tsv").open("w", encoding="ascii", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=EVENT_FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(events)
        with (root / "road_321_writers.tsv").open("w", encoding="ascii", newline="") as stream:
            fields = ["frame", "ordinal", "pc", "value", "cycle"]
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            selected = [r for r in cpu_rows if not (mutation == "missing-writer" and r["frame"] == 700 and r["ordinal"] == 2)]
            writer.writerows(selected)
        with (root / "road_321_postframe.tsv").open("w", encoding="ascii", newline="") as stream:
            fields = ["frame", "ram_0d", "ppu_2005_writes"]
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(ram_rows)

        kinds = ("R2002", "W2000", "W2001", "W2002", "W2005", "W2006")
        counts = {kind: sum(event["type"] == kind for event in events) for kind in kinds}
        count_lines = [
            "frames=321", "first=600", "last=920",
            *(f"{kind}={counts[kind]}" for kind in kinds),
            "frame_clock_rows=321", f"total_events={len(events)}",
            "cpu_writer_events=1284", "postframe_ram_samples=321",
            "rgb_slots=41", "source_values_disclosed=no",
        ]
        (root / "ppu_register_counts.tsv").write_text("\n".join(count_lines) + "\n", encoding="ascii")
        complete = [
            "format=private_road_ppu_latch_rgb321_v1", "frames=321",
            f"events={len(events)}", "frame_clock_rows=321",
            "cpu_writer_events=1284", "postframe_ram_samples=321", "rgb_slots=41",
            "rom_identity_verified=yes", "movie_readonly_verified=yes", "source_values_disclosed=no",
        ]
        (root / "COMPLETE.txt").write_text("\n".join(complete) + "\n", encoding="ascii")
        rgb = bytearray(b"VPDRGB41" + bytes((41, 0, 0, 1, 4, 0, 0, 0, 120, 140, 160, 180)))
        for index, frame in enumerate(range(600, 921, 8)):
            frame_id = frame + 1 if mutation == "bad-rgb-frame" and index == 7 else frame
            rgb.extend(bytes((frame_id % 256, frame_id // 256)))
            rgb.extend(bytes((frame % 256,)) * 3072)
        (root / "road_321_rgb_scanlines.bin").write_bytes(rgb)

    def audit(self, mutation=None):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_bundle(root, mutation)
            return validate_capture(root)

    def test_complete_synthetic_bundle_passes(self):
        result = self.audit()
        self.assertEqual(result["frames"], 321)
        self.assertEqual(result["cpu_writer_events"], 1284)
        self.assertEqual(result["ppu_register_events"], 10203)
        self.assertEqual(result["postframe_ram_samples"], 321)
        self.assertEqual(result["rgb_slots"], 41)
        self.assertEqual(result["cpu_port_values_matched"], 1284)
        self.assertEqual(result["cpu_port_cycles_matched"], 1284)
        self.assertEqual(result["interrupted_scroll_pairs"], 0)

    def test_small_nonoverlapping_frame_boundary_gap_allowed(self):
        self.assertEqual(self.audit("boundary-gap")["frames"], 321)

    def test_ppuaddr_write_between_scroll_pair_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("interrupt-pair")

    def test_cpu_port_value_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("writer-mismatch")

    def test_missing_cpu_writer_row_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("missing-writer")

    def test_bad_rgb_slot_frame_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("bad-rgb-frame")

    def test_event_outside_frame_clock_rejected(self):
        with self.assertRaises(ValueError):
            self.audit("outside-clock")


if __name__ == "__main__":
    unittest.main()
