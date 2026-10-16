"""ROM-free stage54 strict CPU context validation tests."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from validate_joint_cpu_context import validate,FIELDS

class JointContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        d=Path(self.temp.name)
        self.trace=d/'stage53_joint_context.tsv'
        self.meta=d/'stage53_joint_context.meta.txt'
        self.rows=[
            ['19','1','EXEC','835B','unknown','unknown','01','02','03','04','unknown'],
            ['19','2','SELECT','8000','06','unknown','01','02','03','04','unknown'],
            ['19','3','DATA','8001','0C','12','01','02','03','04','unknown'],
            ['19','4','READ','835C','AB','12','01','02','03','04','unknown']
        ]
        self.write_rows()
        self.meta.write_text('\n'.join([
            'format=vice_stage53_joint_context_v1','events_recorded=4',
            'events_dropped=0','complete=yes','initial_mmc3_mode=unknown',
            'register_provenance=callback_time_optional_samples',
            'register_api=memory.getregister',
            'rom_header_profile=ines_mapper4_prg128k',
            'rom_md5_pin=not_supplied',
            'callback_contract=address_size_value_v1',
            'callback_errors=0',
            'effective_address=not_proven','read_causality=not_proven'])+'\n')
    def write_rows(self):
        with self.trace.open('w',newline='',encoding='utf8') as f:
            w=csv.writer(f,delimiter='\t')
            w.writerow(FIELDS);w.writerows(self.rows)
    def test_valid_and_no_causality(self):
        result=validate(self.trace,self.meta)
        self.assertEqual(result['events'],4)
        self.assertEqual(result['unknown_register_samples']['p'],4)
        self.assertFalse(result['read_causality_proven'])
    def test_bad_mapper_bank(self):
        self.rows[3][5]='14';self.write_rows()
        with self.assertRaisesRegex(ValueError,'mapping'):validate(self.trace,self.meta)
    def test_invalid_register(self):
        self.rows[3][6]='ZZ';self.write_rows()
        with self.assertRaisesRegex(ValueError,'Invalid'):validate(self.trace,self.meta)
    def test_event_gap(self):
        self.rows[3][1]='6';self.write_rows()
        with self.assertRaisesRegex(ValueError,'order'):validate(self.trace,self.meta)
    def test_overflow(self):
        self.meta.write_text(self.meta.read_text().replace('events_dropped=0','events_dropped=1').replace('complete=yes','complete=no'))
        with self.assertRaisesRegex(ValueError,'Incomplete'):validate(self.trace,self.meta)
    def test_metadata_mismatch(self):
        self.meta.write_text(self.meta.read_text().replace('events_recorded=4','events_recorded=5'))
        with self.assertRaisesRegex(ValueError,'count mismatch'):validate(self.trace,self.meta)
    def test_legacy_capture_missing_register_api_rejected(self):
        self.meta.write_text(self.meta.read_text().replace(
            'register_api=memory.getregister\n',''))
        with self.assertRaisesRegex(ValueError,'provenance'):
            validate(self.trace,self.meta)

    def test_legacy_callback_contract_rejected(self):
        self.meta.write_text(self.meta.read_text().replace(
            'callback_contract=address_size_value_v1\\n',''))
        with self.assertRaisesRegex(ValueError,'provenance'):
            validate(self.trace,self.meta)

    def test_callback_error_refused(self):
        self.meta.write_text(self.meta.read_text().replace(
            'callback_errors=0','callback_errors=1').replace(
            'complete=yes','complete=no'))
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            validate(self.trace,self.meta)

    def test_missing_rom_preflight_rejected(self):
        self.meta.write_text(self.meta.read_text().replace(
            'rom_header_profile=ines_mapper4_prg128k\n',''))
        with self.assertRaisesRegex(ValueError,'provenance'):
            validate(self.trace,self.meta)

    def test_invalid_rom_pin_rejected(self):
        self.meta.write_text(self.meta.read_text().replace(
            'rom_md5_pin=not_supplied','rom_md5_pin=untrusted'))
        with self.assertRaisesRegex(ValueError,'ROM pin'):
            validate(self.trace,self.meta)

    def test_forged_provenance(self):
        self.meta.write_text(self.meta.read_text().replace('read_causality=not_proven','read_causality=proven'))
        with self.assertRaisesRegex(ValueError,'provenance'):validate(self.trace,self.meta)
if __name__=='__main__':unittest.main()
