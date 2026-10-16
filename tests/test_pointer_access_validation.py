"""Synthetic-only stage43 pointer-log audit regression tests."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from validate_pointer_access import validate,FIELDS

class PointerValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder=Path(self.temp.name)
        self.log=folder/'stage41_pointer_access.tsv'
        self.meta=folder/'stage41_pointer_access.meta.txt'
        self.rows=[
            ['50','1','READ','00AA','unknown','11','22','33','44'],
            ['50','2','WRITE','00AB','99','11','22','33','44']]
        self.write_rows()
        self.meta.write_text('\n'.join([
            'format=vice_stage41_pointer_access_v1',
            'rom_md5='+'a'*32,
            'events_recorded=2','events_dropped=0','callback_errors=0','complete=yes',
            'read_value_provenance=address_only_fceux_zero_sentinel',
            'execution_pc=not_instrumented',
            'meaning=pointer_byte_access_not_dereference'])+'\n',encoding='utf8')

    def write_rows(self):
        with self.log.open('w',newline='',encoding='utf8') as f:
            writer=csv.writer(f,delimiter='\t')
            writer.writerow(FIELDS);writer.writerows(self.rows)

    def test_valid_but_never_rom_evidence(self):
        result=validate(self.log,self.meta)
        self.assertTrue(result['complete'])
        self.assertEqual(result['ram_byte_reads'],1)
        self.assertEqual(result['ram_byte_writes'],1)
        self.assertFalse(result['prg_rom_reads_observed'])
        self.assertFalse(result['effective_addresses_observed'])

    def test_read_callback_byte_fabrication_rejected(self):
        self.rows[0][4]='11';self.write_rows()
        with self.assertRaisesRegex(ValueError,'provenance'):
            validate(self.log,self.meta)

    def test_callback_error_marks_incomplete(self):
        self.meta.write_text(self.meta.read_text().replace(
            'callback_errors=0','callback_errors=1').replace('complete=yes','complete=no'))
        self.assertFalse(validate(self.log,self.meta)['complete'])

    def test_gaps_invalid(self):
        self.rows[1][1]='3';self.write_rows()
        with self.assertRaisesRegex(ValueError,'sequence'):validate(self.log,self.meta)

    def test_rom_address_rejected(self):
        self.rows[0][3]='8000';self.write_rows()
        with self.assertRaisesRegex(ValueError,'Unexpected RAM'):validate(self.log,self.meta)

    def test_incomplete_is_explicit(self):
        s=self.meta.read_text().replace('events_dropped=0','events_dropped=1').replace('complete=yes','complete=no')
        self.meta.write_text(s)
        self.assertFalse(validate(self.log,self.meta)['complete'])

    def test_forged_provenance_rejected(self):
        self.meta.write_text(self.meta.read_text().replace('not_instrumented','tracked'))
        with self.assertRaisesRegex(ValueError,'provenance'):validate(self.log,self.meta)

    def test_bad_count_rejected(self):
        self.meta.write_text(self.meta.read_text().replace('events_recorded=2','events_recorded=3'))
        with self.assertRaisesRegex(ValueError,'count mismatch'):validate(self.log,self.meta)

if __name__=='__main__':unittest.main()
