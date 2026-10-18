"""Synthetic-only stage40 RAM/MMC3 candidate inventory tests."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from inventory_stage40_candidates import inventory
from test_dispatch_execution import fixture

def anchors(path, rows):
    with path.open('w',newline='',encoding='utf8') as f:
        writer=csv.writer(f)
        writer.writerow(['video_frame','trace_frame','label'])
        writer.writerows(rows)
    return path

class CandidateInventoryTests(unittest.TestCase):
    def test_write_values_not_prewrite_samples(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            trace, meta=fixture(root)
            data=inventory(trace,meta,anchors(root/'anchors.csv',[(10,100,'start')]),radius=0)
            self.assertEqual(data['anchor_count'],1)
            self.assertEqual(
                {v['address']:v['observed_write_values'] for v in data['ram_write_candidates']},
                {'$00AA':['76'],'$00AB':['83']})
            self.assertEqual(len(data['mapper_events_in_windows']),4)
            self.assertEqual(data['outside_capture_anchors'],[])

    def test_outside_capture_cannot_generate_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            trace,meta=fixture(root)
            data=inventory(trace,meta,anchors(root/'anchors.csv',[(999,200,'unrecorded')]),radius=0)
            self.assertEqual(data['ram_write_candidates'],[])
            self.assertEqual(data['outside_capture_anchors'],['unrecorded'])

    def test_invalid_anchor_rejected_by_existing_audit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            trace,meta=fixture(root)
            with self.assertRaisesRegex(ValueError,'increase strictly'):
                inventory(trace,meta,anchors(root/'anchors.csv',
                          [(10,100,'a'),(11,99,'b')]))

if __name__=='__main__':
    unittest.main()
