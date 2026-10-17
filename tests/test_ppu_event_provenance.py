"""Stage90 synthetic MMC3/PPU write attribution; no ROM or raster claims."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from audit_ppu_event_provenance import COUNTERS, RegisterObservation


def replay(*events):
    state=RegisterObservation()
    counter={key:0 for key in COUNTERS}
    for frame,address,value in events:
        state.observe(frame,address,value,counter)
    return state,counter


class RegisterProvenanceTests(unittest.TestCase):
    def test_mmc3_mirrored_selector_and_chr_bank_write(self):
        state,c=replay((1,0x8002,0x80),(1,0x9FFF,0x5A))
        self.assertEqual(c['mmc3_select_writes'],1)
        self.assertEqual(c['mmc3_data_writes'],1)
        self.assertEqual(c['chr_register_writes'],1)
        self.assertEqual(state.checkpoint()['distinct_chr_registers_observed_since_start'],1)
        self.assertFalse(state.checkpoint()['all_six_chr_registers_observed_since_start'])

    def test_data_before_selector_does_not_infer_chr_identity(self):
        state,c=replay((1,0x8001,12))
        self.assertEqual(c['mmc3_data_writes_without_known_selector'],1)
        self.assertEqual(c['chr_register_writes'],0)
        self.assertFalse(state.checkpoint()['chr_selector_observed'])

    def test_prg_register_data_not_treated_as_chr_change(self):
        _,c=replay((1,0x8000,7),(1,0x8001,9))
        self.assertEqual(c['prg_register_data_writes'],1)
        self.assertEqual(c['chr_register_writes'],0)

    def test_chr_inversion_change_only_after_previous_observation(self):
        _,c=replay((1,0x8000,0x80),(1,0x8000,0x00),
                   (2,0x8002,0x00),(2,0x8000,0x80))
        self.assertEqual(c['chr_inversion_changes_observed'],2)

    def test_ppustatus_latch_reset_and_mirrored_scroll_pair(self):
        state,c=replay((1,0x3FFA,0),(1,0x200D,7),(1,0x3FFD,14))
        self.assertEqual(c['ppustatus_read_markers'],1)
        self.assertEqual(c['ppuscroll_writes'],2)
        self.assertEqual(c['complete_observed_ppuscroll_pairs'],1)
        self.assertFalse(state.checkpoint()['pending_first_ppuscroll_write'])
        self.assertTrue(state.checkpoint()['ppuscroll_write_toggle_synchronized'])

    def test_scroll_before_latch_sync_remains_unresolved(self):
        state,c=replay((1,0x2005,11),(1,0x2005,23))
        self.assertEqual(c['ppuscroll_writes_before_latch_sync'],2)
        self.assertEqual(c['complete_observed_ppuscroll_pairs'],0)
        self.assertFalse(state.checkpoint()['ppuscroll_write_toggle_synchronized'])

    def test_ppuaddr_interrupts_first_scroll_write(self):
        state,c=replay((1,0x2002,0),(1,0x2005,23),
                       (1,0x2006,0x20),(1,0x2005,45),
                       (1,0x2005,50))
        self.assertEqual(c['interrupted_scroll_first_writes'],1)
        self.assertEqual(c['ppuaddr_writes'],1)
        self.assertEqual(c['complete_observed_ppuscroll_pairs'],1)
        self.assertFalse(state.checkpoint()['pending_first_ppuscroll_write'])

    def test_status_read_interrupts_first_scroll_write(self):
        state,c=replay((1,0x2002,0),(1,0x2005,23),
                       (1,0x2002,0),(1,0x2005,35),
                       (1,0x2005,42))
        self.assertEqual(c['interrupted_scroll_first_writes'],1)
        self.assertEqual(c['complete_observed_ppuscroll_pairs'],1)

    def test_ppuctrl_bg_bit_toggle_requires_known_prior_value(self):
        _,c=replay((1,0x2000,0x10),(2,0x3FF8,0x00),
                   (3,0x2000,0x00),(3,0x2000,0x10))
        self.assertEqual(c['ppuctrl_writes'],4)
        self.assertEqual(c['ppuctrl_bg_pattern_bit_changes'],2)

    def test_all_six_chr_regs_require_six_distinct_observed_writes(self):
        events=[]
        for i in range(6):
            events.extend(((1,0x8000,i),(1,0x8001,i)))
        state,c=replay(*events)
        self.assertEqual(c['chr_register_writes'],6)
        self.assertTrue(state.checkpoint()['all_six_chr_registers_observed_since_start'])
        self.assertFalse(state.checkpoint()['ppu_raster_bank_mapping_proven'])

    def test_no_register_events_do_not_invent_scroll_or_banks(self):
        state,c=replay()
        self.assertEqual(sum(c.values()),0)
        self.assertFalse(state.checkpoint()['chr_inversion_observed'])
        self.assertFalse(state.checkpoint()['ppuctrl_observed_since_start'])
        self.assertFalse(state.checkpoint()['rendered_scroll_value_proven'])


if __name__=='__main__':
    unittest.main()
