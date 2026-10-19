"""Parser mutation fixtures are NOT evidence of native NeXium gameplay."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "wave2_live",ROOT/"tools/audit_nexium_second_wave_live.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def sample():
    fixtures=(
        ("wave",249,106496,4,2,0,0,6,0,1,1,1),
        ("fire",250,107008,4,2,0,0,7,0,1,1,1),
        ("hit1",330,150016,3,1,1,2,15,0,1,1,1),
        ("defeat",342,159232,3,0,2,2,16,0,1,1,1),
        ("exit",481,225280,2,0,2,3,29,1,1,1,1),
    )
    return "".join(
        "VPD_ROMFREE_WAVE2_LIVE_V1 "
        f"seq={i} event={event} frame={frame} player_x={x} "
        f"hero_hp={hero} turret_hp={hp} turret_hits={hits} "
        f"turret_shots={turret_shots} hero_shots={hero_shots} "
        f"wave={wave} clear={clear} input_right={right} "
        f"input_fire={fire} source=live_guest original_game_proven=no\n"
        for i,(event,frame,x,hero,hp,hits,turret_shots,hero_shots,
               clear,wave,right,fire) in enumerate(fixtures,1)
    ).encode("ascii")

class NativeWave2InputAuditTest(unittest.TestCase):
    def test_five_source_ordered_events(self):
        self.assertEqual(m.verify(sample()),{
            "wave_frame":249,"fire_frame":250,"hit_frame":330,
            "defeat_frame":342,"exit_frame":481})
    def test_forged_transitions_fail(self):
        original=sample()
        lines=original.splitlines(keepends=True)
        cases=[
            b"",original[:-1],lines[0],original+original,
            b"".join(reversed(lines)),
            original.replace(b"seq=1",b"seq=01",1),
            original.replace(b"event=exit",b"event=fire"),
            original.replace(b"turret_hp=0 turret_hits=2",
                             b"turret_hp=1 turret_hits=2"),
            original.replace(b"turret_hp=1 turret_hits=1",
                             b"turret_hp=2 turret_hits=1"),
            original.replace(b"clear=1",b"clear=0"),
            original.replace(b"input_fire=1",b"input_fire=0",1),
            original.replace(b"input_right=1",b"input_right=0",1),
            original.replace(b"hero_hp=3",b"hero_hp=0",1),
            original.replace(b"frame=342",b"frame=330"),
            original.replace(b"frame=481",b"frame=341"),
            original.replace(b"player_x=225280",b"player_x=9999"),
            original.replace(b"source=live_guest",b"source=guest_script",1),
            original.replace(b"original_game_proven=no",
                             b"original_game_proven=yes",1),
            original.replace(b"\n",b"\r\n"),
            original.replace(b"\n",b"\x00\n"),
        ]
        for n,modified in enumerate(cases):
            with self.subTest(n=n),self.assertRaises(
                (ValueError,UnicodeError)
            ):
                m.verify(modified)
    def test_missing_native_prerequisites_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"guest-second-wave-live-witness.txt").write_bytes(sample())
            with self.assertRaisesRegex(ValueError,"host did not"):
                m.audit(root)
            (root/"input-probe.txt").write_text(
                "host_second_wave_controls_sent=yes keys=D+Z guest_exit=yes\n")
            with self.assertRaisesRegex(ValueError,"independent"):
                m.audit(root)

if __name__=="__main__":
    unittest.main()
