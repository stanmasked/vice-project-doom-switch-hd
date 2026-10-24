"""Stage364: fabricated-only host + guest binary pixel evidence auditing."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import audit_nexium_stage364_scroll as s


def guest(event,frame,guestframe,shift,**replace):
    data=dict(event=event,original_pair_start=str(frame),guest_frame=str(guestframe),
              image_shift=str(shift),panel_pixel=s.EXPECTED_PANEL,
              edge_pixel=s.EXPECTED_PIXEL,demo_glyph_pixel=s.EXPECTED_PIXEL,
              platform_fp="0123456789abcdef",**s.REQUIRED)
    data.update(replace)
    return s.MARKER+" "+" ".join(k+"="+v for k,v in data.items())


def evidence():
    host="\n".join(("physical_keyboard_chord=R+T+Q Switch=ZL+ZR+L",
        "native_driving_enter=yes","guest_on=yes","guest_last=yes",
        "STAGE364_REAL_NEXIUM_SCROLL_DEMO_GUEST_EVENTS_OBSERVED"))
    drive="VPD_DRIVING_GUEST_V1 seq=1 event=enter key=driving"
    rows="\n".join((guest("on",519,7,3),guest("last",559,47,5)))
    return host,drive,rows


class Stage364OnlyFabricatedTests(unittest.TestCase):
    def test_strict_guest_on_last(self):
        self.assertTrue(s.audit_evidence(*evidence())["real_native_guest_on_and_last"])

    def test_requires_physical_key_record(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_evidence(h.replace("Q Switch","Z Switch"),d,g)

    def test_guest_manual_drive_entry_required(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_evidence(h,d.replace("seq=1","seq=2"),g)

    def test_guest_report_absent_cannot_be_replaced_by_host_events(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):s.audit_evidence(h,d,"")

    def test_host_only_report_fails(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):s.audit_evidence(h.replace("guest_last=yes","guest_last=no"),d,g)

    def test_early_finished_numeric_window_rejected(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):s.audit_evidence(h,d,g.replace("guest_frame=47","guest_frame=46"))

    def test_original_source_claiming_proven_is_rejected(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_evidence(h,d,g.replace("original_game_physics_proven=0","original_game_physics_proven=1"))

    def test_endpoints_do_not_prove_universal_physics(self):
        result=s.audit_evidence(*evidence())
        self.assertFalse(result["original_camera_or_vehicle_physics_proven"])

    def test_cannot_invent_original_raster_data(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_evidence(h,d,g.replace("actual_original_rom_source_verification=0",
                                           "actual_original_rom_source_verification=1"))

    def test_wrong_color_not_a_successful_nro_pixel(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_evidence(h,d,g.replace(s.EXPECTED_PIXEL,"00000000"))

    def test_wrong_demonstration_last_shift_rejected(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_evidence(h,d,g.replace("image_shift=5","image_shift=4"))

    def test_wrong_stage363_pair_start_rejected(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_evidence(h,d,g.replace("original_pair_start=559","original_pair_start=560"))

    def test_duplicates_rejected(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_evidence(h,d,g+"\n"+guest("last",559,47,5))

    def test_wrong_guest_platform_fingerprint_rejected(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_evidence(h,d,g.replace("platform_fp=0123456789abcdef",
                                           "platform_fp=ffffffffffffffff",1))

    def test_reordered_events_rejected(self):
        h,d,g=evidence()
        with self.assertRaises(ValueError):
            s.audit_evidence(h,d,"\n".join(reversed(g.splitlines())))

    def test_malformed_duplicated_guest_fields_rejected(self):
        row=guest("on",519,7,3)+" event=on"
        with self.assertRaises(ValueError):s.parse_line(row)

    def test_malformed_bytes_not_a_numeric_frame(self):
        with self.assertRaises(ValueError):
            s.parse_line(guest("on",519,7,3,guest_frame="NaN"))


if __name__=="__main__":
    unittest.main()
