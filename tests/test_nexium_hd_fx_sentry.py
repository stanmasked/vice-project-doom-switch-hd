#!/usr/bin/env python3
"""Adversarial parser tests for source-owned second-wave L+R proof."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_hd_fx_sentry import verify

def record(seq,frame,age,x,*,slot=0,shots=1,hero=5,
           scene_other="1"*16,scene_actual="2"*16,
           sim_before="3"*16,sim_after="3"*16):
    mode="off" if seq==1 else "on"
    return (
        f"VPD_HD_FX_SENTRY_V1 seq={seq} mode={mode} frame={frame} "
        f"manual=1 l=1 r=1 edge=1 "
        f"guard_hp=0 wave=1 sentry_hp=2 hero_hp={hero} "
        f"bullet_slot={slot} bullet_age={age} bullet_x={x} bullet_y=57000 "
        f"bullet_vx=-768 sentry_shots={shots} stage_clear=0 "
        f"scene_other={scene_other} scene_displayed={scene_actual} "
        f"roi_pixels=414000 simulation_before={sim_before} "
        f"simulation_after={sim_after} "
        f"source=libnx_pad same_frame=yes\n"
    )
def payload(**changes):
    a=dict(seq=1,frame=302,age=2,x=158464)
    b=dict(seq=2,frame=308,age=8,x=153856)
    a.update(changes.get("off",{}))
    b.update(changes.get("on",{}))
    return (record(**a)+record(**b)).encode("ascii")

class SentryShoulderTest(unittest.TestCase):
    def test_real_moving_bullet(self):
        events=verify(payload())
        self.assertEqual([e["frame"] for e in events],[302,308])
        self.assertEqual([e["age"] for e in events],[2,8])
    def test_reject_fabrication_and_wrong_order(self):
        mutations=[
            ("missing second", {"on": {"frame":302,"age":2,"x":158464}}),
            ("different slot", {"on":{"slot":1}}),
            ("another sentry shot", {"on":{"shots":2}}),
            ("player was hit", {"on":{"hero":4}}),
            ("bullet teleported", {"on":{"x":153857}}),
            ("incorrect age", {"on":{"age":7}}),
            ("same frame", {"on":{"frame":302}}),
            ("negative timeline", {"on":{"frame":300}}),
            ("scene hud only", {"off":{"scene_actual":"1"*16}}),
            ("mutated gameplay", {"on":{"sim_after":"9"*16}}),
            ("projectile expired", {"on":{"age":90}}),
        ]
        for title,options in mutations:
            with self.subTest(title=title),self.assertRaises(ValueError):
                verify(payload(**options))
        with self.assertRaises(ValueError):
            verify(payload().replace(b"source=libnx_pad",b"source=host_keyboard"))
        with self.assertRaises(ValueError):
            verify(payload()+b"EXTRA\n")
        with self.assertRaises(ValueError):
            verify(payload()[:-1])

if __name__=="__main__":
    unittest.main()
