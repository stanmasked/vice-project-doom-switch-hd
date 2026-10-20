#!/usr/bin/env python3
"""Adversarial source-only tests: no fixture can fake a real host PNG."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_hd_fx_sentry_hit import verify

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

if __name__=="__main__":
    unittest.main()
