"""Stage55: synthetic 6502 effective address arithmetic only."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("cpu6502_read_address",
    Path(__file__).resolve().parents[1]/"tools"/"6502_read_address.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
calc=module.calculate

class AddressCalculationTests(unittest.TestCase):
    def test_absolute(self):
        r=calc(bytes([0xAD,0x34,0x92]))
        self.assertEqual(r["effective_address"],0x9234)
        self.assertFalse(r["read_executed_proven"])
    def test_absolute_x_page_cross(self):
        r=calc(bytes([0xBD,0xFF,0x81]),x=2)
        self.assertEqual(r["effective_address"],0x8201)
        self.assertTrue(r["page_crossed"])
    def test_absolute_y_wrap(self):
        r=calc(bytes([0xB9,0xFF,0xFF]),y=1)
        self.assertEqual(r["effective_address"],0)
        self.assertFalse(r["prg_window"])
    def test_indirect_y(self):
        r=calc(bytes([0xB1,0xAA]),y=2,zp_low=0xFE,zp_high=0x8F)
        self.assertEqual(r["effective_address"],0x9000)
    def test_unknown_pointer(self):
        self.assertEqual(calc(bytes([0xB1,0xAA]),y=1)["status"],
                         "missing_pointer_or_register")
    def test_missing_index(self):
        self.assertIsNone(calc(bytes([0xBD,0x00,0x80]))["effective_address"])
    def test_unsupported(self):
        self.assertEqual(calc(bytes([0x8D,0,0]))["status"],"unsupported_opcode")
    def test_invalid_length(self):
        with self.assertRaisesRegex(ValueError,"byte count"):
            calc(bytes([0xAD,0x00]))
    def test_invalid_register(self):
        with self.assertRaisesRegex(ValueError,"index"):
            calc(bytes([0xBD,0,0]),x=256)

if __name__=="__main__":unittest.main()
