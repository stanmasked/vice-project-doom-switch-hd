"""ROM-free made-up execution events, never original game captures."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_dispatch_execution import FIELDS,analyze,mapping

MD5='f'*32

def fixture(root,clock=True,drop=0):
    select=r6=r7=None
    events=[]
    frame=100
    def add(kind,addr,val=None):
        nonlocal select,r6,r7,frame
        if kind=='MMC3_SELECT':select=val
        if kind=='MMC3_DATA' and select is not None:
            if select%8==6:r6=val
            if select%8==7:r7=val
        bank,status=mapping(addr,select,r6,r7)
        n=len(events)+1
        events.append(dict(zip(FIELDS,[
            str(frame),str(n),str(n*5) if clock else 'unknown',
            kind,f'{addr:04X}',f'{val:02X}' if val is not None else 'unknown',
            'unknown' if select is None else str((select>>6)&1),
            'unknown' if r6 is None else f'{r6:02X}',
            'unknown' if r7 is None else f'{r7:02X}',
            'unknown' if bank is None else str(bank),status,
            *['07','90','91','92','AA','AB','A8','A9']])))
    add('EXEC',0x835B)
    add('EXEC',0xE479)
    add('MMC3_SELECT',0x8000,0x06)
    add('MMC3_DATA',0x8001,0x0C)
    add('EXEC',0x835B)
    add('RAM_WRITE',0xAA,0x76)
    add('RAM_WRITE',0xAB,0x83)
    add('EXEC',0xC906)
    add('EXEC',0xE4E6)
    add('EXEC',0xE4F3)
    add('MMC3_SELECT',0x8000,0x46)
    add('MMC3_DATA',0x8001,0x0E)
    frame=101
    add('EXEC',0xC906)
    add('EXEC',0x835B)
    trace=root/'stage38_dispatch_exec.tsv'
    meta=root/'stage38_dispatch_exec.meta.txt'
    with trace.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,delimiter='\t',lineterminator='\n')
        w.writeheader();w.writerows(events)
    meta.write_text('\n'.join([
      'format=vice_stage38_execution_v1',f'rom_md5={MD5}',
      'execution_hooks_registered=15','tracked_ram_write_hooks=8',
      f'events_recorded={len(events)}',f'events_dropped={drop}',
      f'trace_complete={"no" if drop else "yes"}',
      f'cycle_trace_available={"yes" if clock else "no"}',
      'initial_mmc3_mode=unknown',
      'mmc3_write_coverage=full_8000_9fff_even_odd','initial_prg_r6=unknown',
      'initial_prg_r7=unknown',
      'execution_provenance=registerexec_callbacks_not_source_disassembly'
    ])+'\n',encoding='utf8')
    return trace,meta

def edit(trace,mutate):
    with trace.open(encoding='utf8',newline='') as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    mutate(rows)
    with trace.open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,delimiter='\t',lineterminator='\n')
        w.writeheader();w.writerows(rows)

class DispatchExecutionTests(unittest.TestCase):
    def test_mapper_mode_and_valid_runtime_callbacks(self):
        with tempfile.TemporaryDirectory() as d:
            path,meta=fixture(Path(d))
            r=analyze(path,meta)
            self.assertTrue(r['complete'])
            self.assertEqual(r['events_recorded'],14)
            self.assertEqual(r['execution_counts_by_cpu_pc']['$835B'],3)
            self.assertEqual(r['candidate_physically_mapped_exec_hits']['835B:bank12'],1)
            self.assertEqual(r['candidate_physically_mapped_exec_hits']['C906:bank14'],2)
            self.assertEqual(r['banked_hits_with_unknown_mapping'],1)
            self.assertEqual(r['banked_hits_with_different_mapping'],1)
            self.assertEqual(r['candidate_setup_before_decoder_observations'],1)
            self.assertEqual(r['pointer_ram_write_events'],2)

    def test_mirrored_bank_registers_replay(self):
        with tempfile.TemporaryDirectory() as d:
            path,meta=fixture(Path(d))
            edit(path,lambda rows:(
                rows[2].update(cpu_address='8002'),
                rows[3].update(cpu_address='8003'),
                rows[10].update(cpu_address='9FFE'),
                rows[11].update(cpu_address='9FFF')))
            result=analyze(path,meta)
            self.assertEqual(result['candidate_physically_mapped_exec_hits']['835B:bank12'],1)

    def test_wrong_mirror_parity_and_legacy_capture_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path,meta=fixture(Path(d))
            edit(path,lambda rows:rows[2].update(cpu_address='8003'))
            with self.assertRaisesRegex(ValueError,'mapper event'):analyze(path,meta)
            path,meta=fixture(Path(d))
            meta.write_text(meta.read_text().replace(
                'mmc3_write_coverage=full_8000_9fff_even_odd\\n',''))
            with self.assertRaisesRegex(ValueError,'coverage'):analyze(path,meta)

    def test_incomplete_capture_refused_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            path,meta=fixture(Path(d),drop=2)
            with self.assertRaisesRegex(ValueError,'Incomplete'):analyze(path,meta)
            result=analyze(path,meta,allow_incomplete=True)
            self.assertFalse(result['complete'])
            self.assertEqual(result['events_dropped'],2)

    def test_forged_mapper_state_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path,meta=fixture(Path(d))
            edit(path,lambda rows:rows[4].update(mapped_bank='14'))
            with self.assertRaisesRegex(ValueError,'Physical PRG mapping'):
                analyze(path,meta)

    def test_mapper_mode_transition_must_match_log(self):
        with tempfile.TemporaryDirectory() as d:
            path,meta=fixture(Path(d))
            edit(path,lambda rows:rows[10].update(mmc3_mode='0'))
            with self.assertRaisesRegex(ValueError,'MMC3 snapshot'):
                analyze(path,meta)

    def test_event_sequence_and_schema_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path,meta=fixture(Path(d))
            edit(path,lambda rows:rows[2].update(seq='500'))
            with self.assertRaisesRegex(ValueError,'Lost/reordered'):
                analyze(path,meta)
            path,meta=fixture(Path(d))
            edit(path,lambda rows:rows[3].update(kind='MADE_UP'))
            with self.assertRaisesRegex(ValueError,'Unknown event kind'):
                analyze(path,meta)

    def test_identity_and_completeness_metadata_checks(self):
        with tempfile.TemporaryDirectory() as d:
            path,meta=fixture(Path(d))
            text=meta.read_text()
            meta.write_text(text.replace(MD5,'not-md5'))
            with self.assertRaisesRegex(ValueError,'ROM identity'):
                analyze(path,meta)
            meta.write_text(text.replace('initial_prg_r6=unknown','initial_prg_r6=0C'))
            with self.assertRaisesRegex(ValueError,'initial mapper'):
                analyze(path,meta)
            meta.write_text(text.replace('events_recorded=14','events_recorded=13'))
            with self.assertRaisesRegex(ValueError,'Metadata event count'):
                analyze(path,meta)

    def test_uncycled_trace_accepted_but_no_timestamps_claimed(self):
        with tempfile.TemporaryDirectory() as d:
            path,meta=fixture(Path(d),clock=False)
            self.assertEqual(analyze(path,meta)['events_recorded'],14)
            edit(path,lambda rows:rows[5].update(cpu_cycle='100'))
            with self.assertRaisesRegex(ValueError,'Unexpected cycle'):
                analyze(path,meta)

    def test_uninstrumented_pc_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path,meta=fixture(Path(d))
            edit(path,lambda rows:rows[9].update(cpu_address='FFFF'))
            with self.assertRaisesRegex(ValueError,'Unexpected EXEC'):
                analyze(path,meta)

if __name__=='__main__':unittest.main()
