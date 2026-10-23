"""Stage346 ROM-free tests: synthetic Lua, manufactured TSV and 8-bit register steps."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_private_stage346_scroll_windows as stage
import prepare_private_stage346_rgb_capture as capture


def samples(first:int,deltas:list[int],*,later:int=150)->list[dict]:
    assert len(deltas)==24
    vals=[160]
    for d in deltas: vals.append((vals[-1]+d)%256)
    return [{'frame':first+i,'first_y':v,'last_y':later,
             'ram_writes':1 if i%2 else 0} for i,v in enumerate(vals)]


def mock_lua()->bytes:
    pieces=[
        capture.FRAME_PREFIX+capture.selection(range(420,445)),
        capture.PALETTE_PREFIX+capture.selection((420,432,444)),
        capture.COUNT_OLD,
        "assert(movie.readonly())",
        "local bytes=gui.gdscreenshot(false)",
        "local a,b,c,p=emu.getscreenpixel(x,y,false)",
        "assert(rom.gethash('md5'))",
        "emu.registerafter(function()",
        "assert(vpd343_capture(frame))",
        "assert(os.rename('COMPLETE.pending','COMPLETE.txt'))",
    ]
    return ('\n'.join(pieces)+'\n'+'-- fabricated padding\n'*45).encode()


class Stage346Pure(unittest.TestCase):
    def test_target_windows_disjoint_from_old_visual_evidence(self):
        self.assertEqual(len(stage.WINDOWS),4)
        self.assertTrue(all(b-a==24 and a>444 for a,b in stage.WINDOWS))

    def test_classify_register_steps_without_physics_claim(self):
        expected={0:'unchanged',-1:'minus_one',-2:'minus_two',
                  -3:'minus_three_or_four',-4:'minus_three_or_four',
                  -5:'minus_five_or_more',-18:'minus_five_or_more',
                  1:'positive_step'}
        for value,label in expected.items():
            with self.subTest(value=value):self.assertEqual(stage.classify(value),label)

    def test_invalid_delta_rejected(self):
        with self.assertRaisesRegex(ValueError,'invalid'):
            stage.classify(500)

    def test_bounded_research_window_counts(self):
        data=samples(445,[-1]*18+[-2]*6)
        out=stage.profile(data,first=445,last=469)
        self.assertEqual(out['first_scroll_deltas_classified']['minus_one'],18)
        self.assertEqual(out['first_scroll_deltas_classified']['minus_two'],6)
        self.assertFalse(out['rgb_scroll_displacement_generalization_proven'])
        self.assertEqual(out['native_rgb_frames_in_this_window_verified'],0)

    def test_synthetic_large_step_separated(self):
        out=stage.profile(samples(470,[-2]*23+[-18]),first=470,last=494)
        self.assertEqual(out['first_scroll_deltas_classified']['minus_five_or_more'],1)

    def test_modular_wrap_classified_as_minus_one(self):
        out=stage.profile(samples(560,[-1]*24),first=560,last=584)
        self.assertEqual(out['first_scroll_deltas_classified']['minus_one'],24)

    def test_later_phase_change_rejected(self):
        s=samples(520,[-3]*24)
        s[7]['last_y']=149
        with self.assertRaisesRegex(ValueError,'later'):
            stage.profile(s,first=520,last=544)

    def test_unselected_window_rejected(self):
        with self.assertRaisesRegex(ValueError,'unsupported'):
            stage.profile(samples(420,[0]*24),first=420,last=444)

    def test_missing_or_duplicate_frame_rejected(self):
        s=samples(445,[-1]*24);s[14]['frame']=s[13]['frame']
        with self.assertRaisesRegex(ValueError,'reordered or duplicate'):
            stage.profile(s,first=445,last=469)

    def test_prepared_capture_uses_only_new_window(self):
        src=mock_lua()
        out=capture.prepare(src,source_sha256=hashlib.sha256(src).hexdigest(),
                            first=445,last=469).decode()
        self.assertIn(capture.FRAME_PREFIX+capture.selection(range(445,470)),out)
        self.assertIn(capture.PALETTE_PREFIX+capture.selection((445,457,469)),out)
        self.assertNotIn(capture.FRAME_PREFIX+capture.selection(range(420,445)),out)
        self.assertEqual(out.count(capture.COUNT_OLD),1)
        self.assertIn('movie.readonly()',out)

    def test_prepared_capture_tampered_digest_rejected(self):
        src=mock_lua()
        with self.assertRaisesRegex(ValueError,'checksum'):
            capture.prepare(src,source_sha256='0'*64,first=445,last=469)

    def test_prepared_capture_source_selector_changed_rejected(self):
        src=mock_lua().replace(b'[420]=true',b'[419]=true')
        with self.assertRaisesRegex(ValueError,'layout'):
            capture.prepare(src,source_sha256=hashlib.sha256(src).hexdigest(),
                            first=445,last=469)

    def test_prepared_capture_repeated_selector_rejected(self):
        src=mock_lua();src+=src.split(b'\n')[0]+b'\n'
        with self.assertRaisesRegex(ValueError,'layout'):
            capture.prepare(src,source_sha256=hashlib.sha256(src).hexdigest(),
                            first=445,last=469)

    def test_prepared_capture_missing_core_identity_rejected(self):
        src=mock_lua().replace(b"rom.gethash('md5')",b"rom.getid('wrong')")
        with self.assertRaisesRegex(ValueError,'contract'):
            capture.prepare(src,source_sha256=hashlib.sha256(src).hexdigest(),
                            first=445,last=469)

    def test_prepared_capture_old_window_rejected(self):
        src=mock_lua()
        with self.assertRaisesRegex(ValueError,'unsupported'):
            capture.prepare(src,source_sha256=hashlib.sha256(src).hexdigest(),
                            first=420,last=444)


class Stage346SyntheticFullSource(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.dir=Path(tmp.name)
        self.cpu=self.dir/'synthetic_cpu.tsv'
        self.native=self.dir/'synthetic_native.tsv'
        self.complete=self.dir/'synthetic_complete.txt'
        self.make()
    @staticmethod
    def h(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
    def make(self):
        self.complete.write_text('rom_identity_verified=yes\nfm2_readonly=yes\n'
             'frames=261\nfirst_frame=380\nlast_frame=640\n')
        with self.cpu.open('w',newline='') as f, self.native.open('w',newline='') as g:
            a=csv.DictWriter(f,fieldnames=stage.scroll.CPU_HEADER,delimiter='\t')
            b=csv.DictWriter(g,fieldnames=stage.scroll.NATIVE_HEADER,delimiter='\t')
            a.writeheader();b.writeheader()
            for frame in range(380,641):
                y=(200-(frame-380))%256
                t=((y&0xf8)<<2)|((y&7)<<12)
                def write_cpu(event,**kw):
                    row={k:'' for k in stage.scroll.CPU_HEADER}
                    row.update(frame=str(frame),event=event,**kw)
                    a.writerow(row)
                def write_native(event,**kw):
                    row={k:'' for k in stage.scroll.NATIVE_HEADER}
                    row.update(core_frame_ordinal=str(frame),event=event,**kw)
                    b.writerow(row)
                write_cpu('frame_begin',cycle='100')
                write_cpu('ppu_bus_write',cycle='110',ppu_toggle_before='1',
                          value=f'{y:02x}',ram0d_live=f'{y:02x}')
                write_cpu('ppu_bus_write',cycle='140',ppu_toggle_before='1',
                          value='46',ram0d_live='46')
                write_cpu('frame_end',cycle='150')
                write_native('core_frame_start',cpu_timestamp='0')
                write_native('legacy_line_start',cpu_timestamp='30',
                             legacy_scanline='0',temp_addr=f'{t:04x}')
    def report(self,**kwargs):
        args=dict(cpu_sha=self.h(self.cpu),native_sha=self.h(self.native),
                  complete_sha=self.h(self.complete))
        args.update(kwargs)
        return stage.private_audit(self.cpu,self.native,self.complete,**args)
    def test_full_owner_contract_on_fabricated_source(self):
        out=self.report()
        self.assertEqual(out['selected_original_register_frames_verified'],100)
        self.assertEqual(len(out['per_window_preflight']),4)
        self.assertFalse(out['original_new_rgb_capture_performed'])
        self.assertFalse(out['hardware_ppu_dot_observed'])
    def test_tampered_cpu_source_refused(self):
        with self.assertRaisesRegex(ValueError,'SHA-256'):
            self.report(cpu_sha='0'*64)
    def test_tampered_native_source_refused(self):
        with self.assertRaisesRegex(ValueError,'SHA-256'):
            self.report(native_sha='0'*64)
    def test_completion_marker_provenance_refused(self):
        self.complete.write_text('fm2_readonly=yes\ninvalid_original_marker=no\n')
        with self.assertRaisesRegex(ValueError,'completion marker'):
            self.report()
    def test_source_native_t_disagreement_fails(self):
        text=self.native.read_text()
        self.native.write_text(text.replace('legacy_line_start', 'legacy_line_fake'))
        with self.assertRaisesRegex(ValueError,'anchors'):
            self.report()

if __name__=='__main__':unittest.main()
