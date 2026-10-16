"""CI-safe synthetic test cases: no copyrighted ROM or original CHR data."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from inspect_rom import parse_rom, tile_indices, render_page  # noqa: E402


def synthetic_mmc3_rom():
    """Return fake NES 2.0 mapper-4 ROM with one PRG and one CHR unit."""
    header = bytearray(16)
    header[0:4] = b'NES\x1a'
    header[4] = 1  # 16 KiB PRG
    header[5] = 1  # 8 KiB CHR
    header[6] = 0x40  # Mapper 4 lower nibble
    header[7] = 0x08  # NES 2.0 marker
    fake_prg = bytes(16 * 1024)
    fake_chr = (bytes([0xff] * 8 + [0] * 8) + bytes([0] * 8 + [0xff] * 8)) * 256
    assert len(fake_chr) == 8192
    return bytes(header) + fake_prg + fake_chr


class SyntheticRomTests(unittest.TestCase):
    def test_parse_synthetic_mmc3(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'fixture.nes'
            path.write_bytes(synthetic_mmc3_rom())
            info = parse_rom(path)
            self.assertTrue(info['nes2'])
            self.assertEqual(info['mapper'], 4)
            self.assertEqual(len(info['prg']), 16 * 1024)
            self.assertEqual(len(info['chr']), 8 * 1024)
            self.assertEqual(info['trailing'], 0)

    def test_tile_planes(self):
        tile = bytes([0b10000000] + [0] * 7 + [0b01000000] + [0] * 7)
        decoded = tile_indices(tile)
        self.assertEqual(decoded[:8], [1, 2, 0, 0, 0, 0, 0, 0])
        self.assertEqual(len(decoded), 64)

    def test_render_one_synthetic_page(self):
        empty = bytes(16)
        im = render_page([empty] * 256, size=2)
        self.assertEqual(im.size, (256, 256))
        self.assertEqual(len(im.getcolors()), 1)

    def test_bad_header(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bad.nes'
            path.write_bytes(b'not a rom')
            with self.assertRaises(ValueError):
                parse_rom(path)


if __name__ == '__main__':
    unittest.main()
