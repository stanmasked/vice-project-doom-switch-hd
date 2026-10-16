"""Stage56 synthetic-only read candidate comparison."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from compare_6502_read_candidates import compare
from test_joint_cpu_context_validation import JointContextTests

class Stage56Tests(JointContextTests):
    def test_matching_address_does_not_prove_causality(self):
        out=compare(self.trace,self.meta,exec_seq=1,opcode_hex="AD5C83")
        # SELECT/DATA intervene; never join across mapper updates.
        self.assertEqual(out["candidate_reads"],[])
        self.assertEqual(out["search_stopped_by"],"execution_or_mapper_event")
        self.assertFalse(out["causality_proven"])

    def test_direct_neighbor_match_remains_hypothesis(self):
        self.rows=[
            ["19","1","EXEC","835B","unknown","unknown","01","02","03","04","unknown"],
            ["19","2","READ","835C","unknown","unknown","01","02","03","04","unknown"]]
        self.write_rows()
        self.meta.write_text(self.meta.read_text().replace("events_recorded=4","events_recorded=2"))
        out=compare(self.trace,self.meta,exec_seq=1,opcode_hex="AD5C83")
        self.assertEqual(len(out["candidate_reads"]),1)
        self.assertEqual(out["candidate_reads"][0]["classification"],"address_match_only")
        self.assertFalse(out["candidate_reads"][0]["instruction_caused_read_proven"])

    def test_unresolved_index_cannot_match(self):
        self.rows[0][7]="unknown"
        self.write_rows()
        out=compare(self.trace,self.meta,exec_seq=1,opcode_hex="BD5A83")
        self.assertEqual(out["calculation"]["status"],"missing_index_register")
        self.assertEqual(out["candidate_reads"],[])

    def test_wrong_event_number_refused(self):
        with self.assertRaisesRegex(ValueError,"EXEC"):
            compare(self.trace,self.meta,exec_seq=2,opcode_hex="AD5C83")

    def test_incomplete_capture_refused(self):
        self.meta.write_text(self.meta.read_text().replace("events_dropped=0","events_dropped=1").replace("complete=yes","complete=no"))
        with self.assertRaisesRegex(ValueError,"Incomplete"):
            compare(self.trace,self.meta,exec_seq=1,opcode_hex="AD5C83")

if __name__=="__main__":unittest.main()
