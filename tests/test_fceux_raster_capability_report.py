"""Stage95 ROM-free raster function-presence audit and fail-closed invariants."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_fceux_raster_capabilities import analyze, parse_probe, ProbeError, SYMBOLS, NEGATIVE

def report(**overrides):
    fields = {'format': 'vpd_fceux_raster_capability_probe_v1',
              'probe_scope': 'lua_symbol_presence_only'}
    fields.update({field: 'absent' for field in SYMBOLS})
    fields.update({field: 'no' for field in NEGATIVE})
    fields.update(overrides)
    return ''.join(f'{k}={v}\n' for k, v in fields.items())


class RasterPreflightTests(unittest.TestCase):
    def test_no_undocumented_candidates_stays_unproven(self):
        out = analyze(report())
        self.assertTrue(out['input_probe_validated'])
        self.assertFalse(out['physical_ppu_timing_proven'])
        self.assertFalse(out['candidate_scanline_function_detected'])
        self.assertFalse(out['cpu_write_to_raster_visibility_proven'])

    def test_candidate_presence_is_not_raster_proof(self):
        out = analyze(report(emu_scanline_candidate='present',
                             ppu_dot_candidate='present',
                             framecount_symbol='present',
                             registerafter_symbol='present',
                             cpu_cycle_symbol='present'))
        self.assertTrue(out['candidate_scanline_function_detected'])
        self.assertTrue(out['candidate_dot_function_detected'])
        self.assertFalse(out['raster_capability_tested_on_real_fceux'])
        self.assertFalse(out['ppu_scanline_or_dot_values_observed'])
        self.assertFalse(out['physical_ppu_timing_proven'])
        self.assertIn('independently_validate', out['next_probing_path'])

    def test_partial_candidate_pair_cannot_claim_viability(self):
        out = analyze(report(emu_scanline_candidate='present'))
        self.assertFalse(out['candidate_dot_function_detected'])
        self.assertIn('instrument_native', out['next_probing_path'])

    def test_missing_final_newline_rejected(self):
        with self.assertRaises(ProbeError):
            parse_probe(report()[:-1])

    def test_missing_required_field_rejected(self):
        with self.assertRaises(ProbeError):
            parse_probe(report().replace('ppu_dot_candidate=absent\n', ''))

    def test_duplicate_or_extra_report_field_rejected(self):
        with self.assertRaises(ProbeError):
            parse_probe(report() + 'framecount_symbol=present\n')
        with self.assertRaises(ProbeError):
            parse_probe(report() + 'rom_data=private\n')

    def test_invalid_symbol_value_rejected(self):
        with self.assertRaises(ProbeError):
            parse_probe(report(ppu_scanline_candidate='verified'))

    def test_raster_claim_is_always_rejected(self):
        for field in NEGATIVE:
            with self.subTest(field=field), self.assertRaises(ProbeError):
                parse_probe(report(**{field: 'yes'}))

    def test_probe_version_and_scope_cannot_be_upgraded(self):
        with self.assertRaises(ProbeError):
            parse_probe(report(format='v2'))
        with self.assertRaises(ProbeError):
            parse_probe(report(probe_scope='raster_measurement'))

    def test_full_positive_symbol_matrix_is_still_untrusted(self):
        out = analyze(report(**{key: 'present' for key in SYMBOLS}))
        self.assertFalse(out['vblank_edge_observed'])
        self.assertFalse(out['first_level_geometry_proven'])
        self.assertFalse(out['rom_or_graphics_bytes_in_report'])


if __name__ == '__main__':
    unittest.main()
