#!/usr/bin/env python3
"""Adversarial parser checks; never substitute fixtures for NeXium runtime."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_hd_fx_guest import audit, verify

def line(seq,mode,frame,other,shown):
    return (
        f"VPD_HD_FX_GUEST_V1 seq={seq} mode={mode} frame={frame} "
        f"manual=1 l=1 r=1 edge=1 scene_other={other:016x} "
        f"scene_displayed={shown:016x} roi_pixels=414000 "
        "source=libnx_pad same_frame=yes\n"
    )
GOOD=(
    line(1,"off",540,0x123456789abcdef0,0x124456789abcdef0)+
    line(2,"on",548,0x124456789abcdef0,0x123456789abcdef0)
).encode("ascii")

class GuestAuditTests(unittest.TestCase):
    def test_real_native_shape(self):
        rows=verify(GOOD)
        self.assertEqual([540,548],[r[0] for r in rows])

    def test_guest_audit_requires_independent_source_and_x11_gates(self):
        # A syntactically valid guest line is never enough to pass.
        with TemporaryDirectory() as temp:
            base=Path(temp)
            proof=base/"guest-hd-fx-toggle-witness.txt"
            proof.write_bytes(GOOD)
            with self.assertRaisesRegex(ValueError,"fourth manual stage"):
                audit(base)
            (base/"fourth-stage-result.txt").write_text(
                "VPD_NEXIUM_FOURTH_STAGE_PASS exit_frame=535\\n",
                encoding="ascii")
            with self.assertRaises(OSError):
                audit(base) # no physical host input transcript
            (base/"input-probe.txt").write_text(
                "host_hd_fx_chord_sent=yes keys=Q+E expected=off guest_seen=yes\\n"
                "host_hd_fx_chord_sent=yes keys=Q+E expected=on guest_seen=yes\\n",
                encoding="ascii")
            with self.assertRaises(OSError):
                audit(base) # no X11 capture timeline
            (base/"visual-probe.txt").write_text(
                "capture=screen-live-hd-fx-off\\n"
                "capture=screen-live-hd-fx-on\\n",
                encoding="ascii")
            with self.assertRaisesRegex(ValueError,"PNG not found"):
                audit(base) # trace, input and capture markers cannot forge pixels
            (base/"fourth-stage-result.txt").write_text(
                "VPD_NEXIUM_FOURTH_STAGE_PASS exit_frame=550\\n",
                encoding="ascii")
            with self.assertRaisesRegex(ValueError,"predates completed"):
                audit(base) # reject proof recorded before stage completion

    def test_fail_closed_mutations(self):
        for data in (
            b"",GOOD[:-1],GOOD+b"extra\n",GOOD.splitlines(True)[0],
            GOOD.replace(b"seq=2",b"seq=1"),
            GOOD.replace(b"mode=on",b"mode=off"),
            GOOD.replace(b"frame=548",b"frame=540"),
            GOOD.replace(b"manual=1",b"manual=0"),
            GOOD.replace(b"l=1",b"l=0"),
            GOOD.replace(b"r=1",b"r=0"),
            GOOD.replace(b"edge=1",b"edge=0"),
            GOOD.replace(b"roi_pixels=414000",b"roi_pixels=0"),
            GOOD.replace(b"source=libnx_pad",b"source=host_fixture"),
            GOOD.replace(b"same_frame=yes",b"same_frame=no"),
            GOOD.replace(b"scene_displayed=124456789abcdef0",
                         b"scene_displayed=123456789abcdef0"),
            GOOD+b"\xff",
        ):
            with self.subTest(data=data[:90]):
                with self.assertRaises(ValueError):
                    verify(data)

if __name__=="__main__":
    unittest.main()
