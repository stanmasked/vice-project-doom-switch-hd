"""Fabricated-only Stage345 comparisons; no copyrighted game pixels or CPU/PPU logs."""
from __future__ import annotations
import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_private_stage345_scroll_motion as stage


def fake_samples(start_y:int=100)->tuple[list[dict],list[int]]:
    ys=[start_y]*12+[(start_y-i)%256 for i in range(1,14)]
    samples=[{'frame':420+i,'first_y':y,'last_y':212,'ram_writes':int(i>=11)}
             for i,y in enumerate(ys)]
    return samples,[0]*11+[1]*13


def fake_scroll(first_y:int=71):
    t=((first_y&0xf8)<<2)|((first_y&7)<<12)
    cpu=[{'event':'frame_begin','cycle':'100'},
         {'event':'ppu_bus_write','ppu_toggle_before':'1',
          'value':f'{first_y:02x}','ram0d_live':f'{first_y:02x}','cycle':'110'},
         {'event':'frame_end','cycle':'150'}]
    native=[{'event':'core_frame_start','cpu_timestamp':'0'},
            {'event':'legacy_line_start','legacy_scanline':'0',
             'temp_addr':f'{t:04x}','cpu_timestamp':'30'}]
    return cpu,native


class SourceFreeStage345(unittest.TestCase):
    def test_full_bounded_correlation(self):
        frames,shifts=fake_samples()
        out=stage.correlate(frames,shifts)
        self.assertEqual(out['display_vs_first_2005_comparisons_matching'],24)
        self.assertEqual(out['display_plus_one_and_first_2005_y_minus_one_pairs'],13)
        self.assertFalse(out['general_camera_speed_proven'])

    def test_stationary_mismatch_rejected(self):
        samples,shifts=fake_samples();samples[2]['first_y']-=1
        with self.assertRaisesRegex(ValueError,'mismatch'):
            stage.correlate(samples,shifts)

    def test_opposite_scroll_rejected(self):
        samples,shifts=fake_samples();samples[12]['first_y']+=2
        with self.assertRaisesRegex(ValueError,'mismatch'):
            stage.correlate(samples,shifts)

    def test_later_scroll_phase_changes_rejected(self):
        samples,shifts=fake_samples();samples[10]['last_y']-=1
        with self.assertRaisesRegex(ValueError,'later'):
            stage.correlate(samples,shifts)

    def test_frame_order_rejected(self):
        samples,shifts=fake_samples();samples[10]['frame']=499
        with self.assertRaisesRegex(ValueError,'frame order'):
            stage.correlate(samples,shifts)

    def test_missing_adjacent_pair_rejected(self):
        samples,shifts=fake_samples()
        with self.assertRaisesRegex(ValueError,'evidence length'):
            stage.correlate(samples,shifts[:-1])

    def test_out_of_scope_shift_rejected(self):
        samples,shifts=fake_samples();shifts[16]=2
        with self.assertRaisesRegex(ValueError,'bounded'):
            stage.correlate(samples,shifts)

    def test_scroll_wrap_is_signed_not_camera_speed(self):
        samples,shifts=fake_samples(start_y=5)
        self.assertEqual(stage.signed_delta(0,255),-1)
        self.assertEqual(stage.signed_delta(255,0),1)
        self.assertEqual(stage.correlate(samples,shifts)['adjacent_pairs'],24)

    def test_scroll_byte_out_of_range_rejected(self):
        with self.assertRaisesRegex(ValueError,'invalid'):
            stage.signed_delta(300,0)

    def test_first_scroll_and_native_t_agree(self):
        cpu,native=fake_scroll()
        out=stage.frame_scroll(cpu,native)
        self.assertEqual(out['first_y'],71)
        self.assertEqual(out['ram_writes'],0)

    def test_live_ram0d_disagreement_rejected(self):
        cpu,native=fake_scroll();cpu[1]['ram0d_live']='48'
        with self.assertRaisesRegex(ValueError,'RAM'):
            stage.frame_scroll(cpu,native)

    def test_native_t_disagreement_rejected(self):
        cpu,native=fake_scroll();native[1]['temp_addr']='0000'
        with self.assertRaisesRegex(ValueError,'temporary Y'):
            stage.frame_scroll(cpu,native)

    def test_first_scroll_write_too_late_rejected(self):
        cpu,native=fake_scroll();native[1]['cpu_timestamp']='9'
        with self.assertRaisesRegex(ValueError,'not before'):
            stage.frame_scroll(cpu,native)

    def test_intervening_ppu_address_write_rejected(self):
        cpu,native=fake_scroll();cpu.insert(2,{'event':'W2006','cycle':'111'})
        with self.assertRaisesRegex(ValueError,'intervening'):
            stage.frame_scroll(cpu,native)

    def test_missing_native_line_zero_anchor_rejected(self):
        cpu,native=fake_scroll();native.pop()
        with self.assertRaisesRegex(ValueError,'anchors'):
            stage.frame_scroll(cpu,native)

    def test_corrupt_original_byte_rejected(self):
        cpu,native=fake_scroll();cpu[1]['value']='xx'
        with self.assertRaisesRegex(ValueError,'invalid'):
            stage.frame_scroll(cpu,native)

    def test_tsv_missing_frame_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'synthetic.tsv'
            with path.open('w',newline='') as f:
                w=csv.writer(f,delimiter='\t');w.writerow(stage.CPU_HEADER)
                for frame in list(range(420,440))+list(range(441,445)):
                    d={k:'' for k in stage.CPU_HEADER};d['frame']=str(frame)
                    w.writerow([d[k] for k in stage.CPU_HEADER])
            with self.assertRaisesRegex(ValueError,'incomplete'):
                stage.original_rows(path,columns=stage.CPU_HEADER,
                                    frame_column='frame',first=420,last=444)

    def test_tsv_nonmonotonic_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'synthetic.tsv'
            with path.open('w',newline='') as f:
                w=csv.writer(f,delimiter='\t');w.writerow(stage.CPU_HEADER)
                for frame in list(range(420,445))+[421]:
                    d={k:'' for k in stage.CPU_HEADER};d['frame']=str(frame)
                    w.writerow([d[k] for k in stage.CPU_HEADER])
            with self.assertRaisesRegex(ValueError,'non-monotonic'):
                stage.original_rows(path,columns=stage.CPU_HEADER,
                                    frame_column='frame',first=420,last=444)


if __name__=='__main__':unittest.main()
