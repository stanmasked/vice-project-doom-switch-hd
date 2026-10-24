"""Synthetic negative tests for real NeXium cancel/restart/terminal-off audit; never runtime proof."""
from pathlib import Path
import sys
import unittest
from tempfile import TemporaryDirectory
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import audit_nexium_stage371_lifecycle as s


def row(pair, guest_frame, event, shift=None, **changes):
    if shift is None:
        shift = 3 if pair <= 526 else 4 if pair <= 558 else 5
    fields = dict(
        event=event, original_pair_start=str(pair), guest_frame=str(guest_frame),
        image_shift=str(shift), panel_pixel="ff5b4118", edge_pixel="ffefda66",
        demo_glyph_pixel="ffefda66", platform_fp="0123456789abcdef",
        source="libnx_drawScene", actual_original_rom_source_verification="0",
        original_game_physics_proven="0", raw_rom_fm2_present="0",
    )
    fields.update(changes)
    return "VPD_STAGE365_NUMERIC_DEMO_V2 " + " ".join(k + "=" + v for k, v in fields.items())


def make_rows(first_count=6):
    first = [row(519+i, 100+i, "on" if i == 0 else "frame") for i in range(first_count)]
    second = [row(519+i, 120+i, "on" if i == 0 else "last" if i == 40 else "frame")
              for i in range(41)]
    return "\n".join(first + second)


def evidence(first_count=6):
    host = "\n".join((
        "guest_sd_witness_files_ready=yes", "native_manual_entry=yes",
        "native_driving_enter=yes",
        "physical_keyboard_chord_start=R+T+Q Switch=ZL+ZR+L",
        "physical_keyboard_chord_cancel=R+T+Q Switch=ZL+ZR+L",
        "physical_keyboard_chord_restart=R+T+Q Switch=ZL+ZR+L",
        "cancel_screenshot_captured=yes", "guest_trace_stable_while_off=yes",
        "guest_trace_stable_after_complete=yes", "screen_completed_cyan_pixels=0",
        "first_session_records=" + str(first_count),
        "guest_trace_after_off_count=" + str(first_count),
        "second_session_records=41", "total_guest_records=" + str(first_count + 41),
        "guest_trace_after_complete_count=" + str(first_count + 41),
        "STAGE371_REAL_NEXIUM_CANCEL_RESTART_OBSERVED",
        "STAGE372_REAL_NEXIUM_TERMINAL_OFF_OBSERVED",
    ))
    manual = "VPD_ROMFREE_MANUAL_V1 seq=1 event=enter frame=0 metric=1 mode=manual original_game_proven=no"
    driving = "VPD_DRIVING_GUEST_V1 seq=1 event=enter key=driving"
    return host, manual, driving, make_rows(first_count)


class Stage372SyntheticNegativeTests(unittest.TestCase):
    def test_valid_cancel_and_full_restart(self):
        result = s.audit_sequence(*evidence())
        self.assertEqual(result["actual_native_guest_sessions"], 2)
        self.assertEqual(result["second_session_states_after_fresh_edge"], 41)
        self.assertTrue(result["post_completion_guest_trace_stable"])

    def test_short_first_session_rejected(self):
        with self.assertRaises(ValueError): s.audit_sequence(*evidence(5))

    def test_first_session_too_long_rejected(self):
        with self.assertRaises(ValueError): s.audit_sequence(*evidence(17))

    def test_only_one_start_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,"\n".join(g.splitlines()[:6]))

    def test_third_start_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g+"\n"+row(519,170,"on"))

    def test_restart_requires_fresh_pair_519(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("event=on original_pair_start=519 guest_frame=120","event=on original_pair_start=520 guest_frame=120",1))

    def test_restarted_session_must_have_41_states(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,"\n".join(g.splitlines()[:-1]))

    def test_first_session_cannot_reach_last_pair(self):
        h,m,d,g=evidence(6)
        lines=g.splitlines()
        lines[5]=row(559,105,"last")
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,"\n".join(lines))

    def test_guest_frame_gap_inside_first_session_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("guest_frame=103","guest_frame=104",1))

    def test_guest_frame_gap_inside_restart_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("guest_frame=125","guest_frame=127",1))

    def test_restart_must_happen_at_later_guest_frame(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("guest_frame=120","guest_frame=105",1))

    def test_shift_corruption_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("image_shift=4","image_shift=3",1))

    def test_wrong_panel_pixel_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("panel_pixel=ff5b4118","panel_pixel=00000000",1))

    def test_wrong_edge_pixel_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("edge_pixel=ffefda66","edge_pixel=00000000",1))

    def test_wrong_glyph_pixel_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("demo_glyph_pixel=ffefda66","demo_glyph_pixel=00000000",1))

    def test_fingerprint_must_stay_constant(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("platform_fp=0123456789abcdef","platform_fp=ffffffffffffffff",1))

    def test_missing_real_manual_witness_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,"",d,g)

    def test_missing_driving_entry_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,"",g)

    def test_missing_cancel_input_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h.replace("physical_keyboard_chord_cancel=R+T+Q Switch=ZL+ZR+L",""),m,d,g)

    def test_missing_restart_input_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h.replace("physical_keyboard_chord_restart=R+T+Q Switch=ZL+ZR+L",""),m,d,g)

    def test_cancel_screenshot_capture_marker_required(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h.replace("cancel_screenshot_captured=yes","cancel_screenshot_captured=no"),m,d,g)

    def test_trace_must_stop_while_overlay_off(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h.replace("guest_trace_stable_while_off=yes","guest_trace_stable_while_off=no"),m,d,g)

    def test_original_physics_claim_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("original_game_physics_proven=0","original_game_physics_proven=1",1))

    def test_original_rom_claim_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("actual_original_rom_source_verification=0","actual_original_rom_source_verification=1",1))

    def test_wrong_last_event_rejected(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,g.replace("event=last original_pair_start=559","event=frame original_pair_start=559"))

    def test_reordered_restart_records_rejected(self):
        h,m,d,g=evidence()
        v=g.splitlines()
        v[-2],v[-3]=v[-3],v[-2]
        with self.assertRaises(ValueError): s.audit_sequence(h,m,d,"\n".join(v))

    def test_bad_schema_rejected(self):
        with self.assertRaises(ValueError): s.parse_line(row(519,100,"on").replace(s.MARKER,"VPD_STAGE363_NUMERIC_DEMO_V1"))



    def test_post_completion_trace_must_remain_stable(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_sequence(h.replace("guest_trace_stable_after_complete=yes",
                                       "guest_trace_stable_after_complete=no"),m,d,g)

    def test_post_completion_count_must_match_trace(self):
        h,m,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_sequence(h.replace("guest_trace_after_complete_count=47",
                                       "guest_trace_after_complete_count=48"),m,d,g)

    def test_terminal_off_screenshot_must_have_zero_cyan_pixels(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            def make_png(name, cyan_count):
                im=Image.new("RGB",(1280,720),(0,0,0))
                for i in range(cyan_count):
                    im.putpixel((1010+(i%195),245+(i//195)),(102,218,239))
                im.save(root/name)
            make_png("screen-demo-start.png",20)
            make_png("screen-cancelled.png",0)
            make_png("screen-restart.png",20)
            make_png("screen-completed.png",0)
            counts=s.screenshot_pixel_counts(root)
            self.assertEqual(counts["screen-completed.png"],0)
            make_png("screen-completed.png",1)
            with self.assertRaises(ValueError):
                s.screenshot_pixel_counts(root)

if __name__ == "__main__":
    unittest.main()
