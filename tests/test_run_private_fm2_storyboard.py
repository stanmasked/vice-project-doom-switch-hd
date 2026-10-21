"""ROM-free negative and positive planning tests for private FCEUX runner."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from run_private_fm2_storyboard import private_target,capture_plan

class RunnerPlanningTests(unittest.TestCase):
    def test_us_length_requires_25_samples(self):
        movie={"frames":43652,"rom_identity_matched":True,
               "starts_from_power_on":True}
        self.assertEqual(capture_plan(movie)["sample_count"],25)
        self.assertEqual(capture_plan(movie)["last_frame"],43651)

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

    def test_reject_checkout_directory(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            (base/".git").mkdir()
            with self.assertRaisesRegex(ValueError,"Git checkout"):
                private_target(base/"captures")

if __name__=="__main__":unittest.main()
