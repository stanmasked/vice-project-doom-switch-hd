"""ROM-free negative and positive planning tests for private FCEUX runner."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from run_private_fm2_storyboard import private_target,capture_plan

class RunnerPlanningTests(unittest.TestCase):
    def test_real_us_capture_cadence_with_4096_frame_synthetic(self):
        invented={"frames":4096,"rom_identity_matched":True,
                  "starts_from_power_on":True}
        result=capture_plan(invented,interval=1803)
        self.assertEqual(result["interval"],1803)
        self.assertEqual(result["sample_count"],3)
        self.assertEqual(result["last_frame"],4095)

    def test_us_length_requires_25_samples_including_terminal(self):
        movie={"frames":43652,"rom_identity_matched":True,
               "starts_from_power_on":True}
        self.assertEqual(capture_plan(movie)["sample_count"],25)
        self.assertEqual(capture_plan(movie)["last_frame"],43651)

    def test_transition_window_uses_global_eight_frame_cadence(self):
        movie={"frames":43652,"rom_identity_matched":True,
               "starts_from_power_on":True}
        result=capture_plan(movie,interval=8,start_frame=3500,stop_frame=3800)
        self.assertEqual(result["start_frame"],3500)
        self.assertEqual(result["stop_frame"],3800)
        self.assertEqual(result["sample_count"],38)
        self.assertEqual(result["last_frame"],43651)

    def test_non_aligned_window_stop_is_included(self):
        movie={"frames":4096,"rom_identity_matched":True,
               "starts_from_power_on":True}
        result=capture_plan(movie,interval=16,start_frame=100,stop_frame=251)
        self.assertEqual(result["sample_count"],10)
        self.assertEqual(result["start_frame"],100)
        self.assertEqual(result["stop_frame"],251)

    def test_reject_window_outside_movie_or_reversed(self):
        movie={"frames":4096,"rom_identity_matched":True,
               "starts_from_power_on":True}
        with self.assertRaisesRegex(ValueError,"window"):
            capture_plan(movie,interval=8,start_frame=3500,stop_frame=4096)
        with self.assertRaisesRegex(ValueError,"window"):
            capture_plan(movie,interval=8,start_frame=200,stop_frame=100)

    def test_reject_too_short_movie_for_first_capture(self):
        with self.assertRaisesRegex(ValueError,"shorter"):
            capture_plan({"frames":8,"rom_identity_matched":True,
                          "starts_from_power_on":True},interval=8)

    def test_unmatched_rom_rejected(self):
        with self.assertRaisesRegex(ValueError,"identity"):
            capture_plan({"frames":64,"rom_identity_matched":False,
                          "starts_from_power_on":True})

    def test_savestate_origin_is_not_silently_assumed(self):
        with self.assertRaisesRegex(ValueError,"power-on"):
            capture_plan({"frames":64,"rom_identity_matched":True,
                          "starts_from_power_on":False})

    def test_more_than_64_images_rejected(self):
        with self.assertRaisesRegex(ValueError,"64"):
            capture_plan({"frames":999999,"rom_identity_matched":True,
                          "starts_from_power_on":True},interval=8)

    def test_reject_existing_directory(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"NEW"):
                private_target(Path(d))

    def test_new_private_directory_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(private_target(Path(d)/"capture"),Path(d)/"capture")

    def test_reject_dangling_output_symlink_before_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            linked=root/"capture-link"
            try:
                linked.symlink_to(root/"not-created",target_is_directory=True)
            except OSError as exc:
                self.skipTest(str(exc))
            with self.assertRaisesRegex(ValueError,"symlink"):
                private_target(linked)
            self.assertFalse((root/"not-created").exists())

    def test_existing_terminal_witness_does_not_create_capture_dir(self):
        from unittest.mock import patch
        from build_fceux_smoke_rom import build_rom
        from build_fceux_smoke_movie import make_movie
        from run_private_fm2_storyboard import launch
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rom=root/"synthetic.nes"
            movie=root/"synthetic.fm2"
            rom.write_bytes(build_rom())
            movie.write_text(make_movie(rom.read_bytes()),encoding="ascii")
            capture=root/"capture"
            witness=root/"capture.terminal_witness.txt"
            witness.write_text("stale",encoding="ascii")
            with patch("run_private_fm2_storyboard.shutil.which",return_value="/usr/games/fceux"):
                with self.assertRaisesRegex(ValueError,"witness"):
                    launch(rom,movie,capture,interval=8,timeout_seconds=5)
            self.assertFalse(capture.exists())
            self.assertEqual(witness.read_text(),"stale")

    def test_invalid_chr_focus_fails_before_emulator(self):
        from run_private_fm2_storyboard import parse_chr_targets
        self.assertEqual(parse_chr_targets("126,124,125,124",128),(124,125,126))
        with self.assertRaisesRegex(ValueError,"CHR"):
            parse_chr_targets("124,125,126",8)
        with self.assertRaisesRegex(ValueError,"CHR"):
            parse_chr_targets("wrong",128)

    def test_nrom_cannot_enable_mmc3_trace(self):
        from unittest.mock import patch
        from build_fceux_smoke_rom import build_rom
        from build_fceux_smoke_movie import make_movie
        from run_private_fm2_storyboard import launch
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rom=root/"invented.nes";movie=root/"invented.fm2"
            rom.write_bytes(build_rom())
            movie.write_text(make_movie(rom.read_bytes()),encoding="ascii")
            with patch("run_private_fm2_storyboard.shutil.which",return_value="/usr/games/fceux"):
                with self.assertRaisesRegex(ValueError,"Mapper 4"):
                    launch(rom,movie,root/"new",interval=8,trace_chr_banks="0")
            self.assertFalse((root/"new").exists())

    def test_private_file_integrity_stamp_changes_on_edit(self):
        from run_private_fm2_storyboard import file_sha256
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"private_synthetic.bin"
            p.write_bytes(b"invented synthetic payload A")
            initial=file_sha256(p)
            self.assertEqual(file_sha256(p),initial)
            p.write_bytes(b"invented synthetic payload B")
            self.assertNotEqual(file_sha256(p),initial)

    def test_symlink_cannot_enter_private_integrity_stamp(self):
        from run_private_fm2_storyboard import file_sha256
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"original";p.write_bytes(b"synthetic")
            alias=Path(d)/"alias"
            try:alias.symlink_to(p)
            except OSError as exc:self.skipTest(str(exc))
            with self.assertRaisesRegex(ValueError,"linked"):
                file_sha256(alias)

    def test_reject_checkout_directory(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            (base/".git").mkdir()
            with self.assertRaisesRegex(ValueError,"Git checkout"):
                private_target(base/"captures")

    def test_unexpected_fceux_exit_before_witness_is_inconclusive(self):
        from unittest.mock import patch
        from build_fceux_smoke_rom import build_rom
        from build_fceux_smoke_movie import make_movie
        from run_private_fm2_storyboard import launch
        class ExitedProcess:
            def poll(self): return 1
            def terminate(self): raise AssertionError("already exited")
            def wait(self,timeout=None): return 1
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rom=root/"synthetic.nes"; movie=root/"synthetic.fm2"
            rom.write_bytes(build_rom())
            movie.write_text(make_movie(rom.read_bytes()),encoding="ascii")
            output=root/"capture"
            with patch("run_private_fm2_storyboard.shutil.which",return_value="/usr/games/fceux"), \
                 patch("run_private_fm2_storyboard.subprocess.Popen",return_value=ExitedProcess()):
                with self.assertRaisesRegex(ValueError,"exited before terminal"):
                    launch(rom,movie,output,interval=8,timeout_seconds=5)
            self.assertTrue(output.is_dir())
            self.assertTrue((root/"capture.fceux.log").is_file())
            self.assertFalse((root/"capture.terminal_witness.txt").exists())

    def test_terminal_witness_cannot_hide_incomplete_storyboard(self):
        from unittest.mock import patch
        from audit_private_fceux_storyboard import P6_HEADER,PAL_SIZE
        from build_fceux_smoke_rom import build_rom
        from build_fceux_smoke_movie import make_movie
        from run_private_fm2_storyboard import launch
        class RunningProcess:
            def __init__(self): self.stopped=False
            def poll(self): return 0 if self.stopped else None
            def terminate(self): self.stopped=True
            def wait(self,timeout=None): return 0
            def kill(self): self.stopped=True
        def capture_one_frame(root):
            (root/"frame_000008.ppm").write_bytes(P6_HEADER+bytes([1,2,3])*PAL_SIZE)
            (root/"frame_000008.pal.bin").write_bytes(bytes([16])*PAL_SIZE)
            (root/"frame_000008.meta.txt").write_text("\n".join([
                "format=private_fceux_storyboard_v1","frame=8","rom_md5="+"a"*32,
                "interval=8","start_frame=8","stop_frame=63","capture_limit=8",
                "invalid_palette_values=0","screen_size=256x240",
                "source=emu.getscreenpixel",""]),encoding="ascii")
        def fake_popen(command,env,stdout,stderr):
            witness=Path(env["VPD_PRIVATE_WITNESS"])
            witness.write_text("\n".join([
                "format=private_fm2_terminal_witness_v4","movie_readonly=yes",
                "movie_terminal_frame=63","movie_frame_count=64",
                "movie_first_observed_frame=1","movie_last_observed_frame=63",
                "movie_consecutive_unique_frames=63","movie_frame_gaps=0",
                "movie_active_before_terminal=yes","movie_mode_at_terminal=finished",
                "loaded_rom_verified=yes","fm2_header_power_on_preflight_verified=yes",
                "original_stage_proven=no","game_completion_proven=no",""]),
                encoding="ascii")
            capture_one_frame(Path(env["VPD_PRIVATE_OUTPUT_DIR"]))
            return RunningProcess()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rom=root/"synthetic.nes"; movie=root/"synthetic.fm2"
            rom.write_bytes(build_rom())
            movie.write_text(make_movie(rom.read_bytes()),encoding="ascii")
            with patch("run_private_fm2_storyboard.shutil.which",return_value="/usr/games/fceux"), \
                 patch("run_private_fm2_storyboard.subprocess.Popen",side_effect=fake_popen):
                with self.assertRaisesRegex(ValueError,"window incomplete"):
                    launch(rom,movie,root/"capture",interval=8,timeout_seconds=5)
            self.assertTrue((root/"capture.terminal_witness.txt").is_file())
            self.assertTrue((root/"capture"/"frame_000008.meta.txt").is_file())

    def test_timeout_without_terminal_witness_is_inconclusive(self):
        from unittest.mock import patch
        from build_fceux_smoke_rom import build_rom
        from build_fceux_smoke_movie import make_movie
        from run_private_fm2_storyboard import launch
        class StalledProcess:
            def __init__(self): self.stopped=False
            def poll(self): return 0 if self.stopped else None
            def terminate(self): self.stopped=True
            def wait(self,timeout=None): return 0
            def kill(self): self.stopped=True
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rom=root/"synthetic.nes"; movie=root/"synthetic.fm2"
            rom.write_bytes(build_rom())
            movie.write_text(make_movie(rom.read_bytes()),encoding="ascii")
            with patch("run_private_fm2_storyboard.shutil.which",return_value="/usr/games/fceux"), \
                 patch("run_private_fm2_storyboard.subprocess.Popen",return_value=StalledProcess()), \
                 patch("run_private_fm2_storyboard.time.monotonic",side_effect=[0.0,0.0,2.0]), \
                 patch("run_private_fm2_storyboard.time.sleep",return_value=None):
                with self.assertRaisesRegex(ValueError,"watchdog"):
                    launch(rom,movie,root/"capture",interval=8,timeout_seconds=1)

if __name__=="__main__":unittest.main()
