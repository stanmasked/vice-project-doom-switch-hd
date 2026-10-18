"""Stage147 fail-closed native source provenance validation.

ROM-independent unit tests: only pinned native FCEUX can produce the actual
source certificate needed for the Stage147 milestone.
"""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from run_stage147_native_frame_source import (
    PASS,ColorSourceError,verify)


def source(mode):
    overflow=mode=="nine_overflow"
    color=143 if overflow else 170
    raw=15 if overflow else 42
    sprite=0 if overflow else 1
    return (
        "VPD_STAGE147_NATIVE_FRAME_COLOR_SOURCE_PASS "
        "case=%s first_raw=%d second_raw=%d "
        "first_sprite=%d second_sprite=%d "
        "first_bgpattern=0 second_bgpattern=0 "
        "first_xbuf=%d second_xbuf=%d samples=16 invalid=0 "
        "native_fceux=yes synthetic_only=yes "
        "original_game_color_source_proven=no" %
        (mode,raw,raw,sprite,sprite,color,color))


def frame(mode):
    overflow=mode=="nine_overflow"
    color=143 if overflow else 170
    flag="yes" if overflow else "no"
    return (
        "VPD_STAGE141_NATIVE_FRAME_RESET_PASS "
        "case=%s first_overflow=%s reset_before=%s reset_after=no "
        "second_overflow=%s first_xbuf=%d second_xbuf=%d "
        "samples=16 invalid=0 actual_ppu_reset_and_xbuf=yes "
        "synthetic_only=yes original_game_frame_reset_proven=no" %
        (mode,flag,flag,flag,color,color))


class NativeFrameSource(unittest.TestCase):
    def test_both_independent_two_frame_colors_and_sprite_sources(self):
        for mode in ("eight_visible","nine_overflow"):
            with self.subTest(mode=mode):
                report=verify(source(mode)+"\n"+frame(mode),mode)
                self.assertEqual(report["case"],mode)
                self.assertEqual(report["samples"],16)
                self.assertEqual(report["raw_colors"],(15,15) if
                                 mode=="nine_overflow" else (42,42))
                self.assertEqual(report["sprite_pixels"],(0,0) if
                                 mode=="nine_overflow" else (1,1))
                self.assertEqual(report["background_patterns"],(0,0))
                self.assertFalse(report["original_game_color_source_proven"])

    def test_wrong_raw_source_fail_closed_even_when_xbuf_unchanged(self):
        for mode in ("eight_visible","nine_overflow"):
            correct=source(mode)+"\n"+frame(mode)
            wrong=(
                "",
                source(mode),
                frame(mode),
                correct+"\n"+source(mode),
                correct+"\n"+frame(mode),
                correct.replace("second_raw=", "second_raw=0"),
                correct.replace("first_sprite=0", "first_sprite=1") if
                    mode=="nine_overflow" else
                    correct.replace("first_sprite=1","first_sprite=0"),
                correct.replace("second_sprite=0", "second_sprite=1") if
                    mode=="nine_overflow" else
                    correct.replace("second_sprite=1","second_sprite=0"),
                correct.replace("first_bgpattern=0","first_bgpattern=3"),
                correct.replace("second_bgpattern=0","second_bgpattern=2"),
                correct.replace("first_xbuf=","first_xbuf=0"),
                correct.replace("second_xbuf=","second_xbuf=0"),
                correct.replace("samples=16","samples=8"),
                correct.replace("invalid=0","invalid=1"),
                correct.replace("native_fceux=yes","native_fceux=no"),
                correct.replace("original_game_color_source_proven=no",
                                "original_game_color_source_proven=yes"),
                correct+"\nVPD_STAGE141_REJECTED_FRAME_RESET case="+mode,
                correct.replace("first_raw=","first_raw=+"),
                correct.replace("first_raw=","first_raw=0"),
            )
            for i,broken in enumerate(wrong):
                with self.subTest(mode=mode,mutation=i):
                    with self.assertRaises(ColorSourceError):
                        verify(broken,mode)

    def test_wrong_mode_or_nontext_never_accepted(self):
        for mode in ("eight_visible","nine_overflow"):
            other="eight_visible" if mode=="nine_overflow" else "nine_overflow"
            with self.assertRaises(ColorSourceError):
                verify(source(mode)+"\n"+frame(mode),other)
        for bad in (None,123,b"",{},[],True):
            with self.subTest(value=bad):
                with self.assertRaises(ColorSourceError):
                    verify(bad,"nine_overflow")


if __name__=="__main__":
    unittest.main()
