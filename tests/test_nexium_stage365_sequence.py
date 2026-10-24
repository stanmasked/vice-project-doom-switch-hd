"""Synthetic negative regressions for Stage365; never a real emulator witness."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import audit_nexium_stage365_sequence as s


def row(i, **changes):
    pair = 519 + i
    event = "on" if i == 0 else "last" if i == 40 else "frame"
    shift = 3 if pair <= 526 else 4 if pair <= 558 else 5
    fields = dict(
        event=event, original_pair_start=str(pair), guest_frame=str(100 + i),
        image_shift=str(shift), panel_pixel=s.EXPECTED_PANEL,
        edge_pixel=s.EXPECTED_EDGE, demo_glyph_pixel=s.EXPECTED_EDGE,
        platform_fp="0123456789abcdef", **s.REQUIRED
    )
    fields.update(changes)
    return s.MARKER + " " + " ".join(k + "=" + v for k, v in fields.items())


def rows():
    return "\n".join(row(i) for i in range(41))


def evidence():
    host = "\n".join((
        "physical_keyboard_chord=R+T+Q Switch=ZL+ZR+L",
        "native_driving_enter=yes", "guest_v2_records=41",
        "guest_v2_first=on", "guest_v2_last=last",
        "STAGE365_REAL_NEXIUM_FULL_SEQUENCE_OBSERVED",
    ))
    driving = "VPD_DRIVING_GUEST_V1 seq=1 event=enter key=driving"
    return host, driving, rows()


class Stage365SyntheticNegativeTests(unittest.TestCase):
    def test_valid_41_guest_states(self):
        r = s.audit_sequence(*evidence())
        self.assertEqual(r["actual_native_guest_records"], 41)
        self.assertTrue(r["presentation_frames_contiguous"])

    def test_one_intermediate_record_missing(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, "\n".join(g.splitlines()[:19] + g.splitlines()[20:]))

    def test_extra_duplicate_state_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g + "\n" + row(40))

    def test_reordered_adjacent_records_rejected(self):
        h, d, g = evidence()
        v = g.splitlines()
        v[13], v[14] = v[14], v[13]
        with self.assertRaises(ValueError): s.audit_sequence(h, d, "\n".join(v))

    def test_pair_skip_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("original_pair_start=530", "original_pair_start=531"))

    def test_pair_duplicate_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("original_pair_start=530", "original_pair_start=529"))

    def test_first_pair_must_be_519(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("original_pair_start=519", "original_pair_start=520"))

    def test_last_pair_must_be_559(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("original_pair_start=559", "original_pair_start=560"))

    def test_event_labels_cannot_be_reordered(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("event=frame original_pair_start=530", "event=last original_pair_start=530"))

    def test_guest_frame_gap_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("guest_frame=130", "guest_frame=131"))

    def test_guest_frame_rewind_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("guest_frame=130", "guest_frame=128"))

    def test_guest_frame_wrap_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("guest_frame=140", "guest_frame=0"))

    def test_shift_mismatch_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("image_shift=4", "image_shift=3", 1))

    def test_wrong_panel_pixel_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("panel_pixel=ff5b4118", "panel_pixel=00000000", 1))

    def test_wrong_edge_pixel_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("edge_pixel=ffefda66", "edge_pixel=00000000", 1))

    def test_wrong_glyph_pixel_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("demo_glyph_pixel=ffefda66", "demo_glyph_pixel=00000000", 1))

    def test_changed_platform_fingerprint_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("platform_fp=0123456789abcdef", "platform_fp=ffffffffffffffff", 1))

    def test_original_physics_cannot_be_claimed(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("original_game_physics_proven=0", "original_game_physics_proven=1", 1))

    def test_original_rom_cannot_be_claimed(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("actual_original_rom_source_verification=0", "actual_original_rom_source_verification=1", 1))

    def test_controller_chord_is_required(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h.replace("R+T+Q", "R+T+W"), d, g)

    def test_real_guest_driving_entry_is_required(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d.replace("seq=1", "seq=2"), g)

    def test_host_sequence_summary_is_not_enough(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, "")

    def test_host_record_count_mismatch_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h.replace("guest_v2_records=41", "guest_v2_records=40"), d, g)

    def test_bad_fingerprint_format_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("platform_fp=0123456789abcdef", "platform_fp=xyz", 1))

    def test_duplicate_field_rejected(self):
        with self.assertRaises(ValueError): s.parse_line(row(0) + " event=on")

    def test_wrong_schema_rejected(self):
        with self.assertRaises(ValueError): s.parse_line(row(0).replace(s.MARKER, "VPD_STAGE363_NUMERIC_DEMO_V1"))

    def test_non_numeric_guest_frame_rejected(self):
        with self.assertRaises(ValueError): s.parse_line(row(0).replace("guest_frame=100", "guest_frame=abc"))

    def test_bad_last_label_rejected(self):
        h, d, g = evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h, d, g.replace("event=last original_pair_start=559", "event=frame original_pair_start=559"))


if __name__ == "__main__":
    unittest.main()
