"""Complete private-join regression uses INVENTED NES, FM2 and RGB only."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_fceux_smoke_rom import build_rom
from build_fceux_smoke_movie import make_movie
from test_audit_private_road_ppu_321_trace import fixture as fake_cpu
from test_audit_private_legacy_road_geometry import synthetic as old_fixture
from test_audit_private_road_mask_reproduction import fabricated_rgb
from seal_private_road_ppu_321 import preflight,finalize
from build_private_road_ppu_join import audit,derive_documents

class OriginalFreeFullJoinTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.rom=self.root/"invented.nes"
        self.movie=self.root/"invented.fm2"
        self.cap=self.root/"private-sealed-session"
        self.old=self.root/"hashless-legacy.json"
        self.rom.write_bytes(build_rom())
        self.movie.write_text(make_movie(self.rom.read_bytes(),frames=1024))
        self.cap.mkdir()
        self.legacy=old_fixture()
        self.old.write_text(json.dumps(self.legacy))
    def tearDown(self):self.tmp.cleanup()
    def build(self,alter=None):
        preflight(self.rom,self.movie,self.cap)
        fake_cpu(self.cap)
        phase=["frame\tbegin_cycle\tend_cycle"]
        for f in range(600,921):
            phase.append(f"{f}\t{f*30000}\t{f*30000+29780}")
        (self.cap/"road_321_frame_clock.tsv").write_text("\n".join(phase)+"\n")
        rgb=bytearray(fabricated_rgb(self.legacy))
        if alter:alter(rgb)
        (self.cap/"road_321_rgb_scanlines.bin").write_bytes(rgb)
        finalize(self.rom,self.movie,self.cap)
    def test_full_synthetic_identity_join(self):
        self.build()
        report=audit(self.rom,self.movie,self.cap,self.old)
        self.assertEqual(report["new_source_cpu_writer_events"],1284)
        self.assertEqual(report["new_source_road_image_slots"],41)
        self.assertTrue(report["original_same_session_ppu_rgb_numeric_join_checked"])
        self.assertFalse(report["legacy_hashless_numeric_report_sha256_authenticated"])
        self.assertFalse(report["original_nes_ppu_effective_scroll_proven"])
        self.assertNotIn("rom_sha256",report)
        self.assertNotIn("road_x",report)
    def test_ephemeral_numeric_docs_match_actual_schema(self):
        self.build()
        road,ppu=derive_documents(self.cap)
        self.assertEqual(road["schema"],"road_image_cross_sections_window_v1")
        self.assertEqual(ppu["schema"],"ppu_cpu_writer_phases_v1")
        self.assertEqual(road["rom_sha256"],ppu["rom_sha256"])
        self.assertEqual(road["fm2_sha256"],ppu["fm2_sha256"])
        self.assertEqual(len(road["slots"]),41)
        self.assertEqual(len(ppu["samples"]),321)
    def test_tampered_movie_after_sealing(self):
        self.build()
        self.movie.write_text(self.movie.read_text()+"\n")
        with self.assertRaises(ValueError):
            audit(self.rom,self.movie,self.cap,self.old)
    def test_changed_original_free_source_rgb_after_sealing(self):
        self.build()
        target=self.cap/"road_321_rgb_scanlines.bin"
        pixels=bytearray(target.read_bytes());pixels[90]^=1
        target.write_bytes(pixels)
        with self.assertRaises(ValueError):
            audit(self.rom,self.movie,self.cap,self.old)
    def test_legacy_numeric_mismatch_not_silently_joined(self):
        self.build()
        old=copy.deepcopy(self.legacy)
        old["frames"][0]["valid_scanline_count"]=3
        self.old.write_text(json.dumps(old))
        with self.assertRaises(ValueError):
            audit(self.rom,self.movie,self.cap,self.old)
    def test_private_cpu_phase_belongs_to_same_frame(self):
        self.build()
        writers=self.cap/"road_321_writers.tsv"
        writers.write_text(writers.read_text().replace(
            "600\t2\tE8F1\t4F\t18000807",
            "600\t2\tE8F1\t4F\t18005007"))
        with self.assertRaises(ValueError):
            audit(self.rom,self.movie,self.cap,self.old)
    def test_unsealed_private_directory_rejected(self):
        with self.assertRaises(ValueError):
            audit(self.rom,self.movie,self.cap,self.old)
    def test_legacy_report_original_media_path_injection_rejected(self):
        self.build()
        old=copy.deepcopy(self.legacy)
        old["original_game_file"]="/secret/rom.nes"
        self.old.write_text(json.dumps(old))
        with self.assertRaises(ValueError):
            audit(self.rom,self.movie,self.cap,self.old)

if __name__=="__main__":unittest.main()
