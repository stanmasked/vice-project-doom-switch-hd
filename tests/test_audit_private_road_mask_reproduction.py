"""Independently invented roadway gray masks; no real NES images."""
from __future__ import annotations

import copy
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))

from audit_private_road_rgb_321 import MAGIC,SCHEMA,SLOT_FRAMES,SCANLINES,WIDTH
from audit_private_road_mask_reproduction import (
    ROAD_GRAY,row_span,extract_report,compare_to_legacy
)
from test_audit_private_legacy_road_geometry import synthetic as fabricated_legacy

BG=bytes((13,34,55))

def fabricated_rgb(legacy:dict)->bytes:
    blocks=[SCHEMA.pack(MAGIC,41,WIDTH,4,0,*SCANLINES)]
    for frame,record in zip(SLOT_FRAMES,legacy["frames"]):
        assert record["frame"]==frame
        blocks.append(struct.pack("<H",frame))
        n=record["valid_scanline_count"]
        for i,y in enumerate(SCANLINES):
            row=bytearray(BG*WIDTH)
            if i<n:
                left=record.get("observed_left_edge",66)
                right=record.get("observed_right_edge",188)
                for x in range(left,right+1):
                    row[3*x:3*x+3]=ROAD_GRAY
            blocks.append(bytes(row))
    return b"".join(blocks)

class SameSessionRoadMaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.file=Path(self.tmp.name)/"road_321_rgb_scanlines.bin"
        self.legacy=fabricated_legacy()
        self.file.write_bytes(fabricated_rgb(self.legacy))
    def tearDown(self):self.tmp.cleanup()
    def extract(self):
        return extract_report(self.file)
    def fail_file(self,patch):
        b=bytearray(self.file.read_bytes())
        patch(b)
        self.file.write_bytes(b)
        with self.assertRaises(ValueError):
            compare_to_legacy(self.extract(),self.legacy)
    def test_all_37_source_free_masks_reproduced(self):
        r=compare_to_legacy(self.extract(),self.legacy)
        self.assertEqual(r["new_original_rgb_intervals_reproduced"],37)
        self.assertEqual(r["ambiguous_source_slots_preserved"],4)
        self.assertFalse(r["old_hashless_road_report_sha256_proven"])
    def test_full_screen_solid_gray_not_road(self):
        self.assertIsNone(row_span(ROAD_GRAY*256))
    def test_short_scattered_gray_not_road(self):
        self.assertIsNone(row_span(ROAD_GRAY*29+BG*(256-29)))
    def test_wrong_scanline_byte_count(self):
        with self.assertRaises(ValueError):row_span(ROAD_GRAY*255)
    def test_incorrect_published_source_anchor_detected(self):
        wrong=copy.deepcopy(self.legacy)
        wrong["frames"][0]["observed_left_edge"]=67
        with self.assertRaises(ValueError):
            compare_to_legacy(self.extract(),wrong)
    def test_old_numeric_report_changed_is_rejected(self):
        wrong=copy.deepcopy(self.legacy)
        wrong["summary"]["minimum_observed_width"]=1
        with self.assertRaises(ValueError):
            compare_to_legacy(self.extract(),wrong)
    def test_non_source_gray_color_not_accepted(self):
        # Three of the four independent source scanlines must shift;
        # changing only one intentionally does NOT affect the median.
        def corrupt(b):
            for row in range(3):
                first=SCHEMA.size+2+row*256*3+3*66
                b[first:first+3]=bytes((116,117,117))
        self.fail_file(corrupt)
    def test_truncated_original_free_rgb_file_rejected(self):
        raw=self.file.read_bytes()
        self.file.write_bytes(raw[:-1])
        with self.assertRaises(ValueError):self.extract()
    def test_wrong_frame_label_rejected(self):
        raw=bytearray(self.file.read_bytes())
        struct.pack_into("<H",raw,SCHEMA.size,601)
        self.file.write_bytes(raw)
        with self.assertRaises(ValueError):self.extract()
    def test_ambiguous_slots_cannot_invent_gray_road(self):
        # Insert gray road color in two formerly absent row slots at 712,
        # turning two visible scanlines into four (invalid legacy status).
        pos=SLOT_FRAMES.index(712)
        start=SCHEMA.size+pos*(2+4*256*3)+2+2*256*3
        def fill(b):
            for y in range(2):
                for x in range(66,189):
                    at=start+y*256*3+x*3
                    b[at:at+3]=ROAD_GRAY
        self.fail_file(fill)
    def test_roi_scanline_count_comparison_is_strict(self):
        wrong=copy.deepcopy(self.legacy)
        wrong["frames"][0]["valid_scanline_count"]=3
        with self.assertRaises(ValueError):
            compare_to_legacy(self.extract(),wrong)
    def test_unknown_report_does_not_pass_legacy_gate(self):
        with self.assertRaises(ValueError):
            compare_to_legacy(self.extract(),{"fake":True})

if __name__=="__main__":unittest.main()
