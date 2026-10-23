"""ROM-free negative/regression checks for Stage341 frame-and-address alignment."""
from __future__ import annotations
import csv
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

TOOLS=Path(__file__).resolve().parents[1]/'tools'
spec=importlib.util.spec_from_file_location('stage341_alignment',TOOLS/'audit_private_stage341_alignment.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AlignmentSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.cpu=self.root/'cpu.tsv';self.native=self.root/'native.tsv';self.complete=self.root/'COMPLETE.txt'
        self.synthetic()

    def synthetic(self,corrupt=False):
        with self.cpu.open('w',newline='') as o:
            fields=['frame','event','value','ppu_toggle_before'];w=csv.DictWriter(o,fieldnames=fields,delimiter='\t');w.writeheader()
            for f in range(380,383):
                for value,toggle in ((f-380+1,0),(f-380+11,1)):
                    w.writerow(dict(frame=f,event='W2006',value=f'{value:02X}',ppu_toggle_before=toggle))
        with self.native.open('w',newline='') as o:
            w=csv.DictWriter(o,fieldnames=module.NATIVE_HEADER,delimiter='\t');w.writeheader()
            for f in range(380,383):
                for t,e in ((0,'core_frame_start'),(1,'cpu_second_2006')):
                    addr=(((f-380+1)&0x3f)<<8)|(f-380+11)
                    if corrupt and f==381:addr^=1
                    w.writerow({'core_frame_ordinal':f,'cpu_timestamp':t,'event':e,'legacy_scanline':1,
                       'renderer_pixel_not_dot':-1,'refresh_addr':f'{addr:04X}','temp_addr':'0000',
                       'write_toggle':0,'fine_x':0,'ppu_mask':24})
        self.complete.write_text('frames=3\nfirst_frame=380\nlast_frame=382\nrom_identity_verified=yes\nfm2_readonly=yes\n')

    def audit(self):
        return module.analyze(self.cpu,self.native,self.complete,
            cpu_sha=module.sha256(self.cpu),native_sha=module.sha256(self.native),
            first=380,last=382,require_stage335=False)

    def test_same_session_full_address_alignment(self):
        data=self.audit()
        self.assertEqual(data['full_ppu_address_matches'],3)
        self.assertTrue(data['same_session_movie_core_frame_alignment_verified'])
        self.assertFalse(data['independent_ppu_dot_phase_observed'])

    def test_reject_address_mismatch(self):
        self.synthetic(corrupt=True)
        with self.assertRaisesRegex(ValueError,'full PPU address mismatch'):
            self.audit()

    def test_reject_forged_source_sha(self):
        with self.assertRaisesRegex(ValueError,'authenticated'):
            module.analyze(self.cpu,self.native,self.complete,
              cpu_sha='0'*64,native_sha=module.sha256(self.native),
              first=380,last=382,require_stage335=False)

    def test_reject_missing_readonly_marker(self):
        self.complete.write_text('frames=3\nfirst_frame=380\nlast_frame=382\nrom_identity_verified=yes\n')
        with self.assertRaisesRegex(ValueError,'completion marker'):
            self.audit()

    def test_reject_missing_native_frame(self):
        content=self.native.read_text().splitlines()
        self.native.write_text('\n'.join([s for s in content if not s.startswith('382\t')])+'\n')
        with self.assertRaisesRegex(ValueError,'native and CPU second-write totals differ|frame marker'):
            self.audit()

if __name__=='__main__':unittest.main()
