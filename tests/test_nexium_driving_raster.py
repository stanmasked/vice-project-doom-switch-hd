import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_nexium_driving_raster import audit

def record(seq, event, frame, car_x, health, cooldown):
    return (f"VPD_DRIVING_GUEST_V1 seq={seq} event={event} "
            f"frame={frame} car_x={car_x} health={health} cooldown={cooldown}")
def raster(seq, frame, car_x, health, flash, car, hud):
    return (f"VPD_DRIVING_RASTER_V1 seq={seq} frame={frame} "
            f"car_x={car_x} health={health} flash={flash} "
            f"car_pixel={car} hud_pixel={hud} car_expected={car} "
            f"hud_expected={hud} source=libnx_drawScene same_frame=yes "
            f"original_assets_used=0")
class TestRasterAuditor(unittest.TestCase):
    def fixture(self, folder):
        self.control=[
            record(1,"enter",0,640,5,0),
            record(2,"right_throttle",1,642,5,0),
            record(3,"left_brake",8,634,5,0),
            record(4,"impact",52,640,4,45),
            record(5,"exit",60,640,4,37),
        ]
        self.raster=[
            raster(2,1,642,5,0,"ff3f2fa3","ff5b55d3"),
            raster(4,52,640,4,1,"ff7ec8e8","ff271911"),
        ]
        self.write(folder)
    def write(self, folder):
        (folder/"guest-driving-witness.txt").write_text("\n".join(self.control)+"\n")
        (folder/"guest-driving-raster-witness.txt").write_text("\n".join(self.raster)+"\n")
    def test_valid_synthetic_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.fixture(p);audit(p)
    def test_corrupt_hud_pixel_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.fixture(p)
            self.raster[1]=self.raster[1].replace("hud_pixel=ff271911",
                                                  "hud_pixel=ff5b55d3")
            self.write(p)
            with self.assertRaises(ValueError):audit(p)
    def test_wrong_guest_frame_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.fixture(p)
            self.raster[1]=self.raster[1].replace("frame=52", "frame=53")
            self.write(p)
            with self.assertRaises(ValueError):audit(p)
    def test_missing_guest_raster_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.fixture(p);self.raster.pop();self.write(p)
            with self.assertRaises(ValueError):audit(p)
if __name__=="__main__":unittest.main()
