"""Stage50 joint trace validation against invented FCEUX events."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from validate_joint_trace import validate,FIELDS

class JointTraceValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.trace=root/'stage49_joint.tsv'
        self.meta=root/'stage49_joint.meta.txt'
        self.rows=[
            ['9','1','EXEC','835B','unknown','unknown'],
            ['9','2','SELECT','8000','06','unknown'],
            ['9','3','DATA','8001','0C','12'],
            ['9','4','EXEC','835B','unknown','12'],
            ['9','5','READ','835C','AA','12']]
        self.write_rows()
        self.meta.write_text('\n'.join([
            'format=vice_stage49_joint_v1','events_recorded=5',
            'events_dropped=0','complete=yes',
            'exec_context=selected_pc_hooks_only',
            'read_causality=not_proven'])+'\n',encoding='utf8')
    def write_rows(self):
        with self.trace.open('w',newline='',encoding='utf8') as f:
            writer=csv.writer(f,delimiter='\t')
            writer.writerow(FIELDS);writer.writerows(self.rows)
    def test_valid_order_without_causal_claim(self):
        result=validate(self.trace,self.meta)
        self.assertEqual(result['unknown_bank_reads'],0)
        self.assertEqual(result['counts']['READ'],1)
        self.assertFalse(result['cpu_read_causality_proven'])
    def test_wrong_bank_rejected(self):
        self.rows[4][5]='14';self.write_rows()
        with self.assertRaisesRegex(ValueError,'bank mismatch'):validate(self.trace,self.meta)
    def test_missing_sequence_rejected(self):
        self.rows[4][1]='6';self.write_rows()
        with self.assertRaisesRegex(ValueError,'Event sequence'):validate(self.trace,self.meta)
    def test_dropped_capture_rejected(self):
        self.meta.write_text(self.meta.read_text().replace('events_dropped=0','events_dropped=1').replace('complete=yes','complete=no'))
        with self.assertRaisesRegex(ValueError,'Incomplete'):validate(self.trace,self.meta)
    def test_forged_provenance_rejected(self):
        self.meta.write_text(self.meta.read_text().replace('not_proven','proven'))
        with self.assertRaisesRegex(ValueError,'provenance'):validate(self.trace,self.meta)
    def test_invalid_exec_refused(self):
        self.rows[0][3]='E123';self.write_rows()
        with self.assertRaisesRegex(ValueError,'Invalid EXEC'):validate(self.trace,self.meta)

if __name__=='__main__':unittest.main()
