"""Stage44 synthetic MMC3 mapped read audit; no ROM bytes."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_prg_read_mapping import FIELDS,audit
from analyze_dispatch_execution import mapping

def fixture(path):
    selected=r6=r7=None
    events=[]
    for kind,addr,value in [('READ',0x835B,0xAA),('SELECT',0x8000,0x06),
                            ('DATA',0x8001,12),('READ',0x835B,0xBB),
                            ('SELECT',0x8000,0x46),('DATA',0x8001,14),
                            ('READ',0xC906,0xCC),('READ',0x835B,0xDD)]:
        if kind=='SELECT':selected=value
        if kind=='DATA' and selected is not None:
            if selected%8==6:r6=value
            if selected%8==7:r7=value
        bank,_=mapping(addr,selected,r6,r7)
        events.append(['10',str(len(events)+1),kind,f'{addr:04X}',f'{value:02X}',
                       'unknown' if bank is None else str(bank)])
    with path.open('w',newline='',encoding='utf8') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(FIELDS);w.writerows(events)
    return events

class PrgReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'trace.tsv'
        self.rows=fixture(self.path)
    def rewrite(self):
        with self.path.open('w',newline='',encoding='utf8') as f:
            w=csv.writer(f,delimiter='\t');w.writerow(FIELDS);w.writerows(self.rows)
    def test_unknown_and_both_modes(self):
        result=audit(self.path)
        self.assertEqual(result['event_counts']['READ'],4)
        self.assertEqual(result['unresolved_reads'],1)
        self.assertEqual([r['bank'] for r in result['reads']],[None,12,14,14])
        self.assertEqual(result['reads'][1]['physical_prg_offset'],12*8192+0x35B)
        self.assertEqual(result['reads'][2]['physical_prg_offset'],14*8192+0x906)
    def test_forged_bank_refused(self):
        self.rows[3][5]='14';self.rewrite()
        with self.assertRaisesRegex(ValueError,'bank disagrees'):audit(self.path)
    def test_sequence_gap_refused(self):
        self.rows[1][1]='8';self.rewrite()
        with self.assertRaisesRegex(ValueError,'reordered'):audit(self.path)
    def test_non_prg_read_refused(self):
        self.rows[0][3]='0090';self.rewrite()
        with self.assertRaisesRegex(ValueError,'outside'):audit(self.path)
    def test_malformed_fields_refused(self):
        self.rows[0].append('extra');self.rewrite()
        with self.assertRaisesRegex(ValueError,'Malformed'):audit(self.path)
if __name__=='__main__':unittest.main()
