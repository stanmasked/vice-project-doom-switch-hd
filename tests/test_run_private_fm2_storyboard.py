"""ROM-free negative and positive planning tests for private FCEUX runner."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from run_private_fm2_storyboard import private_target,capture_plan

class RunnerPlanningTests(unittest.TestCase):
    def test_us_length_requires_24_reliable_samples(self):
        movie={"frames":43652,"rom_identity_matched":True,
               "starts_from_power_on":True}
        self.assertEqual(capture_plan(movie)["sample_count"],24)
        self.assertEqual(capture_plan(movie)["last_frame"],43651)

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

    def test_reject_checkout_directory(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            (base/".git").mkdir()
            with self.assertRaisesRegex(ValueError,"Git checkout"):
                private_target(base/"captures")

if __name__=="__main__":unittest.main()
