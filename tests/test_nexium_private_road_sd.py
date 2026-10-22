"""Only manufactured CRC32 source numeric records and guest text."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from generate_synthetic_road_bundle import synthetic_bundle
from audit_nexium_private_road_sd import validate

GOOD=("VPD_PRIVATE_ROAD_SD_V1 mounted=1 loaded=1 samples=37 "
      "first_frame=600 last_frame=920 source=nro_startup "
      "original_art=no camera_collision_proven=no\n")
class SyntheticSdStartupTests(unittest.TestCase):
    def test_source_free_native_startup(self):
        validate(GOOD,synthetic_bundle())
    def bad(self,record=None,bundle=None):
        with self.assertRaises(ValueError):
            validate(GOOD if record is None else record,
                     synthetic_bundle() if bundle is None else bundle)
    def test_missing_sd(self):
        self.bad(GOOD.replace("loaded=1","loaded=0"))
    def test_wrong_count(self):
        self.bad(GOOD.replace("samples=37","samples=36"))
    def test_wrong_frame(self):
        self.bad(GOOD.replace("last_frame=920","last_frame=912"))
    def test_missing_native_provenance(self):
        self.bad(GOOD.replace("source=nro_startup","source=host_script"))
    def test_unexpected_media_metadata(self):
        self.bad(GOOD.strip()+" original_rom=private.nes\n")
    def test_duplicate_guest_record(self):
        self.bad(GOOD+GOOD)
    def test_truncated_bundle(self):
        self.bad(bundle=synthetic_bundle()[:-1])
    def test_tampered_bundle(self):
        b=bytearray(synthetic_bundle());b[-1]^=1;self.bad(bundle=bytes(b))
    def test_wrong_crc(self):
        b=bytearray(synthetic_bundle());b[12]^=1;self.bad(bundle=bytes(b))
    def test_existing_reference_anchors_preserved(self):
        self.assertEqual(len(synthetic_bundle()),164)
        self.assertEqual(synthetic_bundle()[:8],b"VPDROAD1")
if __name__=="__main__":unittest.main()
