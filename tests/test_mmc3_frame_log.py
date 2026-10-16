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
