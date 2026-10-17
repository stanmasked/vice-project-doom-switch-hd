"""ROM-free MMC3 frame-log tests; all register traces are invented."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_mmc3_frame_log import analyze,read_events,chr_1k_banks

class FrameLogTests(unittest.TestCase):
    def test_chronology_and_inversion(self):
        events=[]
        for i,value in enumerate((3,6,8,9,10,11)):
            events.extend(((10,0x8000,i|0x80),(10,0x8001,value)))
        events.extend(((11,0x2006,0x20),(11,0x2007,3),
                       (11,0x8000,0),(11,0x8001,4)))
        r=analyze(events)
        self.assertEqual(r['event_frame_count'],2)
        self.assertEqual(r['total_chr_writes'],7)
        self.assertEqual(r['mapping_available_for_frames'],2)
        self.assertEqual(r['frames'][0]['ppu_1k_bank_mapping'],[8,9,10,11,2,3,6,7])
        self.assertEqual(r['frames'][1]['ppu_1k_bank_mapping'],[4,5,6,7,8,9,10,11])
        self.assertEqual(r['frames'][1]['ppu_port_writes'],2)

    def test_ppu_port_count_includes_mirror_addresses(self):
        events=[(2,0x2008,0x90),(2,0x3FF9,0x1E),
                (2,0x200D,0x22),(2,0x3456,0x20),
                (2,0x3FFF,0x11),(2,0x3FFA,0),
                (2,0xA000,1)]
        report=analyze(events)
        self.assertEqual(report['frames'][0]['ppu_port_writes'],5)

    def test_all_mmc3_bank_register_mirrors(self):
        events=[(7,0x8002,0x80),(7,0x8003,4),
                (7,0x9FFE,0x85),(7,0x9FFF,9),
                (7,0xA002,1),(7,0xBFFF,0),
                (7,0xC006,10),(7,0xDFFF,11),
                (7,0xE00C,12),(7,0xFFFF,13)]
        result=analyze(events)
        self.assertEqual(result['frames'][0]['mapper_select_writes'],2)
        self.assertEqual(result['total_chr_writes'],2)
        self.assertEqual(result['frames'][0]['chr_registers'][0],4)
        self.assertEqual(result['frames'][0]['chr_registers'][5],9)
        self.assertEqual(result['frames'][0]['chr_inversion'],True)

    def test_unobserved_registers_and_data(self):
        r=analyze(((1,0x8001,13),(1,0x8000,0x85),(1,0x8001,19)))
        self.assertIsNone(r['frames'][0]['ppu_1k_bank_mapping'])
        self.assertEqual(r['unpaired_bank_data_writes'],1)
        self.assertEqual(r['frames'][0]['chr_registers'][5],19)
        self.assertTrue(r['frames'][0]['chr_inversion'])

    def test_tsv_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'capture.tsv'
            f.write_text('frame\taddress\tvalue\n3\t8000\t80\n3\t8001\t0F\n')
            self.assertEqual(list(read_events(f)),[(3,0x8000,0x80),(3,0x8001,15)])
            f.write_text('frame\taddress\tvalue\n3\t8000\tGG\n')
            with self.assertRaisesRegex(ValueError,'Invalid register'):
                list(read_events(f))
            f.write_text('wrong header\n')
            with self.assertRaisesRegex(ValueError,'header'):
                list(read_events(f))

    def test_bank_wrapping_and_out_of_order(self):
        self.assertEqual(chr_1k_banks([255]*6,False),
                         [126,127,126,127,127,127,127,127])
        with self.assertRaises(ValueError):analyze([],127)
        self.assertTrue(analyze(((11,0x8000,0),(10,0x8001,3)))['out_of_order_frame_numbers'])

if __name__=='__main__':unittest.main()
