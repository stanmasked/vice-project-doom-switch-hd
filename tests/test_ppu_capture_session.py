"""Stage79: ROM-free session manifest and event-stream integrity regression."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from verify_ppu_capture_session import verify,SessionError

TOKEN='0011002200330044'


def data_file(path, size):
    Path(path).write_bytes(bytes([size%251])*size)


class CaptureSessionTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.manifest=self.root/'ppu_capture_session.meta.txt'
        self.props={
            'format':'fceux_ppu_session_v1', 'session_id':TOKEN,
            'complete':'yes','first_callback_frame':'1',
            'last_callback_frame':'3','frame_callbacks':'3',
            'frame_callback_gaps':'0','frames_captured':'2',
            'capture_frames':'1,3', 'events_recorded':'3',
            'events_dropped':'0','callback_errors':'0',
            'capture_failures':'0','cycle_trace_available':'yes',
            'mmc3_write_coverage':'full_8000_ffff_even_odd',
            'ppu_register_write_coverage':'full_2000_3fff_mod8',
            'ppu_status_read_coverage':'full_2000_3fff_mod8'}
        self.frames={}
        for index,frame in enumerate((1,3),1):
            props={'format':'fceux_ppu_snapshot_v4', 'session_id':TOKEN,
                'session_snapshot_index':str(index),
                'capture_scope':'frame_prefix_only', 'frame':str(frame),
                'register_log_complete':'yes','dropped_register_writes':'0',
                'callback_errors':'0',
                'mmc3_write_coverage':'full_8000_ffff_even_odd',
                'ppu_register_write_coverage':'full_2000_3fff_mod8',
                'ppu_status_read_coverage':'full_2000_3fff_mod8',
                'cycle_trace_available':'yes','logged_register_writes':str(index+1),
                'screen_reference':'no'}
            path=self.root/f'frame_{frame:06d}'
            self.frames[frame]=props
            data_file(str(path)+'.ppu.bin',0x4000)
            data_file(str(path)+'.ram.bin',0x800)
        self.log=self.root/'mmc3_video_writes.tsv'
        self.log.write_text('frame\taddress\tvalue\n1\t8002\t80\n1\t3FFA\t00\n3\t200D\t22\n')
        self.cyclelog=self.root/'mmc3_ppu_cycles.tsv'
        self.cyclelog.write_text('frame\tcpu_cycle\taddress\tvalue\tkind\n'
                                 '1\t10\t8002\t80\tW\n1\t14\t3FFA\t00\tR\n'
                                 '3\t100\t200D\t22\tW\n')
        self.finalize()

    def finalize(self):
        self.manifest.write_text(''.join(f'{k}={v}\n' for k,v in self.props.items()))
        for frame,props in self.frames.items():
            (self.root/f'frame_{frame:06d}.meta.txt').write_text(
                ''.join(f'{k}={v}\n' for k,v in props.items()))

    def fail_if(self, expr):
        with self.assertRaises(SessionError):
            verify(self.manifest,require_cycle=expr)

    def test_complete_session(self):
        report=verify(self.manifest,require_cycle=True)
        self.assertTrue(report['complete'])
        self.assertEqual(report['frames_captured'],2)
        self.assertEqual(report['events_checked'],3)
        self.assertTrue(report['cycles_checked'])
        self.assertFalse(report['game_identity_authenticated'])
        self.assertFalse(report['stage_geometry_proven'])

    def test_pending_manifest_is_not_completed(self):
        self.manifest.write_text('capture_in_progress=yes\n')
        self.fail_if(True)

    def test_stale_frame_from_previous_session_rejected(self):
        self.frames[3]['session_id']='deadbeef00112233';self.finalize()
        self.fail_if(True)

    def test_missing_frame_snapshot(self):
        (self.root/'frame_000003.ppu.bin').unlink()
        self.fail_if(True)

    def test_truncated_frame_snapshot(self):
        (self.root/'frame_000003.ram.bin').write_bytes(b'!')
        self.fail_if(True)

    def test_truncated_frame_metadata(self):
        (self.root/'frame_000003.meta.txt').write_text('complete=yes\n')
        self.fail_if(True)

    def test_missing_event_record(self):
        self.log.write_text('frame\taddress\tvalue\n1\t8002\t80\n1\t3FFA\t00\n')
        self.fail_if(True)

    def test_wrong_event_and_cycle_pair(self):
        self.cyclelog.write_text(self.cyclelog.read_text().replace('3\t100\t200D\t22','3\t100\t2005\t22'))
        self.fail_if(True)

    def test_wrong_ppustatus_kind(self):
        self.cyclelog.write_text(self.cyclelog.read_text().replace('3FFA\t00\tR','3FFA\t00\tW'))
        self.fail_if(True)

    def test_duplicate_or_out_of_order_frames(self):
        self.props['capture_frames']='3,1';self.finalize()
        self.fail_if(True)

    def test_gap_even_if_complete_flag_claimed(self):
        self.props['frame_callback_gaps']='1';self.finalize()
        self.fail_if(True)
        self.props['frame_callback_gaps']='0';self.props['frame_callbacks']='2';self.finalize()
        self.fail_if(True)

    def test_late_drops_make_all_prior_frames_unverified(self):
        self.props['events_dropped']='1';self.finalize()
        self.fail_if(True)
        self.props['events_dropped']='0';self.props['callback_errors']='1';self.finalize()
        self.fail_if(True)

    def test_duplicate_manifest_key(self):
        with self.manifest.open('a') as stream: stream.write('complete=yes\n')
        self.fail_if(True)

    def test_missing_cycle_trace_and_opt_out(self):
        self.cyclelog.unlink()
        self.fail_if(True)
        self.props['cycle_trace_available']='no'
        for meta in self.frames.values():meta['cycle_trace_available']='no'
        self.finalize()
        r=verify(self.manifest)
        self.assertFalse(r['cycles_checked'])
        self.fail_if(True)

    def test_legacy_frame_metadata_not_session_proof(self):
        self.frames[1].pop('capture_scope');self.finalize()
        self.fail_if(True)

    def test_ordered_but_unverified_frame_checkpoint(self):
        self.frames[1]['logged_register_writes']='3'
        self.frames[3]['logged_register_writes']='2'
        self.finalize();self.fail_if(True)

    def test_rendered_screen_files_required_when_selected(self):
        self.frames[1]['screen_reference']='yes';self.finalize()
        self.fail_if(True)
        data_file(self.root/'frame_000001.screen.rgb.bin',256*240*3)
        data_file(self.root/'frame_000001.screen.pal.bin',256*240)
        self.assertTrue(verify(self.manifest)['complete'])


if __name__=='__main__': unittest.main()
