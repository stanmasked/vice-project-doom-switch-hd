"""Wholly original FM2 fixture: do not use user ROM or movie."""
import base64
import hashlib
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from build_fceux_smoke_rom import build_rom
from build_fceux_smoke_movie import make_movie,MOVIE_FRAMES

class SyntheticMovieTests(unittest.TestCase):
    def test_rom_identity_matches_payload_md5(self):
        rom=build_rom()
        movie=make_movie(rom)
        checksum=next(x.split("base64:",1)[1] for x in movie.splitlines()
                      if x.startswith("romChecksum "))
        self.assertEqual(base64.b64decode(checksum),hashlib.md5(rom[16:]).digest())
        self.assertNotEqual(base64.b64decode(checksum),hashlib.md5(rom).digest())

    def test_64_frames_and_single_controller(self):
        txt=make_movie(build_rom())
        frames=[line for line in txt.splitlines() if line.startswith("|")]
        self.assertEqual(len(frames),MOVIE_FRAMES)
        self.assertEqual(sum(x=="|0|.......A|||" for x in frames),12)
        self.assertTrue(all(len(x.split("|"))==6 and x.endswith("|||") for x in frames))
        self.assertIn("port1 0",txt)
        self.assertIn("guid ",txt)

    def test_mmc3_nes2_fm2_checksum_valid(self):
        from build_fceux_smoke_mmc3_nes2 import build_rom as mmc3_rom
        rom=mmc3_rom()
        payload=make_movie(rom)
        checksum=next(x.split("base64:",1)[1] for x in payload.splitlines()
                      if x.startswith("romChecksum "))
        self.assertEqual(base64.b64decode(checksum),hashlib.md5(rom[16:]).digest())
        self.assertEqual(sum(x.startswith("|") for x in payload.splitlines()),64)

    def test_same_sized_mutated_rom_refused(self):
        modified=bytearray(build_rom())
        modified[16]=modified[16]^1
        with self.assertRaisesRegex(ValueError,"synthetic ROM"):
            make_movie(modified)

    def test_256_frame_extended_movie(self):
        from build_fceux_smoke_mmc3_nes2 import build_rom as mmc3_rom
        lines=make_movie(mmc3_rom(),frames=256).splitlines()
        self.assertEqual(sum(x.startswith("|") for x in lines),256)
        self.assertEqual(sum(x=="|0|.......A|||" for x in lines),12)

    def test_4096_frame_long_synthetic_movie_uses_same_rom_digest(self):
        from build_fceux_smoke_mmc3_nes2 import build_rom as mmc3_rom
        payload=make_movie(mmc3_rom(),frames=4096)
        self.assertEqual(sum(line.startswith("|") for line in payload.splitlines()),4096)
        self.assertIn("romChecksum base64:",payload)
        self.assertEqual(sum(line=="|0|.......A|||" for line in payload.splitlines()),12)

    def test_invalid_extended_movie_bounds(self):
        for count in (0,31,4097,64.5,True):
            with self.subTest(count=count):
                with self.assertRaisesRegex(ValueError,"frame count"):
                    make_movie(build_rom(),frames=count)

    def test_mismatched_source_refused(self):
        with self.assertRaisesRegex(ValueError,"synthetic ROM"):
            make_movie(build_rom()[:-1])

if __name__=="__main__":unittest.main()
