"""Fail-closed NRO structure checks using independently authored binaries."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from check_nro import check_bytes


def sample(with_assets=True):
    payload = bytearray(0x3000)
    payload[0x10:0x14] = b"NRO0"
    struct.pack_into("<III", payload, 0x14, 0, 0x3000, 0)
    for position, off, size in ((0x20, 0, 0x1000),
                                (0x28, 0x1000, 0x1000),
                                (0x30, 0x2000, 0x1000)):
        struct.pack_into("<II", payload, position, off, size)
    struct.pack_into("<I", payload, 0x38, 0x1000)
    payload[0x40:0x50] = b"synthetic-build!"
    if with_assets:
        aset = bytearray(0x38 + 0x4000)
        aset[:4] = b"ASET"
        struct.pack_into("<QQ", aset, 24, 0x38, 0x4000)
        payload.extend(aset)
    return payload


def mutate(name, modification):
    data = sample()
    modification(data)
    return name, data


class NROStructureTests(unittest.TestCase):
    def test_structural_baseline(self):
        self.assertEqual(check_bytes(sample()), (0x3000, 1))
        self.assertEqual(check_bytes(sample(False)), (0x3000, 0))

    def test_rejects_truncated_and_corrupt_layouts(self):
        modifications = [
            ("short", lambda d: d.__delitem__(slice(0x20, None))),
            ("wrong_magic", lambda d: d.__setitem__(slice(0x10, 0x14), b"NES0")),
            ("bad_version", lambda d: struct.pack_into("<I", d, 0x14, 1)),
            ("bad_flags", lambda d: struct.pack_into("<I", d, 0x1c, 1)),
            ("bad_program_length", lambda d: struct.pack_into("<I", d, 0x18, 0x4000)),
            ("misaligned_size", lambda d: struct.pack_into("<I", d, 0x18, 0x3001)),
            ("text_nonzero", lambda d: struct.pack_into("<I", d, 0x20, 0x1000)),
            ("text_zero", lambda d: struct.pack_into("<I", d, 0x24, 0)),
            ("segment_overlap", lambda d: struct.pack_into("<I", d, 0x28, 0)),
            ("segment_gap", lambda d: struct.pack_into("<I", d, 0x28, 0x2000)),
            ("bad_data_end", lambda d: struct.pack_into("<I", d, 0x34, 0x2000)),
            ("bad_bss", lambda d: struct.pack_into("<I", d, 0x38, 0x7fffffff)),
            ("missing_build_id", lambda d: d.__setitem__(
                slice(0x40, 0x60), bytes(32))),
            ("bad_aset_magic", lambda d: d.__setitem__(
                slice(0x3000, 0x3004), b"NOPE")),
            ("bad_aset_version", lambda d: struct.pack_into(
                "<I", d, 0x3004, 1)),
            ("asset_truncated", lambda d: d.__delitem__(slice(-200, None))),
            ("asset_in_header", lambda d: struct.pack_into(
                "<Q", d, 0x3000 + 24, 0x10)),
            ("asset_too_large", lambda d: struct.pack_into(
                "<Q", d, 0x3000 + 32, 0xfffffff)),
            ("asset_overlap", lambda d: struct.pack_into(
                "<QQ", d, 0x3000 + 8, 0x38, 0x100)),
            ("missing_asset_size", lambda d: struct.pack_into(
                "<Q", d, 0x3000 + 32, 0)),
            ("trailing_bytes", lambda d: d.extend(b"JUNK")),
        ]
        for name, change in modifications:
            with self.subTest(error=name):
                data = sample()
                change(data)
                with self.assertRaises(ValueError):
                    check_bytes(data)


if __name__ == "__main__":
    unittest.main()
