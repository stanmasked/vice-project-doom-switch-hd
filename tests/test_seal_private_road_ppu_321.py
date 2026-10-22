"""Fabricated NES and FM2, invented 321-frame CPU traces only."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_fceux_smoke_rom import build_rom
from build_fceux_smoke_movie import make_movie
from test_audit_private_road_ppu_321_trace import fixture
from seal_private_road_ppu_321 import (
    preflight,finalize,verify,private_dir,PRE,POST,
)

class PrivateSha256SealTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        self.rom=root/"invented.nes"
        self.movie=root/"invented.fm2"
        self.directory=root/"ppu321"
        self.rom.write_bytes(build_rom())
        self.movie.write_text(make_movie(self.rom.read_bytes(),frames=1024))
        self.directory.mkdir()
    def tearDown(self):self.temp.cleanup()
    def complete(self):
        self.pre=preflight(self.rom,self.movie,self.directory)
        fixture(self.directory)
        frame_clock=["frame\tbegin_cycle\tend_cycle"]
        for f in range(600,921):
            frame_clock.append(f"{f}\t{f*30000}\t{f*30000+29780}")
        (self.directory/"road_321_frame_clock.tsv").write_text(
            "\n".join(frame_clock)+"\n")
        self.sealed=finalize(self.rom,self.movie,self.directory)
    def test_full_synthetic_capture_sha256_is_private(self):
        self.complete()
        result=verify(self.rom,self.movie,self.directory)
        self.assertTrue(result["original_source_full_file_sha256_stable"])
        self.assertTrue(result["ppu321_raw_reports_sealed"])
        self.assertFalse(result["same_rom_fm2_joined_to_legacy_road"])
        self.assertNotIn(str(self.rom),str(self.sealed))
        self.assertNotIn(str(self.movie),str(self.sealed))
    def test_unsealed_capture_rejected(self):
        preflight(self.rom,self.movie,self.directory)
        with self.assertRaises(ValueError):verify(
            self.rom,self.movie,self.directory)
    def test_original_synthetic_rom_tamper_rejected(self):
        self.complete()
        data=bytearray(self.rom.read_bytes())
        data[-1]^=1
        self.rom.write_bytes(data)
        with self.assertRaises(ValueError):verify(
            self.rom,self.movie,self.directory)
    def test_synthetic_movie_tamper_rejected(self):
        self.complete()
        self.movie.write_text(self.movie.read_text()+"\n")
        with self.assertRaises(ValueError):verify(
            self.rom,self.movie,self.directory)
    def test_private_raw_cpu_trace_tamper_rejected(self):
        self.complete()
        path=self.directory/"road_321_writers.tsv"
        path.write_text(path.read_text().replace("E8F1","E8EC",1))
        with self.assertRaises(ValueError):verify(
            self.rom,self.movie,self.directory)
    def test_private_frame_boundary_tamper_rejected(self):
        self.complete()
        path=self.directory/"road_321_frame_clock.tsv"
        path.write_text(path.read_text().replace("18000000","18000001",1))
        with self.assertRaises(ValueError):verify(
            self.rom,self.movie,self.directory)
    def test_bad_completion_manifest_rejected(self):
        self.complete()
        path=self.directory/POST
        path.write_text(path.read_text().replace(
            '"source_rom_fm2_joined_to_legacy_road": false',
            '"source_rom_fm2_joined_to_legacy_road": true'))
        with self.assertRaises(ValueError):verify(
            self.rom,self.movie,self.directory)
    def test_duplicate_manifest_creation_denied(self):
        preflight(self.rom,self.movie,self.directory)
        with self.assertRaises(ValueError):
            preflight(self.rom,self.movie,self.directory)
    def test_symlinked_capture_directory_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            linked=Path(tmp)/"link"
            try:linked.symlink_to(self.directory,target_is_directory=True)
            except OSError as e:self.skipTest(str(e))
            with self.assertRaises(ValueError):private_dir(linked)
    def test_no_original_capture_bytes_inside_public_checkout(self):
        source=Path(__file__).resolve().parents[1]
        with self.assertRaises(ValueError):private_dir(source)
    def test_duplicate_private_seal_rejected(self):
        self.complete()
        with self.assertRaises(FileExistsError):
            finalize(self.rom,self.movie,self.directory)
    def test_wrong_fm2_rejected_even_before_preflight(self):
        self.movie.write_text("version 3\n|0|........|||\n")
        with self.assertRaises(ValueError):
            preflight(self.rom,self.movie,self.directory)
        self.assertFalse((self.directory/PRE).exists())
    def test_finalizing_invalid_capture_without_sources_rejected(self):
        preflight(self.rom,self.movie,self.directory)
        with self.assertRaises(ValueError):
            finalize(self.rom,self.movie,self.directory)

if __name__=="__main__":unittest.main()
