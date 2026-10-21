"""ROM-free fabricated FCEUX capture preflight and mutation rejection."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_fceux_capture import audit_directory


ROM="f"*32


def capture(root,frame,*,screen=True,dropped=0,md5=ROM,interval=120,limit=24):
    prefix=root/f"frame_{frame:06d}"
    (root/(prefix.name+".ppu.bin")).write_bytes(bytes(16384))
    (root/(prefix.name+".ram.bin")).write_bytes(bytes(2048))
    if screen:
        (root/(prefix.name+".screen.rgb.bin")).write_bytes(bytes(256*240*3))
        (root/(prefix.name+".screen.pal.bin")).write_bytes(bytes([254])+bytes(256*240-1))
    m={
        "format":"fceux_ppu_snapshot_v4",
        "cycle_trace_available":"no",
        "cycle_trace_counter_epoch":"debugger_since_reset",
        "rom_md5":md5,
        "frame":str(frame),
        "capture_interval":str(interval),
        "capture_limit":str(limit),
        "logged_register_writes":str(frame+33),
        "dropped_register_writes":str(dropped),
        "register_log_complete":"no" if dropped else "yes",
        "screen_reference":"yes" if screen else "no",
        "screen_size":"256x240",
        "invalid_screen_palette_values":"1" if screen else "0",
    }
    path=root/(prefix.name+".meta.txt")
    path.write_text("".join(f"{k}={v}\n" for k,v in m.items()),encoding="utf8")
    return path


def replace_meta(path,old,new):
    s=path.read_text(encoding="utf8")
    assert old in s
    path.write_text(s.replace(old,new),encoding="utf8")


class PrivatePreflightTests(unittest.TestCase):
    def test_private_complete_two_frame_session(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"private"
            root.mkdir()
            capture(root,120)
            capture(root,240)
            r=audit_directory(root)
            self.assertEqual((r["capture_count"],r["first_frame"],r["last_frame"]),
                             (2,120,240))
            self.assertTrue(r["all_register_logs_complete"])
            self.assertFalse(r["private_capture_authenticity_proven"])
            self.assertFalse(r["actual_first_stage_proven"])
            self.assertFalse(r["camera_scroll_measured"])
            self.assertFalse(r["first_stage_geometry_recovered"])
            self.assertNotIn(ROM,str(r))
            self.assertNotIn("frame_000120",str(r))

    def test_private_without_optional_screen(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,screen=False)
            result=audit_directory(root)
            self.assertFalse(result["screen_reference"])

    def test_reject_original_rom_identity_mixture(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120)
            capture(root,240,md5="a"*32)
            with self.assertRaisesRegex(ValueError,"ROM identities"):
                audit_directory(root)

    def test_reject_dropped_writes_by_default_and_label_override(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,dropped=1)
            with self.assertRaisesRegex(ValueError,"incomplete register logs"):
                audit_directory(root)
            result=audit_directory(root,allow_incomplete=True)
            self.assertFalse(result["all_register_logs_complete"])
            self.assertEqual(result["incomplete_frame_count"],1)

    def test_reject_contradictory_completeness(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=capture(root,120,dropped=1)
            replace_meta(p,"register_log_complete=no","register_log_complete=yes")
            with self.assertRaisesRegex(ValueError,"contradictory"):
                audit_directory(root)

    def test_reject_missing_and_short_binary_capture(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,screen=False)
            ram=root/"frame_000120.ram.bin"
            ram.write_bytes(b"x"*2047)
            with self.assertRaisesRegex(ValueError,"bad length"):
                audit_directory(root)
            ram.unlink()
            with self.assertRaisesRegex(ValueError,"missing"):
                audit_directory(root)

    def test_reject_wrong_palette_index(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120)
            pal=root/"frame_000120.screen.pal.bin"
            s=bytearray(pal.read_bytes())
            s[5]=128
            pal.write_bytes(s)
            with self.assertRaisesRegex(ValueError,"invalid NES palette"):
                audit_directory(root)

    def test_reject_wrong_palette_unavailable_count(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=capture(root,120)
            replace_meta(p,"invalid_screen_palette_values=1",
                         "invalid_screen_palette_values=0")
            with self.assertRaisesRegex(ValueError,"count mismatch"):
                audit_directory(root)

    def test_reject_wrong_frame_metadata_and_cadence(self):
        for before,after,message in (
            ("frame=120","frame=121","frame/metadata"),
            ("capture_interval=120","capture_interval=119","interval"),
        ):
            with self.subTest(after=after),tempfile.TemporaryDirectory() as d:
                root=Path(d)
                p=capture(root,120,screen=False)
                replace_meta(p,before,after)
                with self.assertRaisesRegex(ValueError,message):
                    audit_directory(root)

    def test_reject_duplicate_metadata_keys(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=capture(root,120)
            p.write_text(p.read_text()+"rom_md5="+"a"*32+"\n")
            with self.assertRaisesRegex(ValueError,"duplicate metadata"):
                audit_directory(root)

    def test_reject_orphan_frame_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120)
            (root/"frame_000360.ppu.bin").write_bytes(bytes(16384))
            with self.assertRaisesRegex(ValueError,"orphan"):
                audit_directory(root)

    def test_reject_missing_screen_file_when_expected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120)
            (root/"frame_000120.screen.rgb.bin").unlink()
            with self.assertRaisesRegex(ValueError,"missing"):
                audit_directory(root)

    def test_reject_leftover_screen_file_when_capture_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,screen=False)
            (root/"frame_000120.screen.rgb.bin").write_bytes(bytes(256*240*3))
            with self.assertRaisesRegex(ValueError,"orphan"):
                audit_directory(root)

    def test_reject_inconsistent_metadata_over_two_frames(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,screen=True,interval=120)
            capture(root,240,screen=False,interval=120)
            with self.assertRaisesRegex(ValueError,"mixed screen"):
                audit_directory(root)

    def test_reject_capture_cadence_change_mid_session(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,screen=False,interval=120)
            capture(root,240,screen=False,interval=80)
            with self.assertRaisesRegex(ValueError,"cadence"):
                audit_directory(root)

    def test_reject_cumulative_counter_regression(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            a=capture(root,120,screen=False)
            b=capture(root,240,screen=False)
            replace_meta(b,"logged_register_writes=273","logged_register_writes=100")
            with self.assertRaisesRegex(ValueError,"decreased"):
                audit_directory(root)

    def test_reject_cumulative_dropped_counter_regression(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,screen=False,dropped=3)
            capture(root,240,screen=False,dropped=1)
            with self.assertRaisesRegex(ValueError,"dropped-register counter decreased"):
                audit_directory(root,allow_incomplete=True)

    def test_reject_disabled_screen_with_nonzero_invalid_palette_count(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=capture(root,120,screen=False)
            replace_meta(p,"invalid_screen_palette_values=0",
                         "invalid_screen_palette_values=1")
            with self.assertRaisesRegex(ValueError,"screen capture disabled"):
                audit_directory(root)

    def test_no_metadata_and_nonstandard_filename(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaisesRegex(ValueError,"1..512"):
                audit_directory(root)
            p=capture(root,120,screen=False)
            p.rename(root/"frame_name.meta.txt")
            with self.assertRaisesRegex(ValueError,"not frame_NUMBER"):
                audit_directory(root)


if __name__=="__main__":
    unittest.main()
