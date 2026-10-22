"""Fabricated FCEUX 41-slot RGB slices; never uses original NES art."""
from __future__ import annotations
import struct
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_road_rgb_321 import (
    MAGIC,SCHEMA,SLOT_FRAMES,SCANLINES,WIDTH,EXACT_SIZE,validate_scanlines
)

def synthetic_rgb()->bytes:
    parts=[SCHEMA.pack(MAGIC,41,WIDTH,4,0,*SCANLINES)]
    for f in SLOT_FRAMES:
        parts.append(struct.pack("<H",f))
        # Purely invented RGB pattern. No game or FCEUX input.
        for y in SCANLINES:
            parts.append(bytes((x+f)%256 for x in range(WIDTH)
                         for _ in range(3))) 
    result=b"".join(parts)
    assert len(result)==EXACT_SIZE
    return result

class SameSessionRgbTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"road_321_rgb_scanlines.bin"
        self.path.write_bytes(synthetic_rgb())
    def tearDown(self):self.tmp.cleanup()
    def test_all_fabricated_rgb_slots(self):
        result=validate_scanlines(self.path)
        self.assertEqual(result["source_image_capture_slots"],41)
        self.assertEqual(result["source_image_rgb_triplets"],41984)
        self.assertFalse(result["previous_legacy_37_of_41_edge_classification_reproduced"])
    def reject(self,fn):
        raw=bytearray(self.path.read_bytes())
        fn(raw)
        self.path.write_bytes(raw)
        with self.assertRaises(ValueError):validate_scanlines(self.path)
    def test_wrong_movie_frame_label(self):
        self.reject(lambda b:struct.pack_into("<H",b,SCHEMA.size,601))
    def test_wrong_last_movie_frame(self):
        self.reject(lambda b:struct.pack_into(
            "<H",b,SCHEMA.size+40*(2+4*256*3),919))
    def test_truncated_private_rgb(self):
        self.reject(lambda b:b.pop())
    def test_unexpected_extra_rgb(self):
        self.reject(lambda b:b.append(0))
    def test_wrong_y_positions(self):
        self.reject(lambda b:b.__setitem__(SCHEMA.size-1,179))
    def test_wrong_movie_interval_count(self):
        self.reject(lambda b:struct.pack_into("<H",b,8,40))
    def test_wrong_rgb_magic(self):
        self.reject(lambda b:b.__setitem__(0,ord("X")))
    def test_wrong_color_channel_contract(self):
        self.reject(lambda b:struct.pack_into("<H",b,10,128))
    def test_symlink_report_refused(self):
        other=self.path.parent/"linked.bin"
        try:other.symlink_to(self.path)
        except OSError as exc:self.skipTest(str(exc))
        with self.assertRaises(ValueError):validate_scanlines(other)
if __name__=="__main__":unittest.main()
