"""Invented ROM, FM2, RGB and CPU clocks; zero original NES assets."""
from __future__ import annotations
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_fceux_smoke_rom import build_rom
from build_fceux_smoke_movie import make_movie
from test_audit_private_legacy_road_geometry import synthetic as old_numeric
from test_audit_private_road_mask_reproduction import fabricated_rgb
from test_audit_private_road_ppu_321_trace import fixture as fake_trace
from seal_private_road_ppu_321 import preflight,finalize
from audit_private_dual_road_ppu_replay import compare,run_and_compare,compare_fresh,run_and_compare_fresh

class DualReplaySourceFreeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.rom=self.root/"invented.nes"
        self.movie=self.root/"invented.fm2"
        self.legacy=self.root/"legacy.json"
        self.first=self.root/"replay-a"
        self.second=self.root/"replay-b"
        self.rom.write_bytes(build_rom())
        self.movie.write_text(make_movie(self.rom.read_bytes(),frames=1024))
        self.legacy.write_text(json.dumps(old_numeric()))
    def tearDown(self):self.temp.cleanup()
    def create(self,output:Path,absolute_epoch_delta=0,
               early_phase_shift=0,mutate_rgb=False,
               mutate_ram=False,mutate_frame_duration=False):
        output.mkdir()
        preflight(self.rom,self.movie,output)
        fake_trace(output)
        clock=["frame\tbegin_cycle\tend_cycle"]
        for f in range(600,921):
            enddelta=1 if mutate_frame_duration and f==616 else 0
            clock.append(
                f"{f}\t{f*30000+absolute_epoch_delta}"
                f"\t{f*30000+29780+absolute_epoch_delta+enddelta}")
        (output/"road_321_frame_clock.tsv").write_text(
            "\n".join(clock)+"\n")
        if absolute_epoch_delta:
            src=output/"road_321_writers.tsv"
            lines=src.read_text().splitlines()
            for i in range(1,len(lines)):
                parts=lines[i].split("\t")
                parts[-1]=str(int(parts[-1])+absolute_epoch_delta)
                lines[i]="\t".join(parts)
            src.write_text("\n".join(lines)+"\n")
        if early_phase_shift:
            src=output/"road_321_writers.tsv"
            lines=src.read_text().splitlines()
            for i in range(1,len(lines)):
                parts=lines[i].split("\t")
                if parts[0]=="616" and parts[1] in ("1","2"):
                    parts[-1]=str(int(parts[-1])+early_phase_shift)
                    lines[i]="\t".join(parts)
            src.write_text("\n".join(lines)+"\n")
        if mutate_ram:
            src=output/"road_321_postframe.tsv"
            raw=src.read_text()
            assert "616\t12\t4" in raw
            src.write_text(raw.replace("616\t12\t4","616\t13\t4",1))
        rgb=bytearray(fabricated_rgb(old_numeric()))
        if mutate_rgb:
            # Non-road background changes, accepted road boundaries same.
            rgb[20+2]^=1
        (output/"road_321_rgb_scanlines.bin").write_bytes(rgb)
        finalize(self.rom,self.movie,output)
    def pair(self,**b_options):
        self.create(self.first)
        self.create(self.second,**b_options)
    def check_bad(self,**opts):
        self.pair(**opts)
        with self.assertRaises(ValueError):
            compare(self.rom,self.movie,self.legacy,self.first,self.second)
    def test_identical_private_source_free_replays(self):
        self.pair()
        result=compare(self.rom,self.movie,self.legacy,self.first,self.second)
        self.assertEqual(result["source_cpu_frames_compared"],321)
        self.assertEqual(result["source_cpu_writer_values_and_phases_compared"],1284)
        self.assertTrue(result["source_raw_rgb_scanline_bytes_identical"])
        self.assertFalse(result["two_independent_fceux_processes_proven_by_existing_files"])
        self.assertFalse(result["original_effective_ppu_scroll_proven"])
        self.assertNotIn("rom_sha256",result)
    def test_different_absolute_clock_epoch_still_valid(self):
        self.pair(absolute_epoch_delta=1000)
        result=compare(self.rom,self.movie,self.legacy,self.first,self.second)
        self.assertFalse(result["absolute_cpu_cycle_clock_epoch_assumed_identical"])
    def test_fresh_source_dual_replay_passes_without_legacy_report(self):
        self.pair()
        result=compare_fresh(self.rom,self.movie,self.first,self.second)
        self.assertEqual(result["source_road_rgb_samples_compared"],41)
        self.assertEqual(result["source_cpu_frames_compared"],321)
        self.assertEqual(result["source_cpu_writer_values_and_phases_compared"],1284)
        self.assertTrue(result["source_raw_rgb_scanline_bytes_identical"])
        self.assertTrue(result["fresh_source_alignment_passed_for_both"])
        self.assertFalse(result["legacy_hashless_numeric_report_compared"])
        self.assertFalse(result["legacy_exact_reproduction_claimed"])
        self.assertFalse(result["two_independent_fceux_processes_proven_by_existing_files"])
        self.assertNotIn("rom_sha256",result)
        self.assertNotIn("fm2_sha256",result)

    def test_fresh_source_mode_does_not_read_legacy_report(self):
        self.pair()
        source=json.loads(self.legacy.read_text())
        source["frames"][0]["valid_scanline_count"]=3
        self.legacy.write_text(json.dumps(source))
        result=compare_fresh(self.rom,self.movie,self.first,self.second)
        self.assertTrue(result["fresh_source_alignment_passed_for_both"])
        self.assertFalse(result["legacy_hashless_numeric_report_compared"])

    def test_fresh_source_nonroad_rgb_drift_rejected(self):
        self.check_bad_fresh(mutate_rgb=True)

    def test_fresh_source_cpu_phase_drift_rejected(self):
        self.check_bad_fresh(early_phase_shift=1)

    def test_fresh_source_ram_drift_rejected(self):
        self.check_bad_fresh(mutate_ram=True)

    def test_fresh_source_frame_duration_drift_rejected(self):
        self.check_bad_fresh(mutate_frame_duration=True)

    def test_fresh_source_wrong_rom_after_seal_rejected(self):
        self.pair()
        self.rom.write_bytes(self.rom.read_bytes()+b"X")
        with self.assertRaises(ValueError):
            compare_fresh(self.rom,self.movie,self.first,self.second)

    def test_fresh_execute_triggers_two_distinct_capture_launches(self):
        called=[]
        def fake_launch(rom,movie,output,fceux,timeout_seconds):
            called.append((output,fceux,timeout_seconds))
            self.create(output)
        with patch("audit_private_dual_road_ppu_replay.launch",
                   side_effect=fake_launch) as run:
            result=run_and_compare_fresh(
                self.rom,self.movie,self.first,self.second,
                executable="fceux",watchdog=600)
        self.assertEqual(run.call_count,2)
        self.assertEqual([x[0] for x in called],[self.first,self.second])
        self.assertTrue(result["two_separate_fceux_processes_launched_by_this_command"])
        self.assertFalse(result["legacy_hashless_numeric_report_compared"])

    def test_fresh_execute_rejects_same_target_before_launch(self):
        with patch("audit_private_dual_road_ppu_replay.launch") as run:
            with self.assertRaises(ValueError):
                run_and_compare_fresh(self.rom,self.movie,self.first,self.first)
            run.assert_not_called()

    def check_bad_fresh(self,**opts):
        self.pair(**opts)
        with self.assertRaises(ValueError):
            compare_fresh(self.rom,self.movie,self.first,self.second)

    def test_nonroad_rgb_pixel_drift_rejected(self):
        self.check_bad(mutate_rgb=True)
    def test_source_cpu_phase_drift_rejected(self):
        self.check_bad(early_phase_shift=1)
    def test_ram_byte_drift_rejected(self):
        self.check_bad(mutate_ram=True)
    def test_actual_frame_duration_drift_rejected(self):
        self.check_bad(mutate_frame_duration=True)
    def test_one_missing_capture_rejected(self):
        self.create(self.first)
        with self.assertRaises(ValueError):
            compare(self.rom,self.movie,self.legacy,self.first,self.second)
    def test_copied_same_directory_rejected(self):
        self.create(self.first)
        with self.assertRaises(ValueError):
            compare(self.rom,self.movie,self.legacy,self.first,self.first)
    def test_file_instead_of_second_directory_rejected(self):
        self.create(self.first)
        self.second.write_text("not a private capture directory")
        with self.assertRaises(ValueError):
            compare(self.rom,self.movie,self.legacy,self.first,self.second)
    def test_symlink_alias_to_capture_directory_rejected(self):
        self.create(self.first)
        try:
            self.second.symlink_to(self.first,target_is_directory=True)
        except OSError as err:
            self.skipTest(str(err))
        with self.assertRaises(ValueError):
            compare(self.rom,self.movie,self.legacy,self.first,self.second)
    def test_execute_triggers_two_independent_capture_launches(self):
        called=[]
        def fake_launch(rom,movie,output,fceux,timeout_seconds):
            called.append((output,fceux,timeout_seconds))
            self.create(output)
        with patch("audit_private_dual_road_ppu_replay.launch",
                   side_effect=fake_launch) as run:
            result=run_and_compare(
                self.rom,self.movie,self.legacy,
                self.first,self.second,executable="fceux",
                watchdog=600)
        self.assertEqual(run.call_count,2)
        self.assertEqual([x[0] for x in called],
                         [self.first,self.second])
        self.assertTrue(
            result["two_separate_fceux_processes_launched_by_this_command"])
        self.assertFalse(result["original_effective_ppu_scroll_proven"])
    def test_execute_rejects_same_target_before_any_launch(self):
        with patch("audit_private_dual_road_ppu_replay.launch") as run:
            with self.assertRaises(ValueError):
                run_and_compare(
                    self.rom,self.movie,self.legacy,
                    self.first,self.first)
            run.assert_not_called()
    def test_execute_second_launch_failure_never_reports_success(self):
        calls=[]
        def fake_launch(rom,movie,output,fceux,timeout_seconds):
            calls.append(output)
            if len(calls)==2:
                raise ValueError("second private process did not finish")
            self.create(output)
        with patch("audit_private_dual_road_ppu_replay.launch",
                   side_effect=fake_launch):
            with self.assertRaises(ValueError):
                run_and_compare(self.rom,self.movie,self.legacy,
                                self.first,self.second)
        self.assertEqual(calls,[self.first,self.second])
    def test_wrong_rom_fm2_input_file_rejected(self):
        self.pair()
        self.rom.write_bytes(self.rom.read_bytes()+b"X")
        with self.assertRaises(ValueError):
            compare(self.rom,self.movie,self.legacy,self.first,self.second)
    def test_legacy_road_numeric_status_change_rejected(self):
        self.pair()
        source=json.loads(self.legacy.read_text())
        source["frames"][0]["valid_scanline_count"]=3
        self.legacy.write_text(json.dumps(source))
        with self.assertRaises(ValueError):
            compare(self.rom,self.movie,self.legacy,self.first,self.second)

if __name__=="__main__":unittest.main()
