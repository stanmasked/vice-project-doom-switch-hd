"""Source-free synthetic tests for Stage 337 write-side PPU register replay."""
import csv
import importlib.util
import json
import pathlib
import tempfile
import unittest

PATH=pathlib.Path(__file__).resolve().parents[1]/'tools'/'audit_private_ppu_register_shadow.py'
spec=importlib.util.spec_from_file_location('private_ppu_shadow',PATH)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
COLUMNS=['frame','sequence','cycle','event','value','ppu_toggle_before','ppu_toggle_after','ppu_ordinal']


def emit(rows, frame, event, value, before, after, ordinal=''):
    rows.append(dict(frame=str(frame),sequence=str(len(rows)+1),cycle=str((len(rows)+1)*4),
                     event=event,value=f'{value:02X}',ppu_toggle_before=str(before),
                     ppu_toggle_after=str(after),ppu_ordinal=str(ordinal)))


def fixture(path, rows):
    with path.open('x',newline='',encoding='utf-8') as out:
        writer=csv.DictWriter(out,fieldnames=COLUMNS,delimiter='\t')
        writer.writeheader();writer.writerows(rows)


class Stage337Test(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'events.tsv'

    def make(self):
        rows=[]
        emit(rows,380,'W2000',0x88,0,0)
        emit(rows,380,'ppu_status_read',0x80,0,0)
        emit(rows,380,'W2006',0x21,0,1)
        emit(rows,380,'W2006',0x50,1,0)
        emit(rows,380,'ppu_bus_write',0x2B,0,1,1)
        emit(rows,380,'ppu_bus_write',0x43,1,0,2)
        emit(rows,380,'W2001',0x18,0,0)
        # second frame has status reset between write phases
        emit(rows,381,'ppu_bus_write',0x02,0,1,1)
        emit(rows,381,'ppu_status_read',0x00,1,0)
        emit(rows,381,'ppu_bus_write',0x10,0,1,2)
        emit(rows,381,'W2006',0x3F,1,0)
        return rows

    def test_valid_mixed_register_stream(self):
        fixture(self.path,self.make())
        r=m.shadow_audit(self.path,380,381)
        self.assertEqual(r['source_frames'],2)
        self.assertEqual(r['ppu_bus_events']['PPUADDR_2006_writes'],3)
        self.assertEqual(r['ppu_bus_events']['PPUADDR_2006_second_half_cpu_v_assignments'],2)
        self.assertEqual(r['scroll_input_phase_counts']['first_2005'],3)
        self.assertEqual(r['scroll_input_phase_counts']['second_2005'],1)
        self.assertEqual(r['toggle_mismatches'],0)
        self.assertFalse(r['effective_raster_scroll_proven'])
        self.assertFalse(r['actual_ppu_v_during_rendering_known'])
        dump=json.dumps(r)
        self.assertNotIn('2B',dump)
        self.assertNotIn('E8EC',dump)

    def test_phase_mismatch_rejected(self):
        rows=self.make();rows[3]['ppu_toggle_before']='0'
        fixture(self.path,rows)
        with self.assertRaisesRegex(ValueError,'toggle'):
            m.shadow_audit(self.path,380,381)

    def test_write_after_phase_mismatch_rejected(self):
        rows=self.make();rows[4]['ppu_toggle_after']='0'
        fixture(self.path,rows)
        with self.assertRaisesRegex(ValueError,'after-state'):
            m.shadow_audit(self.path,380,381)

    def test_unsorted_rejected(self):
        rows=self.make();rows[3]['sequence']=rows[2]['sequence']
        fixture(self.path,rows)
        with self.assertRaisesRegex(ValueError,'monotonic'):
            m.shadow_audit(self.path,380,381)

    def test_frame_gap_rejected(self):
        rows=self.make()
        for r in rows:
            if r['frame']=='381':r['frame']='382'
        fixture(self.path,rows)
        with self.assertRaisesRegex(ValueError,'missing source frames'):
            m.shadow_audit(self.path,380,382)

    def test_nonhex_byte_rejected(self):
        rows=self.make();rows[5]['value']='GG'
        fixture(self.path,rows)
        with self.assertRaisesRegex(ValueError,'invalid private PPU'):
            m.shadow_audit(self.path,380,381)

    def test_bad_ordinal_rejected(self):
        rows=self.make();rows[5]['ppu_ordinal']='9'
        fixture(self.path,rows)
        with self.assertRaisesRegex(ValueError,'ordinal discontinuity'):
            m.shadow_audit(self.path,380,381)

    def test_no_status_read_rejected(self):
        rows=[r for r in self.make() if r['event']!='ppu_status_read']
        for i,r in enumerate(rows):r['sequence']=str(i+1)
        # Remove conflicting register phases; failure is missing initial witness.
        for r in rows:
            if r['frame']=='381':r['frame']='380'
        fixture(self.path,rows[:1])
        with self.assertRaisesRegex(ValueError,'missing PPUSTATUS'):
            m.shadow_audit(self.path,380,380)

    def test_truncated_fields_rejected(self):
        fixture(self.path,self.make())
        with self.path.open('a') as out:out.write('381\t999\n')
        with self.assertRaisesRegex(ValueError,'truncated TSV'):
            m.shadow_audit(self.path,380,381)


if __name__=='__main__':unittest.main()
