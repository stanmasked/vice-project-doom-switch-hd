"""ROM-free Stage340 legacy FCEUX patch, compile and witness-schema tests."""
import csv
import hashlib
import importlib.util
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

patcher=load('generate_stage340_legacy_ppu_patch.py','stage340patcher')
auditor=load('audit_private_stage340_legacy_trace.py','stage340auditor')

class Stage340Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.dir=pathlib.Path(self.temp.name)

    def pristine(self):
        # Synthetic layout, never sourced from the owner's ROM or a real emu trace.
        content='\n'.join([
            '#include <cstdio>','#include <cstdlib>','uint32 TempAddr = 0, RefreshAddr = 0;',
            'uint8 vtoggle = 0;','uint8 XOffset = 0;', 'int scanline;','int g_rasterpos;',
            'uint8 PPU[4];',
            'static DECLFW(B2006) {','if (vtoggle) {','RefreshAddr = TempAddr;','\t\tDummyRead = 1;',
            '}','}','static DECLFW(B2007) {','}',
            'static INLINE void Fixit2(void) {','RefreshAddr = rad;','}',
            'static void Fixit1(void) {','RefreshAddr = rad;','}',
            'void MMC5_hb(int);','static void DoLine(void) {',
            '\tX6502_Run(256);','\tEndRL();','\tscanline++;','\tif (scanline < 240)',
            '}','#define V_FLIP 0x80','int FCEUPPU_Loop(int skip) {','}',
            '//padding'+'z'*1800
        ])
        b=content.encode();return b,patcher.git_blob(b)

    def test_pinned_synthetic_patch_with_all_classic_hooks(self):
        b,blob=self.pristine();r=patcher.patch(b,expected_blob=blob)
        text=r.decode()
        for event in ('legacy_horizontal_reload','legacy_vertical_increment',
                      'cpu_second_2006','legacy_line_start','legacy_line_end','core_frame_start'):
            self.assertIn('"'+event+'"',text)
        self.assertIn('#ifdef VPD_STAGE340_DIAGNOSTICS',text)
        self.assertIn('newppu) return',text)
        self.assertIn('DIAGNOSTIC',text)
        self.assertEqual(text.count('VPD_STAGE340_LEGACY_PPU_DIAGNOSTICS'),2)
        self.assertNotIn('PRIVATE_FM2_SHA256',text)

    def test_idempotence_refused(self):
        b,blob=self.pristine();p=patcher.patch(b,expected_blob=blob)
        with self.assertRaisesRegex(ValueError,'pristine'):
            patcher.patch(p,expected_blob=blob)

    def test_wrong_git_blob_refused(self):
        b,_=self.pristine()
        with self.assertRaisesRegex(ValueError,'pristine'):
            patcher.patch(b)

    def test_missing_or_ambiguous_anchor(self):
        b,_=self.pristine()
        s=b.decode().replace('static void Fixit1(void) {','not_fixit1')
        with self.assertRaisesRegex(ValueError,'layout'):
            patcher.patch(s.encode(),expected_blob=patcher.git_blob(s.encode()))
        s=b.decode().replace('uint8 PPU[4];','uint8 PPU[4];\nuint8 PPU[4];')
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            patcher.patch(s.encode(),expected_blob=patcher.git_blob(s.encode()))

    def test_preserve_crlf(self):
        b,_=self.pristine()
        crlf=b.replace(b'\n',b'\r\n')
        p=patcher.patch(crlf,expected_blob=patcher.git_blob(crlf))
        self.assertEqual(p.count(b'\n'),p.count(b'\r\n'))

    def test_compile_diagnostic_helper_on_and_off(self):
        cxx=shutil.which('g++')
        if cxx is None:self.skipTest('compiler not installed')
        # Extract *exact* helper emitted by patcher; isolate the C++ runtime ABI.
        b,blob=self.pristine()
        s=patcher.patch(b,expected_blob=blob).decode()
        fragment=s[s.index('// BEGIN VPD_STAGE340_LEGACY_PPU_DIAGNOSTICS'):s.index('// END VPD_STAGE340_LEGACY_PPU_DIAGNOSTICS')+len('// END VPD_STAGE340_LEGACY_PPU_DIAGNOSTICS')]
        wrapper='''#include <cstdio>\n#include <cstdlib>\n#include <cstdint>\ntypedef unsigned char uint8;\ntypedef uint32_t uint32;\nint newppu=0;\nuint32 timestamp=0,TempAddr=0,RefreshAddr=0;\nuint8 vtoggle=0,XOffset=0,PPU[4]={0};\nint scanline=0;\n'''+fragment+'''\nint main(){vpd340_frame_enter(); vpd340_emit("legacy_line_end",-1); return 0;}\n'''
        path=self.dir/'synthetic-runtime.cpp';path.write_text(wrapper)
        for flag in ([],['-DVPD_STAGE340_DIAGNOSTICS']):
            cmd=[cxx,'-std=c++11','-Wall','-Wextra','-Werror','-Wno-unused-function',*flag,'-fsyntax-only',str(path)]
            cp=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr)

    def rows(self,first=380,last=381):
        rows=[]
        for f in range(first,last+1):
            for i,e in enumerate(('core_frame_start','legacy_line_start',
                      'legacy_vertical_increment','legacy_line_256_cpu_slice',
                      'legacy_horizontal_reload','legacy_line_end')):
                rows.append(dict(core_frame_ordinal=str(f),cpu_timestamp=str(i*5),event=e,
                                 legacy_scanline='0',renderer_pixel_not_dot='-1',
                                 refresh_addr='2000',temp_addr='2800',write_toggle='0',fine_x='1',ppu_mask='24'))
        return rows

    def emit(self,rows):
        p=self.dir/'trace.tsv'
        with p.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=auditor.FIELDS,delimiter='\t');w.writeheader();w.writerows(rows)
        return p

    def test_synthetic_trace_valid_but_dot_unproven(self):
        p=self.emit(self.rows())
        r=auditor.audit(p,first=380,last=381,expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertEqual(r['core_frames_observed'],2)
        self.assertFalse(r['exact_hardware_ppu_dot_observed'])
        self.assertFalse(r['movie_frame_alignment_verified'])
        self.assertFalse(r['raster_effective_scroll_proven'])
        self.assertFalse(r['private_values_disclosed'])

    def test_source_sha_mismatch_rejected(self):
        p=self.emit(self.rows())
        with self.assertRaisesRegex(ValueError,'checksum'):
            auditor.audit(p,first=380,last=381,expected_sha256='0'*64)

    def test_truncated_trace_rejected(self):
        p=self.emit(self.rows())
        with p.open('a') as f:f.write('VPD_STAGE340_TRUNCATED\n')
        with self.assertRaisesRegex(ValueError,'truncated'):
            auditor.audit(p,first=380,last=381)

    def test_missing_frame_marker_rejected(self):
        p=self.emit([x for x in self.rows() if not (x['core_frame_ordinal']=='381' and x['event']=='core_frame_start')])
        with self.assertRaisesRegex(ValueError,'incomplete'):
            auditor.audit(p,first=380,last=381)

    def test_unexpected_dot_claim_rejected(self):
        rows=self.rows();rows[2]['event']='ppu_dot_witness'
        p=self.emit(rows)
        with self.assertRaisesRegex(ValueError,'unknown'):
            auditor.audit(p,first=380,last=381)

    def test_non_monotone_event_rejected(self):
        rows=self.rows();rows[3]['cpu_timestamp']='0'
        p=self.emit(rows)
        with self.assertRaisesRegex(ValueError,'nonmonotonic'):
            auditor.audit(p,first=380,last=381)

    def test_illegal_ppu_value_rejected(self):
        rows=self.rows();rows[2]['fine_x']='9'
        p=self.emit(rows)
        with self.assertRaisesRegex(ValueError,'invalid legacy'):
            auditor.audit(p,first=380,last=381)

    def test_duplicate_core_frame_rejected(self):
        rows=self.rows();rows.append(rows[-6].copy());rows.sort(key=lambda r:(int(r['core_frame_ordinal']),int(r['cpu_timestamp'])))
        p=self.emit(rows)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            auditor.audit(p,first=380,last=381)

if __name__=='__main__':unittest.main()
