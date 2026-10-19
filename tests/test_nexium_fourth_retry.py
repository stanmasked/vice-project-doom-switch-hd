"""Mutation tests for genuine fourth consecutive native manual attempt."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "fourth_retry",ROOT/"tools/audit_nexium_fourth_retry.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fixture():
    return (
        b"VPD_ROMFREE_FOURTH_RETRY_V1 seq=1 event=restart "
        b"old_frame=480 old_hp=3 old_guard_hp=0 old_sentry_hp=0 "
        b"old_clear=1 new_frame=0 new_x=12288 hero_hp=5 guard_hp=3 "
        b"sentry_hp=2 wave=0 clear=0 input_minus=1 "
        b"source=live_guest original_game_proven=no\n"
        b"VPD_ROMFREE_FOURTH_RETRY_V1 seq=2 event=move "
        b"frame=8 before_frame=7 before_x=15872 after_x=16384 "
        b"delta_fixed=512 hero_hp=5 guard_hp=3 sentry_hp=2 "
        b"guard_attacks=0 shots=0 wave=0 clear=0 input_right=1 "
        b"source=live_guest original_game_proven=no\n"
    )

class FourthRetryProofTests(unittest.TestCase):
    def test_real_fourth_retry_then_right(self):
        self.assertEqual(m.verify(fixture()),
                         {"old_frame":480,"frame":8,"after_x":16384})

    def test_wrong_reset_prior_progression_and_controls_rejected(self):
        raw=fixture()
        cases=[
            b"",raw[:-1],raw+raw,raw.replace(b"\n",b"\r\n"),
            b"".join(reversed(raw.splitlines(keepends=True))),
            raw.replace(b"seq=1",b"seq=01",1),
            raw.replace(b"event=restart",b"event=move",1),
            raw.replace(b"old_frame=480",b"old_frame=0",1),
            raw.replace(b"old_frame=480",b"old_frame=1201",1),
            raw.replace(b"old_hp=3",b"old_hp=0",1),
            raw.replace(b"old_guard_hp=0",b"old_guard_hp=1",1),
            raw.replace(b"old_sentry_hp=0",b"old_sentry_hp=1",1),
            raw.replace(b"old_clear=1",b"old_clear=0",1),
            raw.replace(b"new_frame=0",b"new_frame=1",1),
            raw.replace(b"new_x=12288",b"new_x=0",1),
            raw.replace(b"hero_hp=5",b"hero_hp=4",1),
            raw.replace(b"guard_hp=3",b"guard_hp=2",1),
            raw.replace(b"sentry_hp=2",b"sentry_hp=1",1),
            raw.replace(b"input_minus=1",b"input_minus=0",1),
            raw.replace(b"frame=8",b"frame=7",1),
            raw.replace(b"before_frame=7",b"before_frame=6",1),
            raw.replace(b"before_x=15872",b"before_x=15873",1),
            raw.replace(b"after_x=16384",b"after_x=16383",1),
            raw.replace(b"delta_fixed=512",b"delta_fixed=511",1),
            raw.replace(b"guard_attacks=0",b"guard_attacks=1",1),
            raw.replace(b"shots=0",b"shots=1",1),
            raw.replace(b"wave=0",b"wave=1",1),
            raw.replace(b"clear=0",b"clear=1",1),
            raw.replace(b"input_right=1",b"input_right=0",1),
            raw.replace(b"source=live_guest",b"source=guest_script",1),
            raw.replace(b"original_game_proven=no",
                        b"original_game_proven=yes",1),
        ]
        for i,c in enumerate(cases):
            with self.subTest(case=i),self.assertRaises((ValueError,UnicodeError)):
                m.verify(c)

    def test_fourth_reset_requires_changed_native_scene_image(self):
        # Synthetic pixels validate ONLY fail-closed parser behavior;
        # they do NOT count as real NeXium guest/runtime evidence.
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            (base/"guest-fourth-retry-witness.txt").write_bytes(fixture())
            (base/"third-stage-result.txt").write_text(
                "VPD_NEXIUM_THIRD_STAGE_PASS fixture_only=yes\n")
            (base/"guest-third-stage-witness.txt").write_bytes(
                b"VPD_ROMFREE_THIRD_STAGE_V1 seq=1 event=wave frame=250 "
                b"hero_x=107008 hero_hp=5 guard_hp=0 guard_hits=3 "
                b"sentry_hp=2 sentry_hits=0 wave=1 clear=0 "
                b"input_right=1 input_fire=0 source=live_guest "
                b"original_game_proven=no\n"
                b"VPD_ROMFREE_THIRD_STAGE_V1 seq=2 event=exit frame=470 "
                b"hero_x=225280 hero_hp=3 guard_hp=0 guard_hits=3 "
                b"sentry_hp=0 sentry_hits=2 wave=1 clear=1 "
                b"input_right=1 input_fire=1 source=live_guest "
                b"original_game_proven=no\n")
            (base/"input-probe.txt").write_text(
                "host_fourth_retry_minus_sent=yes key=N guest_restart=yes\n"
                "host_fourth_retry_right_sent=yes key=D guest_move=yes\n")
            (base/"visual-probe.txt").write_text(
                "capture=screen-live-fourth-restart\n"
                "capture=screen-live-fourth-move\n"
                "live_fourth_movement_raster_after_guest_event=yes\n")
            p6=b"P6\n1280 720\n255\n"
            raster=p6+bytes(1280*720*3)
            for name in ("screen-live-third-stage-clear",
                         "screen-live-fourth-restart",
                         "screen-live-fourth-move"):
                (base/(name+".png")).write_bytes(b"\x89PNG\r\n\x1a\n")
                (base/(name+".ppm")).write_bytes(raster)
            with self.assertRaisesRegex(ValueError,"matches completed level"):
                m.audit(base)

    def test_missing_prior_third_victory_and_real_x11_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            (base/"guest-fourth-retry-witness.txt").write_bytes(fixture())
            with self.assertRaisesRegex(ValueError,"third-stage victory"):
                m.audit(base)
            (base/"third-stage-result.txt").write_text(
                "VPD_NEXIUM_THIRD_STAGE_PASS guest=yes\n")
            # A prior PASS label alone cannot prove the fourth reset.
            with self.assertRaisesRegex(ValueError,"third-stage guest"):
                m.audit(base)
            (base/"guest-third-stage-witness.txt").write_bytes(
                b"VPD_ROMFREE_THIRD_STAGE_V1 seq=1 event=wave frame=250 "
                b"hero_x=107008 hero_hp=5 guard_hp=0 guard_hits=3 "
                b"sentry_hp=2 sentry_hits=0 wave=1 clear=0 "
                b"input_right=1 input_fire=0 source=live_guest "
                b"original_game_proven=no\n"
                b"VPD_ROMFREE_THIRD_STAGE_V1 seq=2 event=exit frame=470 "
                b"hero_x=225280 hero_hp=3 guard_hp=0 guard_hits=3 "
                b"sentry_hp=0 sentry_hits=2 wave=1 clear=1 "
                b"input_right=1 input_fire=1 source=live_guest "
                b"original_game_proven=no\n")
            with self.assertRaisesRegex(ValueError,"host key"):
                m.audit(base)
            (base/"guest-fourth-retry-witness.txt").write_bytes(
                fixture().replace(b"old_frame=480",b"old_frame=200"))
            with self.assertRaisesRegex(ValueError,"not linked"):
                m.audit(base)

if __name__=="__main__":
    unittest.main()
