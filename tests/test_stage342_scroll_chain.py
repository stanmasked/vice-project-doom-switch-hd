"""Stage342 fabricated-only tests; never ship ROM, FM2 or original trace values."""
from __future__ import annotations
import csv
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stage342_probe',ROOT/'tools'/'audit_private_stage342_scroll_chain.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class Stage342Synthetic(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.cpu=self.root/'synthetic_cpu.tsv'
        self.native=self.root/'synthetic_classic.tsv'
        self.generate()

    def generate(self,*,bad_clock=False,bad_ram=False,bad_temp=False,intervene=False,
                 missing_line=False,duplicate_core=False,bad_addr=False,bad_dot=False):
        cr=[];nr=[]
        for f in range(380,383):
            base=(f-380+1)*1000
            def cpu(cycle,event,**extra):
                d={k:'' for k in mod.CPU_HEADER};d.update(frame=str(f),sequence=str(len(cr)+1),cycle=str(base+cycle),event=event)
                d.update(extra);cr.append(d)
            def native(tick,event,**extra):
                d={k:'' for k in mod.NATIVE_HEADER};d.update(core_frame_ordinal=str(f),cpu_timestamp=str(tick),event=event,
                  legacy_scanline='0',renderer_pixel_not_dot='0' if bad_dot else '-1',refresh_addr='2004',temp_addr='0000',
                  write_toggle='0',fine_x='0',ppu_mask='24')
                d.update(extra);nr.append(d)
            cpu(0,'frame_begin');native(0,'core_frame_start')
            if duplicate_core and f==380:native(1,'core_frame_start')
            cpu(10,'W2006',value='20',ppu_toggle_before='0')
            cpu(22,'W2006',value='04',ppu_toggle_before='1')
            native(23 if bad_clock and f==380 else 22,'cpu_second_2006',refresh_addr='2005' if bad_addr and f==380 else '2004')
            if f!=382:
                ybyte='15' if f==380 else '09'
                cpu(30,'ppu_bus_write',value='00',ppu_toggle_before='0')
                cpu(35,'ppu_bus_write',value=ybyte,ram0d_live='FF' if bad_ram and f==380 else ybyte,ppu_toggle_before='1')
                if intervene and f==380:cpu(40,'W2006',value='20',ppu_toggle_before='0')
                val=int(ybyte,16);t=((val&0xf8)<<2)|((val&7)<<12)
                native(70,'legacy_line_start',temp_addr=f'{(t^(1<<12) if bad_temp and f==380 else t):04x}')
                native(80,'legacy_vertical_increment');native(90,'legacy_horizontal_reload')
            else:
                native(70,'legacy_line_start')
            cpu(100,'frame_end')
        if missing_line:nr=[r for r in nr if not (r['core_frame_ordinal']=='381' and r['event']=='legacy_line_start')]
        for path,fields,rows in [(self.cpu,mod.CPU_HEADER,cr),(self.native,mod.NATIVE_HEADER,nr)]:
            with path.open('w',newline='') as f:
                w=csv.DictWriter(f,delimiter='\t',fieldnames=fields);w.writeheader();w.writerows(rows)

    def runaudit(self,**kwargs):
        digest=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
        return mod.audit(self.cpu,self.native,cpu_sha=digest(self.cpu),native_sha=digest(self.native),first=380,last=382,
                         require_sealed=False,**kwargs)

    def test_source_free_good_but_raster_unproven(self):
        r=self.runaudit()
        self.assertEqual(r['same_session_cpu_ppu_event_clock_matches'],3)
        self.assertEqual(r['first_second_phase_scroll_matches_live_ram0d'],2)
        self.assertEqual(r['first_scroll_to_classic_line0_temp_vertical_bit_matches'],2)
        self.assertFalse(r['per_pixel_road_scroll_proven'])
        self.assertFalse(r['exact_ppu_hardware_dot_observed'])
    def test_reject_cpu_native_clock_mismatch(self):
        self.generate(bad_clock=True)
        with self.assertRaisesRegex(ValueError,'timestamp mismatch'):self.runaudit()
    def test_reject_real_ppu_address_difference(self):
        self.generate(bad_addr=True)
        with self.assertRaisesRegex(ValueError,'full address'):self.runaudit()
    def test_reject_ram0d_mismatch(self):
        self.generate(bad_ram=True)
        with self.assertRaisesRegex(ValueError,'RAM'):self.runaudit()
    def test_reject_temp_y_mismatch(self):
        self.generate(bad_temp=True)
        with self.assertRaisesRegex(ValueError,'vertical bits'):self.runaudit()
    def test_reject_intervening_ppu_write(self):
        self.generate(intervene=True)
        with self.assertRaisesRegex(ValueError,'nested|intervening|unpaired'):self.runaudit()
    def test_reject_missing_renderer_line0(self):
        self.generate(missing_line=True)
        with self.assertRaisesRegex(ValueError,'line zero'):self.runaudit()
    def test_reject_duplicate_core_frame_marker(self):
        self.generate(duplicate_core=True)
        with self.assertRaisesRegex(ValueError,'anchor'):self.runaudit()
    def test_reject_fake_dot_claim(self):
        self.generate(bad_dot=True)
        with self.assertRaisesRegex(ValueError,'falsely labeled PPU dot'):self.runaudit()
    def test_reject_wrong_authenticated_digest(self):
        with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):
            mod.audit(self.cpu,self.native,cpu_sha='0'*64,native_sha=hashlib.sha256(self.native.read_bytes()).hexdigest(),first=380,last=382,require_sealed=False)
    def test_original_baseline_required_by_default(self):
        with self.assertRaisesRegex(ValueError,'capture interval'):
            mod.audit(self.cpu,self.native,cpu_sha=hashlib.sha256(self.cpu.read_bytes()).hexdigest(),native_sha=hashlib.sha256(self.native.read_bytes()).hexdigest(),first=380,last=382)

if __name__=='__main__': unittest.main()
