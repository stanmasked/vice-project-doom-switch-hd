"""Stage70: cross-generation READ provenance regressions, ROM-free.

All callbacks/ROM bytes here are synthetic. These are separate test fixtures;
we never claim they represent a single authentic FCEUX session.
"""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_prg_read_mapping import audit_verified
from validate_joint_trace import validate as validate49
from validate_joint_cpu_context import validate as validate53
from validate_pointer_access import validate as validate41
from compare_6502_read_candidates import compare
from group_prg_read_ranges import runs
from test_prg_capture_completeness import VerifiedCaptureTests
from test_joint_trace_validation import JointTraceValidationTests
from test_joint_cpu_context_validation import JointContextTests
from test_pointer_access_validation import PointerValidationTests


class ReadProvenanceEndToEndTests(unittest.TestCase):
    def prepare(self, fixture_type):
        fixture = fixture_type()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_stage41_unknown_read_and_independent_ram_snapshot(self):
        fixture = self.prepare(PointerValidationTests)
        result = validate41(fixture.log, fixture.meta)
        self.assertEqual(fixture.rows[0][4], 'unknown')
        self.assertEqual(fixture.rows[0][5:9], ['11', '22', '33', '44'])
        self.assertFalse(result['read_callback_values_proven'])
        self.assertFalse(result['prg_rom_reads_observed'])

    def test_stage45_address_mapping_without_read_bytes(self):
        fixture = self.prepare(VerifiedCaptureTests)
        result = audit_verified(fixture.trace, fixture.meta)
        self.assertFalse(result['read_values_proven'])
        self.assertEqual(len(result['reads']), 4)
        self.assertEqual(result['reads'][1]['physical_prg_offset'],
                         12*8192 + 0x35B)
        summary = runs(fixture.trace, fixture.meta, min_run=1)
        self.assertFalse(summary['read_values_proven'])

    def test_stage49_joint_trace_rejects_fake_read_byte(self):
        fixture = self.prepare(JointTraceValidationTests)
        result = validate49(fixture.trace, fixture.meta)
        self.assertFalse(result['read_values_proven'])
        fixture.rows[4][4] = 'AB'
        fixture.write_rows()
        with self.assertRaisesRegex(ValueError, 'READ value provenance'):
            validate49(fixture.trace, fixture.meta)

    def test_stage53_address_candidate_remains_noncausal(self):
        fixture = self.prepare(JointContextTests)
        result = validate53(fixture.trace, fixture.meta)
        self.assertFalse(result['read_values_proven'])
        self.assertEqual(fixture.rows[3][4], 'unknown')
        candidates = compare(fixture.trace, fixture.meta,
                             exec_seq=1, opcode_hex='AD5C83')
        self.assertEqual(candidates['candidate_reads'], [])
        self.assertFalse(candidates['causality_proven'])
        self.assertFalse(candidates['read_values_proven'])

    def test_stage41_legacy_callback_bytes_not_accepted(self):
        fixture = self.prepare(PointerValidationTests)
        fixture.rows[0][4] = '11'
        fixture.write_rows()
        with self.assertRaisesRegex(ValueError, 'provenance'):
            validate41(fixture.log, fixture.meta)

    def test_stage45_legacy_capture_metadata_rejected(self):
        fixture = self.prepare(VerifiedCaptureTests)
        fixture.meta.write_text(fixture.meta.read_text().replace(
            'read_value_provenance=address_only_fceux_zero_sentinel\n', ''),
            encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'provenance'):
            audit_verified(fixture.trace, fixture.meta)

    def test_stage53_legacy_read_value_and_metadata_rejected(self):
        fixture = self.prepare(JointContextTests)
        fixture.rows[3][4] = 'AB'
        fixture.write_rows()
        with self.assertRaisesRegex(ValueError, 'READ value provenance'):
            validate53(fixture.trace, fixture.meta)
        fixture.rows[3][4] = 'unknown'
        fixture.write_rows()
        fixture.meta.write_text(fixture.meta.read_text().replace(
            'read_value_provenance=address_only_fceux_zero_sentinel\n', ''),
            encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'provenance'):
            validate53(fixture.trace, fixture.meta)


if __name__ == '__main__':
    unittest.main()
