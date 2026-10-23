import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_private_same_session_road_ppu_latch_rgb321_join import (
    derive_numeric_documents,
)
from audit_private_road_ppu_alignment import audit as audit_alignment

ROAD_GRAY = bytes((117, 117, 117))
ROWS = (120, 140, 160, 180)
AMBIGUOUS = {712, 720, 728, 736}
ANCHORS = {
    600: (66, 188, 79, 79),
    744: (66, 188, 136, 134),
    800: (100, 155, 144, 139),
    920: (116, 203, 24, 19),
}


class SameSessionRoadPpuJoinTests(unittest.TestCase):
    def build_folder(self, root: Path, mutation=None):
        identity = {"rom_sha256": "a" * 64, "fm2_sha256": "b" * 64}
        rgb = bytearray(b"VPDRGB41" + bytes((41, 0, 0, 1, 4, 0, 0, 0, 120, 140, 160, 180)))
        for index, frame in enumerate(range(600, 921, 8)):
            rgb.extend(bytes((frame % 256, frame // 256)))
            if frame in AMBIGUOUS and not (mutation == "accept-ambiguous" and frame == 712):
                for _ in ROWS:
                    rgb.extend(bytes(256 * 3))
                continue
            if frame in ANCHORS:
                left, right = ANCHORS[frame][0:2]
            else:
                left, right = 50 + index % 20, 120 + index % 20
            if mutation == "bad-image-anchor" and frame == 600:
                left += 1
            for _ in ROWS:
                row = bytearray(256 * 3)
                for x in range(left, right + 1):
                    row[3*x:3*x+3] = ROAD_GRAY
                rgb.extend(row)
        (root / "road_321_rgb_scanlines.bin").write_bytes(rgb)

        writer_fields = ["frame", "ordinal", "pc", "value", "cycle"]
        ram_fields = ["frame", "ram_0d", "ppu_2005_writes"]
        clock_fields = ["frame", "begin_cycle", "end_cycle"]
        with (root / "road_321_writers.tsv").open("w", encoding="ascii", newline="") as stream:
            import csv
            writer = csv.DictWriter(stream, fieldnames=writer_fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for frame in range(600, 921):
                begin = frame * 30000
                second = ANCHORS.get(frame, (0, 0, frame % 256, frame % 256))[2]
                if mutation == "bad-cpu-anchor" and frame == 600:
                    second = (second + 1) % 256
                values = (0, second, 0, 0)
                pcs = ("E8EC", "E8F1", "E369", "E36C")
                offsets = (800, 807, 24283, 24287)
                for ordinal in range(1, 5):
                    writer.writerow({
                        "frame": frame, "ordinal": ordinal, "pc": pcs[ordinal-1],
                        "value": f"{values[ordinal-1]:02X}", "cycle": begin + offsets[ordinal-1],
                    })
        with (root / "road_321_postframe.tsv").open("w", encoding="ascii", newline="") as stream:
            import csv
            writer = csv.DictWriter(stream, fieldnames=ram_fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for frame in range(600, 921):
                ram = ANCHORS.get(frame, (0, 0, 0, frame % 256))[3]
                writer.writerow({"frame": frame, "ram_0d": f"{ram:02X}", "ppu_2005_writes": 4})
        with (root / "source_frame_clock.tsv").open("w", encoding="ascii", newline="") as stream:
            import csv
            writer = csv.DictWriter(stream, fieldnames=clock_fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            for frame in range(600, 921):
                begin = frame * 30000
                writer.writerow({"frame": frame, "begin_cycle": begin, "end_cycle": begin + 30000})
        return identity

    def test_fresh_numeric_docs_join_and_match_four_anchors(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            identity = self.build_folder(root)
            road, ppu, coverage = derive_numeric_documents(root, identity)
            result = audit_alignment(road, ppu)
            self.assertEqual(coverage["rgb_slots"], 41)
            self.assertEqual(coverage["accepted_intervals"], 37)
            self.assertEqual(coverage["ambiguous_intervals"], 4)
            self.assertEqual(coverage["cpu_writer_events"], 1284)
            self.assertEqual(result["joined_frames"], 37)
            self.assertEqual(result["published_anchor_frames"], [600, 744, 800, 920])
            self.assertFalse(coverage["ambiguous_frames"] == [])

    def test_ambiguous_frame_is_not_interpolated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            identity = self.build_folder(root, "accept-ambiguous")
            with self.assertRaises(ValueError):
                derive_numeric_documents(root, identity)

    def test_published_image_anchor_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            identity = self.build_folder(root, "bad-image-anchor")
            road, ppu, _ = derive_numeric_documents(root, identity)
            with self.assertRaises(ValueError):
                audit_alignment(road, ppu)

    def test_published_cpu_anchor_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            identity = self.build_folder(root, "bad-cpu-anchor")
            road, ppu, _ = derive_numeric_documents(root, identity)
            with self.assertRaises(ValueError):
                audit_alignment(road, ppu)


if __name__ == "__main__":
    unittest.main()
