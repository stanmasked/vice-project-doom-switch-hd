#!/usr/bin/env python3
"""Adversarial source + 1280x720 native X11 HP2 raster verification tests."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_nexium_hd_low_health import source_witness, hp2_warning, verify_phase

WIDTH, HEIGHT = 1280, 720
BEFORE = {"contact_frame":113, "death_frame":241}
PHASE = (b"VPD_HD_LOW_HEALTH_PHASE_V1 third_frame=177 frame=192 "
         b"hero_hp=2 guard_attacks=3 input=idle hd=on pulse=on "
         b"source=libnx_tick original_game_proven=no\n")
VALID = (b"VPD_HD_LOW_HEALTH_GUEST_V1 contact_frame=113 frame=177 "
         b"hero_hp_before=3 hero_hp_after=2 "
         b"guard_attacks_before=2 guard_attacks_after=3 "
         b"input=idle hd=on guard_hp=3 wave=0 clear=0 "
         b"source=libnx_tick original_game_proven=no\n")

def block(img,x0,x1,y0,y1,rgb):
    ink=bytes(rgb)
    for y in range(y0,y1):
        for x in range(x0,x1):
            p=(y*WIDTH+x)*3
            img[p:p+3]=ink

def frame(hp=2, warning=True, flicker=False):
    img=bytearray(WIDTH*HEIGHT*3)
    for left,right in ((757,766),(771,781),(786,795),(800,810),(814,824)):
        n = ((757,771,786,800,814)).index(left)
        block(img,left,right+1,17,29,
              (255,220,153) if n<hp and flicker else
              ((106,198,174) if n<hp else (55,64,79)))
    if warning:
        block(img,757,836,34,37,(237,115,112))
        block(img,846,856,17,25,(255,171,147))
    return img

class SourceTest(unittest.TestCase):
    def test_native_event_tied_to_real_first_contact_and_death(self):
        self.assertEqual(source_witness(VALID,BEFORE),(113,177))

    def test_reject_fake_frames_hp_or_controls(self):
        for old,new in (
            (b"contact_frame=113",b"contact_frame=112"),
            (b"frame=177",b"frame=178"),
            (b"hero_hp_after=2",b"hero_hp_after=3"),
            (b"guard_attacks_after=3",b"guard_attacks_after=2"),
            (b"input=idle",b"input=right"),
            (b"hd=on",b"hd=off"),
            (b"guard_hp=3",b"guard_hp=0"),
            (b"source=libnx_tick",b"source=host"),
        ):
            with self.subTest(new=new),self.assertRaises(ValueError):
                source_witness(VALID.replace(old,new),BEFORE)

    def test_native_warning_on_half_cycle(self):
        self.assertEqual(verify_phase(PHASE,177),192)
        for before,after in (
            (b"third_frame=177",b"third_frame=176"),
            (b"frame=192",b"frame=193"),
            (b"frame=192",b"frame=216"),
            (b"pulse=on",b"pulse=off"),
            (b"hero_hp=2",b"hero_hp=1"),
        ):
            with self.subTest(after=after),self.assertRaises(ValueError):
                verify_phase(PHASE.replace(before,after),177)
        with self.assertRaises(ValueError):
            verify_phase(PHASE*2,177)

    def test_reject_second_session_or_early_death(self):
        with self.assertRaises(ValueError):
            source_witness(VALID,{"contact_frame":115,"death_frame":243})
        with self.assertRaises(ValueError):
            source_witness(VALID,{"contact_frame":113,"death_frame":209})

    def test_reject_duplicates_and_truncated_source(self):
        for raw in (VALID*2,VALID[:-1],b"",b"\xff"):
            with self.subTest(raw=raw[:10]),self.assertRaises(ValueError):
                source_witness(raw,BEFORE)

class RasterTest(unittest.TestCase):
    def test_native_hp2_with_both_warning_elements(self):
        self.assertEqual(hp2_warning(frame()),(True,237,80))
        self.assertEqual(hp2_warning(frame(flicker=True)),(True,237,80))

    def test_reject_only_text_or_only_warning_line(self):
        img=frame()
        block(img,757,836,34,37,(0,0,0))
        active,underline,label=hp2_warning(img)
        self.assertTrue(active)
        self.assertEqual((underline,label),(0,80))
        img=frame()
        block(img,846,856,17,25,(0,0,0))
        active,underline,label=hp2_warning(img)
        self.assertEqual((underline,label),(237,0))

    def test_reject_hud_only_or_nonmatching_hp(self):
        for hp in (0,1,3,4,5):
            with self.subTest(hp=hp):
                self.assertFalse(hp2_warning(frame(hp=hp))[0])

    def test_reject_critical_warning_if_heart_missing(self):
        img=frame()
        block(img,760,765,19,27,(55,64,79))
        self.assertFalse(hp2_warning(img)[0])

    def test_reject_frame_not_real_1280x720(self):
        with self.assertRaisesRegex(ValueError,"full-resolution"):
            hp2_warning(frame()[:-3])

if __name__ == "__main__":
    unittest.main()
