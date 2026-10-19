"""Host-side negative fixtures; never substitute for a live NeXium run."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "third_run_audit",ROOT/"tools/audit_nexium_third_run_control.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def sample():
    return (
        b"VPD_ROMFREE_THIRD_RUN_V1 event=move frame=20 before_frame=19 "
        b"before_x=16384 after_x=16896 delta_fixed=512 hero_hp=5 "
        b"guard_hp=3 guard_attacks=0 sentry_hp=2 shots=0 dash=0 "
        b"wave=0 clear=0 input_right=1 source=live_guest "
        b"original_game_proven=no\n"
    )

class ThirdRunControlTests(unittest.TestCase):
    def test_accept_exact_native_source_movement(self):
        self.assertEqual(m.verify(sample()),
                         {"frame":20,"after_x":16896,"delta":512})

    def test_reject_forged_input_deltas_and_reset_state(self):
        raw=sample()
        cases=[
            b"", raw[:-1], raw+raw, raw.replace(b"\n",b"\r\n"),
            raw.replace(b"frame=20",b"frame=0",1),
            raw.replace(b"frame=20",b"frame=101",1),
            raw.replace(b"before_frame=19",b"before_frame=18",1),
            raw.replace(b"before_x=16384",b"before_x=16383",1),
            raw.replace(b"after_x=16896",b"after_x=16895",1),
            raw.replace(b"delta_fixed=512",b"delta_fixed=0",1),
            raw.replace(b"hero_hp=5",b"hero_hp=4",1),
            raw.replace(b"guard_hp=3",b"guard_hp=2",1),
            raw.replace(b"guard_attacks=0",b"guard_attacks=1",1),
            raw.replace(b"sentry_hp=2",b"sentry_hp=0",1),
            raw.replace(b"shots=0",b"shots=1",1),
            raw.replace(b"dash=0",b"dash=1",1),
            raw.replace(b"wave=0",b"wave=1",1),
            raw.replace(b"clear=0",b"clear=1",1),
            raw.replace(b"input_right=1",b"input_right=0",1),
            raw.replace(b"source=live_guest",b"source=guest_script",1),
            raw.replace(b"original_game_proven=no",
                        b"original_game_proven=yes",1),
        ]
        for i,case in enumerate(cases):
            with self.subTest(i=i),self.assertRaises((ValueError,UnicodeError)):
                m.verify(case)

    def test_requires_real_guest_host_previous_proofs_and_frames(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)
            (out/"guest-post-defeat-control-witness.txt").write_bytes(sample())
            with self.assertRaisesRegex(ValueError,"controller"):
                m.audit(out)
            (out/"input-probe.txt").write_text(
                "host_defeat_retry_guest_observed=yes\n"
                "host_third_run_control_sent=yes key=D guest_observed=yes\n",
                encoding="ascii")
            with self.assertRaisesRegex(ValueError,"prior required"):
                m.audit(out)

if __name__=="__main__":
    unittest.main()
