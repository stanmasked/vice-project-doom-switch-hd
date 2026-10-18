"""Stage146: stale-vs-relocated JMP evidence and native runner controls.

These are parser, fixture, and orchestration unit tests. Only the pinned
native FCEUX CI job can provide the actual causal framebuffer evidence.
"""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from make_stage141_frame_reset_rom import make_rom as make_stale_rom
from make_stage144_stable_frame_rom import (
    make_rom as make_stable_rom, relocate, relocation_sites)
from run_stage141_native_frame_reset import (
    FrameResetError,execute,run,verify,verify_rejection,
    verify_stale_jump_rejection)

STALE_DIAGNOSTIC=(
    "VPD_STAGE143_FRAME_PIXEL_DIAGNOSTIC case=nine_overflow "
    "first_raw=15 second_raw=36 first_sprite=0 second_sprite=0 "
    "first_bgpattern=0 second_bgpattern=0 first_xbuf=143 "
    "second_xbuf=164 synthetic_only=yes")
STALE_REJECTION=(
    "VPD_STAGE141_REJECTED_FRAME_RESET case=nine_overflow "
    "invalid=8 first_overflow=yes reset_before=yes reset_after=no "
    "second_overflow=yes first_xbuf=143 second_xbuf=164 "
    "samples=16 synthetic_only=yes")
STALE_LOG=STALE_DIAGNOSTIC+"\n"+STALE_REJECTION
FALSE_CLEAN=(
    "VPD_STAGE141_REJECTED_FRAME_RESET case=eight_visible "
    "invalid=19 first_overflow=yes reset_before=yes reset_after=no "
    "second_overflow=yes first_xbuf=143 second_xbuf=143 "
    "samples=16 synthetic_only=yes")


def positive(mode):
    overflow=mode=="nine_overflow"
    flag="yes" if overflow else "no"
    color=143 if overflow else 170
    return ("VPD_STAGE141_NATIVE_FRAME_RESET_PASS "
            "case=%s first_overflow=%s reset_before=%s reset_after=no "
            "second_overflow=%s first_xbuf=%d second_xbuf=%d "
            "samples=16 invalid=0 actual_ppu_reset_and_xbuf=yes "
            "synthetic_only=yes original_game_frame_reset_proven=no"%
            (mode,flag,flag,flag,color,color))


class StaleJumpCertificate(unittest.TestCase):
    def test_genuine_stale_scenario_accepts_only_explicit_rejection(self):
        observed=verify_stale_jump_rejection(STALE_LOG)
        self.assertTrue(observed["stale_jmp"])
        self.assertEqual((observed["first_xbuf"],observed["second_xbuf"]),
                         (143,164))
        self.assertFalse(observed["native_sprite_pixel"])
        with self.assertRaises(FrameResetError):
            verify(STALE_LOG,"nine_overflow")

    def test_corrupted_duplicated_or_forged_native_evidence_is_rejected(self):
        wrong=(
            "",STALE_DIAGNOSTIC,STALE_REJECTION,
            STALE_LOG+"\n"+STALE_REJECTION,STALE_LOG+"\n"+STALE_DIAGNOSTIC,
            STALE_LOG+"\n"+positive("nine_overflow"),
            STALE_LOG.replace("second_raw=36","second_raw=15"),
            STALE_LOG.replace("first_sprite=0","first_sprite=1"),
            STALE_LOG.replace("second_sprite=0","second_sprite=1"),
            STALE_LOG.replace("second_bgpattern=0","second_bgpattern=3"),
            STALE_LOG.replace("first_raw=15","first_raw=015"),
            STALE_LOG.replace("first_xbuf=143","first_xbuf=170"),
            STALE_LOG.replace("second_xbuf=164","second_xbuf=143"),
            STALE_LOG.replace("invalid=8","invalid=08"),
            STALE_LOG.replace("reset_after=no","reset_after=yes"),
            STALE_LOG.replace("case=nine_overflow","case=eight_visible"),
            STALE_LOG.replace("samples=16","samples=8"),
        )
        for i,bad in enumerate(wrong):
            with self.subTest(case=i),self.assertRaises(FrameResetError):
                verify_stale_jump_rejection(bad)

    def test_illegal_native_negative_mode_fails_before_execution(self):
        for kwargs in (
            {"mode":"eight_visible","stale":True},
            {"mode":"nine_overflow","stale":True,"enabled":False},
            {"mode":"nine_overflow","stale":True,"reject":True},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(FrameResetError):
                    execute("unused","unused","unused",**kwargs)


class PairedROMControl(unittest.TestCase):
    def test_only_eight_6502_jump_operand_bytes_change(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            old=root/"stale.nes"
            new=root/"stable.nes"
            make_stale_rom(old,"nine_overflow")
            make_stable_rom(new,"nine_overflow")
            original=old.read_bytes()
            stabilized=new.read_bytes()
            self.assertEqual(stabilized,relocate(original))
            self.assertEqual(len(original),len(stabilized))
            self.assertEqual(len(relocation_sites(original)),4)
            differences=[i for i,(a,b) in enumerate(zip(original,stabilized))
                         if a!=b]
            permitted={start+rel+k
                       for start,rel in relocation_sites(original)
                       for k in (1,2)}
            self.assertEqual(set(differences),permitted)
            self.assertEqual(len(differences),8)
            self.assertEqual(original[:16],stabilized[:16])
            self.assertEqual(original[32784:],stabilized[32784:])

    def test_harness_requires_both_native_scenarios_and_stale_control(self):
        calls=[]
        def fake_execute(binary,rom,folder,mode,**flags):
            calls.append((mode,flags,Path(rom).name))
            if flags.get("stale"):
                self.assertEqual(mode,"nine_overflow")
                self.assertEqual(Path(rom).name,"stale_nine_overflow.nes")
                return verify_stale_jump_rejection(STALE_LOG)
            if flags.get("reject"):
                return verify_rejection(FALSE_CLEAN)
            if flags.get("enabled") is False:
                return None
            return verify(positive(mode),mode)

        with tempfile.TemporaryDirectory() as td:
            with mock.patch(
                    "run_stage141_native_frame_reset.execute",
                    side_effect=fake_execute):
                printed=io.StringIO()
                with redirect_stdout(printed):
                    outcome=run("mock-binary",td)
        self.assertEqual(outcome["cases"],2)
        self.assertEqual(outcome["samples"],32)
        self.assertEqual(len(calls),5)
        self.assertEqual([mode for mode,_,_ in calls],
                         ["eight_visible","nine_overflow","eight_visible",
                          "nine_overflow","eight_visible"])
        self.assertTrue(calls[3][1]["stale"])
        self.assertIn("STAGE146_NATIVE_STALE_JMP_CAUSAL_CONTROL",printed.getvalue())
        self.assertIn("STAGE141_NATIVE_FRAME_OVERFLOW_RESET_PROOF",printed.getvalue())


if __name__=="__main__":
    unittest.main()
