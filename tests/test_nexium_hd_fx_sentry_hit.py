#!/usr/bin/env python3
"""Adversarial source-only tests: no fixture can fake a real host PNG."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_hd_fx_sentry_hit import verify, fifth_heart_loss

ON={"frame":360,"slot":0,"age":12,"x":150272,"y":57000,"hero_hp":5}

def record(**override):
    fields=dict(
        frame=400,on_frame=360,bullet_slot=0,bullet_age_before=51,
        bullet_x_before=120320,bullet_y=57000,
        hero_x=119808,hero_y=55000,
        hero_hp_before=5,hero_hp_after=4,
        shots_hit_before=0,shots_hit_after=1,
        before_hash="a"*16,after_hash="b"*16,
    )
    fields.update(override)
    return (
        f"VPD_HD_FX_SENTRY_HIT_V1 frame={fields['frame']} "
        f"on_frame={fields['on_frame']} bullet_slot={fields['bullet_slot']} "
        f"bullet_age_before={fields['bullet_age_before']} "
        f"bullet_x_before={fields['bullet_x_before']} "
        f"bullet_y={fields['bullet_y']} bullet_vx=-768 "
        f"hero_x={fields['hero_x']} hero_y={fields['hero_y']} "
        f"hero_hp_before={fields['hero_hp_before']} "
        f"hero_hp_after={fields['hero_hp_after']} "
        f"shots_hit_before={fields['shots_hit_before']} "
        f"shots_hit_after={fields['shots_hit_after']} "
        f"input=idle mode=on wave=1 guard_hp=0 sentry_hp=2 "
        f"bullet_consumed=yes simulation_before={fields['before_hash']} "
        f"simulation_after={fields['after_hash']} "
        f"source=libnx_tick collision=swept original_game_proven=no\n"
    ).encode("ascii")

class RealSentryHitTest(unittest.TestCase):
    def test_real_moving_source_bullet_hits_authored_hitbox(self):
        v=verify(record(),ON)
        self.assertEqual(v["hero_hp_after"],4)
        self.assertEqual(v["frame"],400)
    def test_reject_fabricated_or_unrelated_damage(self):
        bad=[
            ("no hp decrease",{"hero_hp_after":5}),
            ("damage twice",{"hero_hp_after":3}),
            ("wrong guest on frame",{"on_frame":359}),
            ("different bullet",{"bullet_slot":1}),
            ("too fast bullet",{"bullet_x_before":120319}),
            ("age mismatch",{"bullet_age_before":50}),
            ("early hit",{"frame":359}),
            ("too late hit",{"frame":500}),
            ("wrong player position",{"hero_x":90000}),
            ("missed vertical collision",{"hero_y":20000}),
            ("altered hit counter",{"shots_hit_after":0}),
            ("non-first hit",{"shots_hit_before":1,"shots_hit_after":2}),
            ("no source change",{"after_hash":"a"*16}),
        ]
        for name,change in bad:
            with self.subTest(name=name),self.assertRaises(ValueError):
                verify(record(**change),ON)
        for replacement in [
            (b"source=libnx_tick",b"source=host_keyboard"),
            (b"input=idle",b"input=right"),
            (b"bullet_consumed=yes",b"bullet_consumed=no"),
            (b"collision=swept",b"collision=synthetic"),
        ]:
            with self.subTest(text=replacement[1]),self.assertRaises(ValueError):
                verify(record().replace(*replacement),ON)
        with self.assertRaises(ValueError):
            verify(record()[:-1],ON)
        with self.assertRaises(ValueError):
            verify(record()+record(),ON)

class FifthHeartX11Test(unittest.TestCase):
    """Synthetic 1280x720 X11 bars: force exact health colors/viewport shift."""
    @staticmethod
    def pair(*,no_hit=False,other_lost=False,flash_only=False):
        before=bytearray(1280*720*3)
        after=bytearray(before)
        teal=bytes((106,198,174))
        yellow=bytes((255,220,153))
        grey=bytes((55,64,79))
        # Observed X11 shift/scale from renderer HUD rectangles:
        # 757..766, 771..781, 786..795, 800..810, 814..824.
        for n,(left,right) in enumerate(
            ((757,766),(771,781),(786,795),(800,810),(814,824))):
            for y in range(17,29):
                for x in range(left,right+1):
                    ix=(y*1280+x)*3
                    before[ix:ix+3]=teal
                    after[ix:ix+3]=(
                        teal if no_hit else
                        grey if (n==4 and not flash_only) or
                                (other_lost and n==2) else yellow)
        return bytes(before),bytes(after)

    def test_one_actual_empty_segment_and_four_survive(self):
        before,after=self.pair()
        self.assertEqual(fifth_heart_loss(before,after),132)

    def test_reject_damage_flash_without_hp_loss(self):
        before,after=self.pair(flash_only=True)
        with self.assertRaises(ValueError):
            fifth_heart_loss(before,after)

    def test_reject_missing_fifth_heart_loss(self):
        before,after=self.pair(no_hit=True)
        with self.assertRaises(ValueError):
            fifth_heart_loss(before,after)

    def test_reject_other_lost_heart(self):
        before,after=self.pair(other_lost=True)
        # A second lost heart must be rejected by the four-kept condition.
        with self.assertRaises(ValueError):
            fifth_heart_loss(before,after)

    def test_reject_single_empty_pixel_in_another_heart(self):
        # Old aggregate 440-pixel guard would accept 503 remaining
        # pixels and miss this partial second-cell damage.
        before,after=self.pair()
        after=bytearray(after)
        x,y=775,22  # second heart, disjoint from the lost fifth
        ix=(y*1280+x)*3
        after[ix:ix+3]=bytes((55,64,79))
        with self.assertRaisesRegex(ValueError,"remaining heart 2"):
            fifth_heart_loss(before,bytes(after))

    def test_accept_four_healthy_hearts_without_flash(self):
        # Flash is permitted, not required: unflashed cells remain teal.
        before,after=self.pair()
        after=bytearray(after)
        for left,right in ((757,766),(771,781),(786,795),(800,810)):
            for y in range(17,29):
                for x in range(left,right+1):
                    ix=(y*1280+x)*3
                    after[ix:ix+3]=bytes((106,198,174))
        self.assertEqual(fifth_heart_loss(before,bytes(after)),132)

    def test_reject_incomplete_image(self):
        before,after=self.pair()
        with self.assertRaises(ValueError):
            fifth_heart_loss(before[:400],after)

if __name__=="__main__":
    unittest.main()
