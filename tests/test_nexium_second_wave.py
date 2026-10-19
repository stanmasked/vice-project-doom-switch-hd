"""Strict parser fixtures; only real SD data from NeXium proves guest execution."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "second_wave",ROOT/"tools/audit_nexium_second_wave.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def sample():
    rows=(
        ("guard","stage",65,12288,0,2,5,0,0,0,0,0),
        ("wave","stage",249,106496,0,2,5,0,0,0,1,0),
        ("hostile_hit","stationary",330,118784,0,2,4,1,1,0,1,0),
        ("turret_down","stage",300,134144,0,0,5,1,0,2,1,0),
        ("exit","stage",488,225280,0,0,5,1,0,2,1,1),
    )
    return "".join(
        "VPD_ROMFREE_WAVE2_V1 "
        f"seq={i} event={event} scenario={scenario} "
        f"frame={frame} player_x={x} guard_hp={guard} "
        f"sentry_hp={hp} player_hp={player} sentry_shots={shots} "
        f"sentry_hits={hits} sentry_damage={damage} wave={wave} "
        f"clear={clear} source=guest_script original_game_proven=no\n"
        for i,(event,scenario,frame,x,guard,hp,player,shots,hits,damage,
               wave,clear) in enumerate(rows,1)
    ).encode("ascii")

class NativeSecondWaveAuditTests(unittest.TestCase):
    def test_all_realistic_milestones(self):
        self.assertEqual(m.verify(sample()),{
            "spawn_frame":249,"hostile_hit_frame":330,
            "turret_defeat_frame":300,"exit_frame":488
        })
    def test_corruption_or_forged_native_source_fails(self):
        ok=sample()
        lines=ok.splitlines(keepends=True)
        cases=[
            b"",ok[:-1],lines[0],ok+lines[-1],ok+ok,
            b"".join(reversed(lines)),
            ok.replace(b"seq=1",b"seq=01",1),
            ok.replace(b"event=exit",b"event=wave"),
            ok.replace(b"source=guest_script",b"source=host",1),
            ok.replace(b"scenario=stationary",b"scenario=stage"),
            ok.replace(b"player_hp=4",b"player_hp=5"),
            ok.replace(b"sentry_hits=1",b"sentry_hits=0"),
            ok.replace(b"sentry_hp=0",b"sentry_hp=1"),
            ok.replace(b"sentry_damage=2",b"sentry_damage=1"),
            ok.replace(b"clear=1",b"clear=0"),
            ok.replace(b"guard_hp=0",b"guard_hp=1",1),
            ok.replace(b"frame=488",b"frame=300"),
            ok.replace(b"player_x=225280",b"player_x=10000"),
            ok.replace(b"original_game_proven=no",
                       b"original_game_proven=yes",1),
            ok.replace(b"\n",b"\r\n"),
            ok.replace(b"\n",b"\x00\n")
        ]
        for i,bad in enumerate(cases):
            with self.subTest(i=i),self.assertRaises(
                (ValueError,UnicodeError)
            ):
                m.verify(bad)
    def test_independent_guest_prerequisites_required(self):
        with tempfile.TemporaryDirectory() as name:
            base=Path(name)
            (base/"guest-second-wave-witness.txt").write_bytes(sample())
            with self.assertRaisesRegex(ValueError,"independent"):
                m.audit(base)
            for f,mark in (
                ("manual-result.txt","VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
                ("dash-result.txt","VPD_NEXIUM_GUEST_DASH_PASS "),
                ("guard-result.txt","VPD_NEXIUM_GUARD_PATROL_PASS "),
                ("guard-live-defeat-result.txt",
                 "VPD_NEXIUM_GUARD_LIVE_DEFEAT_PASS "),
                ("guard-live-raster-result.txt",
                 "VPD_NEXIUM_GUARD_LIVE_RASTER_PASS "),
                ("native-exit-result.txt","VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
            ):
                (base/f).write_text(mark+"ok\n",encoding="ascii")
            m.audit(base)
            self.assertIn("VPD_NEXIUM_SECOND_WAVE_SCRIPT_PASS",
                          (base/"second-wave-result.txt").read_text())
            (base/"native-exit-result.txt").write_text("INCONCLUSIVE\n")
            with self.assertRaisesRegex(ValueError,"independent"):
                m.audit(base)

if __name__=="__main__":
    unittest.main()
