"""Synthetic stage47 contiguous PRG read grouping tests."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from group_prg_read_ranges import runs
from test_prg_capture_completeness import VerifiedCaptureTests

class ReadRangeTests(VerifiedCaptureTests):
    def test_metadata_and_contiguous_runs(self):
        # Synthetic original fixture contains noncontiguous CPU reads.
        result=runs(self.trace,self.meta,min_run=1)
        self.assertTrue(result['capture_metadata_verified'])
        self.assertEqual(result['unresolved_reads'],1)
        self.assertEqual(len(result['candidate_runs']),3)
        self.assertEqual(runs(self.trace,self.meta,min_run=2)['candidate_runs'],[])
    def test_reject_incomplete_capture(self):
        self.write_meta(dropped=1,complete='no')
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            runs(self.trace,self.meta)
    def test_mapper_event_breaks_adjacent_addresses(self):
        # Fixed bank 15 remains mapped across SELECT, yet stream is not contiguous.
        import csv
        from audit_prg_read_mapping import FIELDS
        with self.trace.open('w',newline='',encoding='utf8') as out:
            writer=csv.writer(out,delimiter='\t')
            writer.writerow(FIELDS)
            writer.writerows([['10','1','READ','E000','unknown','15'],
                              ['10','2','SELECT','8000','06','unknown'],
                              ['10','3','READ','E001','unknown','15']])
        import re
        self.meta.write_text(re.sub(r'events_recorded=[0-9]+',
                                    'events_recorded=3',self.meta.read_text()))
        data=runs(self.trace,self.meta,min_run=2)
        self.assertEqual(data['candidate_runs'],[])
        self.assertEqual(data['discarded_short_runs'],2)
    def test_threshold_bounds(self):
        with self.assertRaisesRegex(ValueError,'min_run'):
            runs(self.trace,self.meta,0)
        with self.assertRaisesRegex(ValueError,'min_run'):
            runs(self.trace,self.meta,10001)

if __name__=='__main__':unittest.main()
