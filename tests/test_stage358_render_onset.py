"""Stage358: no original media, all test images and CPU event rows fabricated."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import audit_private_stage358_render_onset as s


def rgb(a=b"\x00\x00\x00"):
    return a*4


def record(f,*,flat,delta=0,band=0,spike=False):
    return dict(frame=f,image_sha="fake"+str(f if not flat else 0),
                unique_colors=1 if flat else 4,uniform=flat,delta_pixels=delta,
                regions_changing=band,w2000=4 if spike else 2,
                w2006=14 if spike else 10,
                ppu_status_reads=4 if spike else 2,
                native_line_zero_mask_nonzero=True)


def source_shaped():
    return [record(f,flat=(f<409),delta=36854 if f==409 else 8312 if f==417 else 333,
                   band=4 if f in (409,417) else 0,spike=f in (409,417))
            for f in range(405,420)]


class Stage358SourceFree(unittest.TestCase):
    def test_frozen_source_window_and_masks(self):
        self.assertEqual((s.FIRST,s.LAST), (405,419))
        self.assertEqual(len(s.REGIONS),4)
        self.assertEqual(s.REGIONS["left_env_upper"],(0,52,20,98))

    def test_single_color_is_uniform(self):
        self.assertEqual(s.source_frame_features(rgb(),width=2,height=2),
                         {"unique_colors":1,"uniform":True})

    def test_multi_color_not_uniform(self):
        f=rgb()[:-3]+b"\x01\x00\x00"
        self.assertEqual(s.source_frame_features(f,width=2,height=2)["unique_colors"],2)

    def test_missing_rgb_pixel_is_rejected(self):
        with self.assertRaises(ValueError):
            s.source_frame_features(b"\x00"*11,width=2,height=2)

    def test_identical_images_have_zero_change_not_proven_camera(self):
        self.assertEqual(s.changed_pixels(rgb(),rgb(),width=2,height=2),0)

    def test_one_pixel_change_counted_once_even_all_channels(self):
        after=rgb()[:-3]+b"\xff\xee\xdd"
        self.assertEqual(s.changed_pixels(rgb(),after,width=2,height=2),1)

    def test_region_excludes_change_outside_region(self):
        after=rgb()[:-3]+b"\xff\xee\xdd"
        self.assertEqual(s.changed_pixels(rgb(),after,width=2,height=2,rect=(0,1,0,1)),0)

    def test_region_rejects_malformed_coordinates(self):
        with self.assertRaises(ValueError):
            s.changed_pixels(rgb(),rgb(),width=2,height=2,rect=(-1,2,0,2))

    def test_ppu_extra_event_profile_keeps_native_mask_separate(self):
        sample=s.event_profile(["W2000"]*4+["W2006"]*14+
                               ["ppu_status_read"]*4,30)
        self.assertEqual(sample["w2000"],4)
        self.assertEqual(sample["w2006"],14)
        self.assertEqual(sample["ppu_status_reads"],4)
        self.assertTrue(sample["native_line_zero_mask_nonzero"])

    def test_nonzero_mask_does_not_prove_texture(self):
        sample=s.event_profile(["W2000"]*2,30)
        self.assertTrue(sample["native_line_zero_mask_nonzero"])

    def test_zero_mask_not_counted_as_cpu_write_absence(self):
        sample=s.event_profile(["W2000"]*2,0)
        self.assertFalse(sample["native_line_zero_mask_nonzero"])
        self.assertEqual(sample["w2000"],2)

    def test_malformed_native_mask_fails(self):
        with self.assertRaises(ValueError):
            s.event_profile(["W2000"],256)

    def test_onset_and_second_spike_recognized(self):
        result=s.summarize(source_shaped())
        self.assertEqual(result["first_nonflat_rgb_frame"],409)
        self.assertEqual(result["uniform_prefix_frames"],4)
        self.assertEqual(result["four_environment_region_change_frame_numbers"],[409,417])
        self.assertEqual(result["cpu_ppu_extra_write_and_status_read_frame_numbers"],[409,417])
        self.assertEqual(result["four_region_change_and_cpu_ppu_extra_event_overlap"],2)

    def test_similar_event_counts_without_image_changes_not_causal(self):
        rows=source_shaped()
        rows[12]["regions_changing"]=0
        result=s.summarize(rows)
        self.assertEqual(result["four_region_change_and_cpu_ppu_extra_event_overlap"],1)
        self.assertFalse(result["all_cpu_ppu_extra_events_proven_cause_of_pixels"])

    def test_previous_unproven_gate_must_remain_failed(self):
        result=s.summarize(source_shaped())
        self.assertFalse(result["prior_stage355_inconclusive_motion_gate_changed"])
        self.assertFalse(result["prior_stage357_strict_zero_shift_qualified_pairs_modified"])
        self.assertFalse(result["vehicle_speed_camera_road_collision_or_ppu_dots_proven"])

    def test_not_15_consecutive_source_frames_fails(self):
        with self.assertRaises(ValueError):
            s.summarize(source_shaped()[:-1])

    def test_duplicate_source_frame_rejected(self):
        rows=source_shaped();rows[7]["frame"]=rows[6]["frame"]
        with self.assertRaises(ValueError):
            s.summarize(rows)

    def test_no_observable_texture_onset_fails(self):
        rows=[record(f,flat=True) for f in range(405,420)]
        with self.assertRaises(ValueError):
            s.summarize(rows)


if __name__=="__main__":unittest.main()
