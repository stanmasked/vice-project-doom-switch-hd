"""Mutation tests of raster *auditor*. Synthetic images are NOT emulator proof."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "guard_live_raster",ROOT/"tools/audit_nexium_guard_live_raster.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

W,H=1280,720
ANCHORS={"strike_frame":203,"defeat_frame":219,
         "strike_x":360,"defeat_x":358}


def fixture(include_guard=True):
    data=bytearray(bytes((25,40,65))*(W*H))
    # Palette texture is synthetic test material, never actual NeXium data.
    for y in range(570,625):
        for x in range(320,458):
            if (x+y)%59==0:
                i=3*(y*W+x)
                data[i:i+3]=bytes((100+(x%6)*11,60+(y%7)*8,70))
    if include_guard:
        for y in range(audit.GUARD_Y+11,audit.GUARD_Y+21):
            for x in range(ANCHORS["strike_x"]+5,ANCHORS["strike_x"]+20):
                i=3*(y*W+x)
                data[i:i+3]=audit.ALERT_COLOR
    return b"P6\n1280 720\n255\n"+bytes(data)


class LiveRasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=fixture(True)
        cls.after=fixture(False)

    def test_alert_guard_disappears_at_actual_map_coordinates(self):
        out=audit.evaluate(self.before,self.after,ANCHORS)
        self.assertGreaterEqual(out["guard_pixels_strike"],120)
        self.assertEqual(out["guard_pixels_defeat"],0)

    def test_wrong_order_stale_or_blank_raster_fails(self):
        for a,b in ((self.after,self.after),(self.after,self.before),
                    (self.before,self.before)):
            with self.subTest(a=len(a),b=len(b)), self.assertRaises(ValueError):
                audit.evaluate(a,b,ANCHORS)
        blank=b"P6\n1280 720\n255\n"+bytes(3*W*H)
        with self.assertRaises(ValueError):
            audit.evaluate(blank,self.after,ANCHORS)

    def test_wrong_pixel_payload_and_guard_viewport(self):
        bad=[
            b"",self.before[:-1],self.before+b"x",
            self.before.replace(b"P6",b"P3",1),
            self.before.replace(b"1280 720",b"1280 719",1),
            self.before.replace(b"255",b"65535",1),
        ]
        for index,item in enumerate(bad):
            with self.subTest(index=index),self.assertRaises(ValueError):
                audit.evaluate(item,self.after,ANCHORS)
        altered={**ANCHORS,"strike_x":840}
        with self.assertRaisesRegex(ValueError,"alerted guard"):
            audit.evaluate(self.before,self.after,altered)

    def test_guest_event_linkage_fails_when_absent_or_forged(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            before=(
                "VPD_ROMFREE_GUARD_LIVE_V1 seq=1 event=alert frame=143 "
                "player_x=25600 guard_x=61696\n"
                "VPD_ROMFREE_GUARD_LIVE_V1 seq=2 event=strike frame=203 "
                "player_x=52224 guard_x=57344\n"
            )
            defeat=(
                "VPD_ROMFREE_GUARD_LIVE_DEFEAT_V1 seq=1 event=fire frame=208\n"
                "VPD_ROMFREE_GUARD_LIVE_DEFEAT_V1 seq=3 event=defeat "
                "frame=219 player_x=52736 guard_x=57344\n"
            )
            (folder/"guest-guard-live-witness.txt").write_text(before)
            (folder/"guest-guard-live-defeat-witness.txt").write_text(defeat)
            coords=audit.load_anchors(folder)
            self.assertEqual((coords["strike_x"],coords["defeat_x"]),(360,356))
            with self.assertRaisesRegex(ValueError,"screenshots absent"):
                audit.audit(folder)
            (folder/"guest-guard-live-defeat-witness.txt").write_text(
                defeat.replace("event=defeat","event=impact"))
            with self.assertRaisesRegex(ValueError,"linked"):
                audit.load_anchors(folder)
            (folder/"guest-guard-live-defeat-witness.txt").write_text(
                defeat.replace("frame=219","frame=202"))
            with self.assertRaisesRegex(ValueError,"order"):
                audit.load_anchors(folder)

if __name__=="__main__":
    unittest.main()
