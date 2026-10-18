"""Stage122 regression: do not certify carry-prefetched first 16 pixels.

The native Stage119/120/121 witnesses use pixels X=32..47 after the
two-record scanline carry proved by Stage115. Test data are generated
from independent Mapper-4 synthetic ROMs only.
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from make_stage119_nametable_rom import make_rom, nametable_init

HEADER = ROOT / "tools" / "vpd_newppu_raw_step_probe.h"
PALETTE = (0x0F, 0x16, 0x27, 0x30,
           0x0F, 0x11, 0x21, 0x31,
           0x0F, 0x12, 0x22, 0x32,
           0x0F, 0x13, 0x23, 0x33)


class PrefetchWindow(unittest.TestCase):
    def test_all_three_native_consumers_sample_after_carry(self):
        source = HEADER.read_text()
        for namespace in ("a", "old"):
            prefix = ("a.writes" if namespace == "a" else "old.writes")
            expression = (
                "const bool before=sl==" + namespace + ".sl1+1 "
                "&& x>=32 && x<48;"
            )
            second = (
                "const bool after=" + prefix + "==2 && "
                "sl==" + namespace + ".sl2+1 && x>=32 && x<48;"
            )
            self.assertIn(expression, source)
            self.assertIn(second, source)
        self.assertEqual(source.count("x>=32 && x<48;"), 4)
        self.assertNotIn("x<16;", source[source.index("struct NTIdentityAudit"):
                                         source.index("// Stage109 synthetic-only")])

    def test_attribute_palette_initialization_has_16_real_ppu_writes(self):
        init = nametable_init()
        offset = bytes((0xA9, 0x3F, 0x8D, 6, 0x20,
                        0xA9, 0, 0x8D, 6, 0x20))
        self.assertEqual(init.count(offset), 1)
        start = init.index(offset) + len(offset)
        writes = b"".join(
            bytes((0xA9, color, 0x8D, 7, 0x20)) for color in PALETTE)
        self.assertEqual(init[start:start+len(writes)], writes)
        self.assertEqual(len(writes), 80)
        # CHR pixel 0 is transparent; color3 from palette0 differs from
        # color3 from attribute-selected palette1 under fixture setup.
        self.assertNotEqual(PALETTE[3], PALETTE[7])
        self.assertEqual(PALETTE[4], 0x0F)

    def test_positive_and_uniform_chr_control_share_prg_and_palette(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder)/"distinct.nes", Path(folder)/"uniform.nes"
            make_rom(a, first=3)
            make_rom(b, first=3, differentiated=False)
            dat, control = a.read_bytes(), b.read_bytes()
            self.assertEqual(dat[:32784], control[:32784])
            self.assertNotEqual(dat[32784:], control[32784:])
            self.assertIn(nametable_init(), dat[:32784])


if __name__ == "__main__":
    unittest.main()
