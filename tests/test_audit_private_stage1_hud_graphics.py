"""Invented pixels only: Stage 1-1 HUD vs road original counterfactual audit."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_private_stage1_hud_graphics import audit, PIXELS, PPM_HEADER


def fixtures(root, *, road_pixel=False, mismatched_palette=False,
             other_frame=False, changed_position=False):
    manifest = []
    for frame in (600, 800):
        folder = root / f"f{frame}"
        folder.mkdir()
        dirs = {}
        for kind in ("original", "chr0", "ppumask"):
            directory = folder / kind
            directory.mkdir()
            dirs[kind] = directory
            original = kind != "chr0"
            info = {
                "format": "private_ppumask_one_write_ab_v1" if original
                          else "private_chr0_one_write_ab_v1",
                "mode": {"original":"original","chr0":"chr_bank_0_two_probe",
                         "ppumask":"probe_bg_off"}[kind],
                "frame": str(frame),
                "first_observed_frame": "1",
                "last_observed_frame": str(frame+2),
                "frame_gaps": "0",
                "target_instruction_hits": "1",
                "fm2_readonly": "yes",
            }
            if kind == "chr0":
                info["accumulator_restored_before_e38a"] = "yes"
                info["rom_identity_verified"] = "yes"
            else:
                info["source_rom_unchanged"] = "yes"
            (directory/"COMPLETE.txt").write_text(
                "".join(f"{key}={value}\n" for key,value in info.items()), "ascii")
            for n in range(frame-1, frame+3):
                rgb = bytearray(b"\x24" * PIXELS * 3)
                palette = bytearray(b"\x0f" * PIXELS)
                changed = (n == frame+1) if not other_frame else (n==frame)
                if changed and kind != "original":
                    locations = ([(200,32),(202,80),(227,120)] if kind=="chr0"
                                 else [(202,80),(205,100)])
                    if road_pixel and kind == "chr0":
                        locations.append((195,42))
                    if changed_position and frame == 800 and kind == "chr0":
                        locations[-1] = (227,121)
                    for y,x in locations:
                        i=y*256+x
                        rgb[i*3]=100
                        if not (mismatched_palette and kind=="chr0" and frame==600
                                and (y,x)==(202,80)):
                            palette[i]=0x09
                name=f"frame_{n:06d}"
                (directory/(name+".ppm")).write_bytes(PPM_HEADER+rgb)
                (directory/(name+".pal.bin")).write_bytes(palette)
        manifest.append({"frame":frame,"original":str(dirs["original"]),
                         "chr0":str(dirs["chr0"]),
                         "ppumask":str(dirs["ppumask"])})
    out=root/"manifest.json"
    out.write_text(json.dumps(manifest),"utf8")
    return out


class Stage159HUDResponseTests(unittest.TestCase):
    def test_two_cases_overlap_and_hud_only(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest=fixtures(Path(directory))
            report=audit(manifest,acknowledge_legacy=True)
            self.assertEqual(report["frames_compared"],2)
            self.assertEqual(report["per_frame"][0]["chr0_changed_pixels"],3)
            self.assertEqual(report["per_frame"][0]["ppumask_changed_pixels"],2)
            self.assertEqual(report["per_frame"][0]["overlapping_changed_pixels"],1)
            self.assertEqual(report["per_frame"][0]["chr0_only_changed_pixels"],2)
            self.assertEqual(report["per_frame"][0]["ppumask_only_changed_pixels"],1)
            self.assertEqual(report["per_frame"][0]["chr0_rows_not_affected_by_ppumask"],
                             [200,227])
            self.assertEqual(report["cross_frame_spatial_iou_first_two_cases"]
                             ["chr0"]["iou"],1.0)
            self.assertEqual(report["per_frame"][0]["upper_image_pixels_changed"],0)
            self.assertTrue(report["only_lower_hud_region_responded_in_tested_frames"])
            self.assertFalse(report["ppu_scanline_origin_proven"])
            self.assertFalse(report["cpu_x_restoration_independently_attested_by_legacy_witness"])
            self.assertNotIn(directory,json.dumps(report))

    def test_legacy_acknowledgement_required(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"explicit acknowledgement"):
                audit(fixtures(Path(directory)))

    def test_reject_changed_pixel_in_road_region(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"outside analyzed lower HUD"):
                audit(fixtures(Path(directory),road_pixel=True),acknowledge_legacy=True)

    def test_reject_rgb_palette_spatial_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"masks diverged"):
                audit(fixtures(Path(directory),mismatched_palette=True),
                      acknowledge_legacy=True)

    def test_reject_non_next_frame_response(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"outside next"):
                audit(fixtures(Path(directory),other_frame=True),acknowledge_legacy=True)

    def test_temporal_mask_iou_tracks_small_position_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            report=audit(fixtures(Path(directory),changed_position=True),
                         acknowledge_legacy=True)
            self.assertLess(report["cross_frame_spatial_iou_first_two_cases"]
                            ["chr0"]["iou"],1.0)
            self.assertEqual(report["cross_frame_spatial_iou_first_two_cases"]
                             ["ppumask"]["iou"],1.0)

    def test_reject_reused_capture_path(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest=fixtures(Path(directory))
            info=json.loads(manifest.read_text("utf8"))
            info[1]["original"]=info[0]["original"]
            manifest.write_text(json.dumps(info),"utf8")
            with self.assertRaisesRegex(ValueError,"directory reused"):
                audit(manifest,acknowledge_legacy=True)

    def test_reject_legacy_chr0_witness_renamed_to_x(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            manifest=fixtures(root)
            witness=root/"f600"/"chr0"/"COMPLETE.txt"
            witness.write_text(witness.read_text("ascii").replace(
                "accumulator_restored_before_e38a",
                "cpu_x_restored_before_e383"),"ascii")
            with self.assertRaisesRegex(ValueError,"provenance inconsistent"):
                audit(manifest,acknowledge_legacy=True)

    def test_reject_missing_private_palette_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            manifest=fixtures(root)
            (root/"f800"/"chr0"/"frame_000801.pal.bin").unlink()
            with self.assertRaisesRegex(ValueError,"screenshot missing"):
                audit(manifest,acknowledge_legacy=True)

    def test_reject_unsorted_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            manifest=fixtures(root)
            info=json.loads(manifest.read_text("utf8"))
            info.reverse()
            manifest.write_text(json.dumps(info),"utf8")
            with self.assertRaisesRegex(ValueError,"unique and sorted"):
                audit(manifest,acknowledge_legacy=True)


if __name__ == "__main__":
    unittest.main()
