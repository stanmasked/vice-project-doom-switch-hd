"""Stage140 OAM overflow status lifecycle across consecutive PPU frames."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from audit_stage136_oam_eight_limit import ANCHORS,OAMLimitError
from audit_stage140_overflow_frame_reset import (
    FRAME_ANCHORS,verify_frame_source,frame_sequence)


def oam(*visible,late=None):
    values=[255]*64
    for i in visible:values[i]=120
    if late is not None:values[late]=128
    return tuple(values)


class FrameResetModel(unittest.TestCase):
    def test_ninth_sprite_overflow_clears_for_next_clean_frame(self):
        evidence=frame_sequence([oam(*range(9)),oam(*range(8))])
        self.assertEqual([x["end_overflow"] for x in evidence["frames"]],
                         [True,False])
        self.assertEqual([x["status_after_reset"] for x in evidence["frames"]],
                         [0,0])
        self.assertFalse(evidence["native_multiframe_overflow_proven"])

    def test_new_overflow_reenters_only_at_lower_eight_pixel_half(self):
        sequence=frame_sequence([
            oam(*range(9)),
            oam(*range(8)),
            oam(*range(8),late=8)],scanlines=(124,132))
        first,second,third=sequence["frames"]
        self.assertTrue(all(x["status_overflow"] for x in first["rows"]))
        self.assertFalse(any(x["status_overflow"] for x in second["rows"]))
        self.assertEqual([x["status_overflow"] for x in third["rows"]],
                         [False,True])
        self.assertEqual([x["new_overflow"] for x in third["rows"]],
                         [False,True])
        self.assertEqual(third["rows"][0]["selected"],tuple(range(8)))
        self.assertEqual(third["rows"][1]["selected"],tuple(range(8)))

    def test_overflow_bit_sticky_within_frame(self):
        # OAM8 leaves the visible window on the later row; the flag
        # still remains set until the following frame's pre-render reset.
        sprites=oam(*range(8),late=8)
        evidence=frame_sequence([sprites,sprites],scanlines=(132,149))
        for frame in evidence["frames"]:
            self.assertTrue(frame["rows"][0]["new_overflow"])
            self.assertFalse(frame["rows"][1]["new_overflow"])
            self.assertTrue(frame["rows"][1]["status_overflow"])
            self.assertTrue(frame["end_overflow"])

    def test_free_eighth_slot_never_generates_false_overflow(self):
        arr=oam(*range(7),late=8)
        frames=frame_sequence([arr,arr],scanlines=(124,132))
        for f in frames["frames"]:
            self.assertFalse(f["end_overflow"])
            self.assertEqual([row["count"] for row in f["rows"]],[7,8])
            self.assertEqual(f["rows"][1]["selected"],tuple(range(7))+(8,))

    def test_bad_controls_fail_closed(self):
        fine=oam(*range(8))
        cases=[
            ([],(124,132),16),
            ([fine],(124,132),16),
            ([fine,fine],(),16),
            ([fine,fine],(132,124),16),
            ([fine,fine],(124,124),16),
            ([fine,fine],(124,132),12),
            ([fine,fine],[124,True],16),
            ([fine,fine],(124,241),16),
            ([fine,(120,)*63],(124,132),16),
        ]
        for frames,rows,height in cases:
            with self.subTest(rows=rows,height=height,n=len(frames)):
                with self.assertRaises(OAMLimitError):
                    frame_sequence(frames,scanlines=rows,height=height)

    def test_pinned_vblank_reset_source_order_and_mutations(self):
        text="\n".join(FRAME_ANCHORS+ANCHORS)
        source=verify_frame_source(text)
        self.assertTrue(source["source_frame_status_reset"])
        self.assertEqual(source["clears_overflow_bit"],0x20)
        self.assertFalse(source["native_multiframe_overflow_proven"])
        for anchor in FRAME_ANCHORS:
            with self.subTest(anchor=anchor),self.assertRaises(OAMLimitError):
                verify_frame_source(text.replace(anchor,"removed"))
        for wrong in (text+"\n"+text,
                      "\n".join(reversed(FRAME_ANCHORS)+ANCHORS),
                      "\n".join(ANCHORS+FRAME_ANCHORS),None):
            with self.assertRaises(OAMLimitError):
                verify_frame_source(wrong)


if __name__=="__main__":
    unittest.main()
