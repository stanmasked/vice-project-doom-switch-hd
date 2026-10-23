"""Stage349 fabricated-only modulo-240 PPU vertical-wrap tests."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_private_stage349_periodic_scroll as model
import audit_private_stage345_scroll_motion as legacy


def manufactured_window(first:int,last:int,steps:list[int],start_y:int)->tuple:
    assert len(steps)==24
    ys=[start_y]
    for display in steps:ys.append((ys[-1]-display)%240)
    pairs=[(model.periodic_y_step(a,b),legacy.signed_delta(a,b),display)
           for a,b,display in zip(ys,ys[1:],steps)]
    return first,last,pairs


def three_synthetic_windows()->list[tuple]:
    return [
      manufactured_window(420,444,[0]*11+[1]*13,61),
      manufactured_window(445,469,[1]*18+[2]*6,89),
      manufactured_window(470,494,[2]*24,18),
    ]


class Stage349RomFree(unittest.TestCase):
    def test_reconstructed_three_window_tally(self):
        result=model.summarize(three_synthetic_windows())
        self.assertEqual(result['adjacent_pixel_register_pairs_verified'],72)
        self.assertEqual(result['modulo240_first_y_inverse_pixel_motion_matches'],72)
        self.assertEqual(result['ordinary_signed_8bit_first_y_inverse_pixel_motion_matches'],71)
        self.assertFalse(result['universal_game_camera_speed_model_proven'])

    def test_actual_240_wrap_math(self):
        self.assertEqual(model.periodic_y_step(0,238),-2)
        self.assertEqual(legacy.signed_delta(0,238),-18)

    def test_normal_negative_scroll_without_wrap(self):
        self.assertEqual(model.periodic_y_step(14,12),-2)

    def test_positive_forward_step(self):
        self.assertEqual(model.periodic_y_step(238,0),2)

    def test_zero_step(self):
        self.assertEqual(model.periodic_y_step(64,64),0)

    def test_bad_attribute_table_vertical_input_rejected(self):
        for value in (240,255,-1,256):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,'outside validated'):
                    model.periodic_y_step(value,0)

    def test_booleans_are_not_scroll_values(self):
        with self.assertRaises(ValueError):
            model.periodic_y_step(True,0)

    def test_ambiguous_half_period_rejected(self):
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            model.periodic_y_step(0,120)

    def test_missing_window_rejected(self):
        with self.assertRaisesRegex(ValueError,'three exact'):
            model.summarize(three_synthetic_windows()[:2])

    def test_wrong_window_order_rejected(self):
        ws=three_synthetic_windows()
        with self.assertRaisesRegex(ValueError,'three exact'):
            model.summarize([ws[1],ws[0],ws[2]])

    def test_missing_frame_pair_rejected(self):
        ws=three_synthetic_windows()
        ws[1]=(445,469,ws[1][2][:-1])
        with self.assertRaisesRegex(ValueError,'missing original'):
            model.summarize(ws)

    def test_one_pixel_contradiction_rejected(self):
        ws=three_synthetic_windows()
        data=list(ws[0][2])
        old=data[17]
        data[17]=(old[0],old[1],0)
        ws[0]=(420,444,data)
        with self.assertRaisesRegex(ValueError,'contradicts'):
            model.summarize(ws)

    def test_wrong_signed_8bit_baseline_rejected(self):
        ws=three_synthetic_windows()
        data=list(ws[2][2])
        old=data[9]
        data[9]=(old[0],-2,old[2])
        ws[2]=(470,494,data)
        with self.assertRaisesRegex(ValueError,'baseline'):
            model.summarize(ws)

    def test_dont_force_camera_speed_from_pixel_register_match(self):
        report=model.summarize(three_synthetic_windows())
        self.assertFalse(report['vehicle_collision_or_road_geometry_proven'])
        self.assertFalse(report['actual_hardware_ppu_dot_proven'])

    def test_unselected_frame_window_rejected(self):
        ws=three_synthetic_windows()
        ws[0]=(430,454,ws[0][2])
        with self.assertRaisesRegex(ValueError,'three exact'):
            model.summarize(ws)

    def test_scroll_outside_240_rejected_not_wrapped_silently(self):
        with self.assertRaises(ValueError):
            model.periodic_y_step(239,240)


if __name__=='__main__':unittest.main()
