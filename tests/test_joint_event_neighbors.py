"""Stage51 synthetic adjacency checks; no original ROM."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from joint_event_neighbors import neighbors
from test_joint_trace_validation import JointTraceValidationTests

class NeighborTests(JointTraceValidationTests):
    def test_nearest_is_not_causality(self):
        data=neighbors(self.trace,self.meta,max_gap=2)
        self.assertEqual(len(data['candidates']),1)
        self.assertEqual(data['candidates'][0]['exec_seq'],4)
        self.assertFalse(data['causality_proven'])
    def test_mapper_change_blocks(self):
        self.rows[3][2]='SELECT'
        self.rows[3][3]='8000'
        self.rows[3][4]='06'
        self.write_rows()
        result=neighbors(self.trace,self.meta)
        self.assertEqual(result['candidates'],[])
        self.assertEqual(result['excluded_read_counts']['mapper_intervened'],1)
    def test_max_gap_rejects_nonpositive(self):
        with self.assertRaisesRegex(ValueError,'max_gap'):
            neighbors(self.trace,self.meta,max_gap=0)
    def test_incomplete_refused(self):
        self.meta.write_text(self.meta.read_text().replace('events_dropped=0','events_dropped=1').replace('complete=yes','complete=no'))
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            neighbors(self.trace,self.meta)
if __name__=='__main__':unittest.main()
