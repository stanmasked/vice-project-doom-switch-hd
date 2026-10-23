"""ROM-free synthetic regression tests for the Stage338 NTSC Loopy raster model."""
import csv
import hashlib
import importlib.util
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

def module(file, name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    obj=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name]=obj
    spec.loader.exec_module(obj)
    return obj

model=module('ppu_dot_scroll_model.py','stage338_loopy')
audit=module('audit_private_ppu_dot_readiness.py','stage338_gate')

class LoopyPPUTests(unittest.TestCase):
    def test_reject_bad_seed(self):
        for kw in ({'w':2},{'x':8},{'v':0x8000},{'mask':256},{'t':-1},{'v':True}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                model.PPUScroll(**kw)

    def test_2005_first_second_and_2002_reset(self):
        p=model.PPUScroll()
        p.write2005(0xab)
        self.assertEqual((p.t&0x1f,p.x,p.w),(0x15,3,1))
        p.write2005(0xdd)
        self.assertEqual((p.t>>12,(p.t>>5)&0x1f,p.w),(5,0x1b,0))
        p.write2005(0x77)
        p.read2002()
        p.write2005(0x13)
        self.assertEqual((p.x,p.w,p.t&0x1f),(3,1,2))

    def test_2006_pair_sets_v_and_clears_bit_14(self):
        p=model.PPUScroll(t=0x7fff,v=0x7001)
        p.write2006(0xff)
        self.assertEqual(p.t,0x3fff)
        self.assertEqual(p.v,0x7001)
        p.write2006(0x22)
        self.assertEqual((p.v,p.t,p.w),(0x3f22,0x3f22,0))

    def test_2005_2006_share_toggle(self):
        p=model.PPUScroll()
        p.write2005(0x12)
        p.write2006(0x34)
        self.assertEqual((p.v,p.w),(0x0034,0))
        p.write2006(0x2e)
        p.read2002()
        self.assertEqual(p.w,0)
        p.write2006(0x21)
        p.write2006(0x44)
        self.assertEqual(p.v,0x2144)

    def test_2000_nametable_select_only(self):
        p=model.PPUScroll(t=0x7fff)
        p.write2000(0x80)
        self.assertEqual(p.t,0x73ff)
        self.assertEqual((p.ctrl,p.w),(0x80,0))

    def test_coarse_x_wrap_toggles_horizontal_nametable(self):
        p=model.PPUScroll(v=0x701f)
        p.increment_x()
        self.assertEqual(p.v,0x7400)
        p.increment_x()
        self.assertEqual(p.v,0x7401)

    def test_fine_y_advance(self):
        p=model.PPUScroll(v=0x60a1)
        p.increment_y()
        self.assertEqual(p.v,0x70a1)
        p.increment_y()
        self.assertEqual(p.v,0x00c1)

    def test_coarse_y_29_wrap_toggles_vertical_nametable(self):
        p=model.PPUScroll(v=(7<<12)|(29<<5)|0x0003)
        p.increment_y()
        self.assertEqual((p.v>>12,(p.v>>5)&31,p.v&0x0800),(0,0,0x0800))

    def test_coarse_y_31_wrap_does_not_toggle_vertical_nametable(self):
        p=model.PPUScroll(v=(7<<12)|(31<<5)|0x0803)
        p.increment_y()
        self.assertEqual((p.v>>12,(p.v>>5)&31,p.v&0x0800),(0,0,0x0800))

    def test_coarse_y_30_advances_to_31(self):
        p=model.PPUScroll(v=(7<<12)|(30<<5))
        p.increment_y()
        self.assertEqual((p.v>>5)&31,31)

    def test_horizontal_reload_copies_only_coarse_x_and_name_x(self):
        p=model.PPUScroll(v=0x7fff,t=0x0002)
        p.reload_horizontal()
        self.assertEqual(p.v,0x7be2)

    def test_vertical_reload_preserves_coarse_x_and_name_x(self):
        p=model.PPUScroll(v=0x041d,t=0x7be2)
        p.reload_vertical()
        self.assertEqual(p.v,0x7ffd)

    def test_dots_increment_and_reload_only_in_rendering(self):
        p=model.PPUScroll(v=0x0005,t=0x000c)
        self.assertEqual(p.dot(0,8),())
        p.write2001(0x08)
        self.assertEqual(p.dot(0,8),('increment_x',))
        self.assertEqual(p.v,0x0006)
        self.assertEqual(p.dot(0,257),('reload_horizontal',))
        self.assertEqual(p.v & 0x041f,0x000c)
        self.assertEqual(p.dot(0,328),('increment_x',))
        self.assertEqual(p.dot(0,336),('increment_x',))
        self.assertEqual(p.dot(0,337),())

    def test_y_increment_dot_256(self):
        p=model.PPUScroll(v=0x0100,mask=0x10)
        self.assertEqual(p.dot(0,256),('increment_x','increment_y'))
        self.assertEqual((p.v>>12)&7,1)
        self.assertEqual(p.dot(0,257),('reload_horizontal',))

    def test_prerender_vertical_reload_dots_280_304(self):
        p=model.PPUScroll(v=0,t=0x78a1,mask=0x08)
        self.assertEqual(p.dot(-1,279),())
        self.assertEqual(p.dot(-1,280),('reload_vertical',))
        self.assertEqual(p.v & 0x7be0,p.t & 0x7be0)
        self.assertEqual(p.dot(-1,304),('reload_vertical',))
        self.assertEqual(p.dot(0,280),())
        self.assertEqual(p.dot(241,280),())
        self.assertEqual(p.dot(260,256),())

    def test_critical_frame_no_rendering(self):
        p=model.PPUScroll(v=0x3f20,t=0x5000,mask=0)
        state=p.snap()
        for line in (-1,0,239,240,260):
            for d in (8,256,257,280,304,328,336):
                self.assertEqual(p.dot(line,d),())
        self.assertEqual(p.snap(),state)

    def test_invalid_dot_and_bus(self):
        p=model.PPUScroll()
        for line,d in ((-2,0),(261,0),(0,-1),(0,341),(False,8)):
            with self.assertRaises(ValueError):p.dot(line,d)
        for v in (-1,256,True,'16'):
            with self.assertRaises(ValueError):p.write2005(v)

    def test_model_is_only_source_free_not_original_game_evidence(self):
        p=model.PPUScroll(mask=0x08)
        p.dot(0,8)
        self.assertTrue(p.v>=0)
        # A model transition is never an observed emulator PPU-v witness.
        self.assertFalse(hasattr(p,'source_verified'))

class ReadinessGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=pathlib.Path(self.tmp.name)/'cpu.tsv'

    def make(self,extra_columns=()):
        fields=['frame','sequence','cycle','event','ppu_toggle_before','ppu_toggle_after']+list(extra_columns)
        with self.path.open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=fields,delimiter='\t')
            writer.writeheader()
            for i in range(380,641):
                row=dict(frame=i,sequence=i-379,cycle=i*9,event='frame_begin',ppu_toggle_before='0',ppu_toggle_after='0')
                row.update({c:0 for c in extra_columns})
                writer.writerow(row)

    def test_cpu_trace_never_claims_dots(self):
        self.make()
        summary=audit.audit(self.path)
        self.assertEqual(summary['source_window_frames'],261)
        self.assertFalse(summary['source_has_ppu_scanline_dot'])
        self.assertFalse(summary['source_has_internal_v_witness'])
        self.assertFalse(summary['effective_raster_scroll_proven'])
        self.assertFalse(summary['stage335_cpu_bus_baseline_matches'])

    def test_source_sha_fail_closed(self):
        self.make()
        with self.assertRaisesRegex(ValueError,'SHA-256'):
            audit.audit(self.path,expected_sha256='0'*64)
        expected=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertEqual(audit.audit(self.path,expected_sha256=expected)['source_window_frames'],261)

    def test_baseline_mismatch_fail_closed(self):
        self.make()
        with self.assertRaisesRegex(ValueError,'baseline'):
            audit.audit(self.path,require_baseline=True)

    def test_dot_claim_not_accepted_in_cpu_trace_schema(self):
        self.make(['scanline','ppu_dot','actual_v'])
        with self.assertRaisesRegex(ValueError,'separate authenticated'):
            audit.audit(self.path)

    def test_truncated_or_corrupt_trace_rejected(self):
        self.make()
        with self.path.open('a',encoding='utf-8') as f:f.write('380\t999\n')
        with self.assertRaisesRegex(ValueError,'truncated'):
            audit.audit(self.path)

    def test_missing_frame_rejected(self):
        self.make()
        text=self.path.read_text()
        text='\n'.join(r for r in text.splitlines() if not r.startswith('421\t'))+'\n'
        self.path.write_text(text)
        with self.assertRaisesRegex(ValueError,'coverage'):
            audit.audit(self.path)

if __name__=='__main__':unittest.main()
