"""Stage356 source-free synthetic negative controls; no ROM or actual image pixels."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_private_stage356_early_ppu_mask as s


def frame(color:bytes=b'\x10\x20\x30')->bytes:
    return color*4


def registers():
    return [(2,30)]*9+[(0,0)]*8+[(2,30)]*8


class Stage356OriginalStateSuitability(unittest.TestCase):
    def test_flat_identical_rgb_sequence_is_not_a_motion_measurement(self):
        r=s.classify_images([frame()]*25,width=2,height=2)
        self.assertEqual(r['uniform_single_color_image_frames'],25)
        self.assertEqual(r['identical_consecutive_rgb_pairs'],24)
        self.assertEqual(r['unique_complete_rgb_frames'],1)

    def test_flat_color_switch_counts_one_change(self):
        frames=[frame()]*12+[frame(b'\x10\x20\x31')]*13
        r=s.classify_images(frames,width=2,height=2)
        self.assertEqual(r['uniform_single_color_image_frames'],25)
        self.assertEqual(r['identical_consecutive_rgb_pairs'],23)
        self.assertEqual(r['unique_complete_rgb_frames'],2)

    def test_tiled_texture_is_not_uniform(self):
        f=frame()[:-3]+b'\xff\x00\x00'
        r=s.classify_images([f]*25,width=2,height=2)
        self.assertEqual(r['uniform_single_color_image_frames'],0)
        self.assertEqual(r['identical_consecutive_rgb_pairs'],24)

    def test_missing_frame_rejected(self):
        with self.assertRaisesRegex(ValueError,'25'):
            s.classify_images([frame()]*24,width=2,height=2)

    def test_frame_shape_rejected(self):
        with self.assertRaisesRegex(ValueError,'RGB'):
            s.classify_images([b'\x00']*25,width=2,height=2)

    def test_missing_write_and_line_mask_coincide(self):
        r=s.classify_registers(registers())
        self.assertEqual(r['source_frames_without_second_phase_2005_write'],8)
        self.assertEqual(r['native_line_zero_ppu_mask_zero_frames'],8)
        self.assertEqual(r['missing_second_phase_write_and_zero_line_mask_frames'],8)

    def test_source_shaped_ninth_zero_mask_does_not_hide_present_write(self):
        sample=registers()
        sample[0]=(2,0)
        r=s.classify_registers(sample)
        self.assertEqual(r['source_frames_without_second_phase_2005_write'],8)
        self.assertEqual(r['native_line_zero_ppu_mask_zero_frames'],9)
        self.assertEqual(r['missing_second_phase_write_and_zero_line_mask_frames'],8)
        self.assertEqual(r['zero_line_mask_but_present_write_frames'],1)

    def test_discordant_mask_and_writes_not_erased(self):
        x=registers();x[9]=(0,30);x[0]=(2,0)
        r=s.classify_registers(x)
        self.assertEqual(r['missing_second_phase_write_and_zero_line_mask_frames'],7)
        self.assertEqual(r['missing_write_but_nonzero_line_mask_frames'],1)
        self.assertEqual(r['zero_line_mask_but_present_write_frames'],1)

    def test_zero_line_mask_with_present_write_is_not_reconstructed(self):
        x=[(2,0)]*25
        r=s.classify_registers(x)
        self.assertEqual(r['source_frames_without_second_phase_2005_write'],0)
        self.assertEqual(r['zero_line_mask_but_present_write_frames'],25)
        self.assertFalse(r['carried_previous_register_value_verified'])

    def test_all_missing_writes_still_do_not_prove_retention(self):
        r=s.classify_registers([(0,0)]*25)
        self.assertEqual(r['source_frames_without_second_phase_2005_write'],25)
        self.assertFalse(r['carried_previous_register_value_verified'])

    def test_bool_write_count_rejected(self):
        x=registers();x[0]=(True,30)
        with self.assertRaisesRegex(ValueError,'valid'):
            s.classify_registers(x)

    def test_invalid_mask_rejected(self):
        x=registers();x[0]=(2,256)
        with self.assertRaisesRegex(ValueError,'valid'):
            s.classify_registers(x)

    def test_missing_register_frame_rejected(self):
        with self.assertRaisesRegex(ValueError,'25'):
            s.classify_registers(registers()[:-1])

    def test_diagnostic_cannot_retroactively_upgrade_old_holdout(self):
        payload=s.summarize(s.classify_images([frame()]*25,width=2,height=2),
                            s.classify_registers(registers()))
        self.assertFalse(payload['previous_stage355_motion_gate_passing'])
        self.assertFalse(payload['frozen_stage355_four_mask_motion_result_changed'])
        self.assertFalse(payload['automatic_zero_scroll_assumed_when_no_write'])

    def test_no_general_camera_or_vehicle_inference(self):
        payload=s.summarize(s.classify_images([frame()]*25,width=2,height=2),
                            s.classify_registers(registers()))
        self.assertFalse(payload['camera_or_vehicle_physics_proven'])
        self.assertFalse(payload['original_frames_trace_rows_or_private_hashes_in_output'])

    def test_external_source_manifest_not_included_in_classification(self):
        payload=s.summarize(s.classify_images([frame()]*25,width=2,height=2),
                            s.classify_registers(registers()))
        self.assertNotIn('source_hashes',payload)
        self.assertEqual(payload['stage'],356)


if __name__=='__main__': unittest.main()
