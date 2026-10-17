"""Stage79: ROM-free session manifest and event-stream integrity regression."""
import json
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from verify_ppu_capture_session import verify,SessionError
from audit_ppu_reference_frames import analyze_verified

TOKEN='0011002200330044'


def data_file(path, size):
    Path(path).write_bytes(bytes([size%251])*size)


def log_prefixes(path):
    lines=Path(path).read_bytes().splitlines(keepends=True)
    checksum=1
    result=[]
    for line in lines:
        checksum=zlib.adler32(line,checksum)
        result.append(f'{checksum:08X}')
    return result


def checksum_file(path):
    return f'{zlib.adler32(Path(path).read_bytes()):08X}'


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
            'cycle_order_policy':'nondecreasing_v1',
            'cycle_regressions':'0','cycle_equal_adjacent':'0',
            'cycle_regressions_same_frame':'0',
            'cycle_regressions_between_frames':'0',
            'frame_callback_clock_mode':'disabled',
            'frame_callback_clock_samples':'0',
            'frame_callback_clock_boundary_proven':'no',
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
                'frame_callback_clock_scope':'disabled',
                'frame_callback_cpu_cycle':'not_captured',
                'screen_reference':'no'}
            path=self.root/f'frame_{frame:06d}'
            self.frames[frame]=props
            data_file(str(path)+'.ppu.bin',0x4000)
            data_file(str(path)+'.ram.bin',0x800)
            props['snapshot_checksum']='adler32_v1'
            props['ppu_adler32']=checksum_file(str(path)+'.ppu.bin')
            props['ram_adler32']=checksum_file(str(path)+'.ram.bin')
            props['screen_rgb_adler32']='not_captured'
            props['screen_pal_adler32']='not_captured'
        self.log=self.root/'mmc3_video_writes.tsv'
        self.log.write_text('frame\taddress\tvalue\n1\t8002\t80\n1\t3FFA\t00\n3\t200D\t22\n')
        self.cyclelog=self.root/'mmc3_ppu_cycles.tsv'
        self.cyclelog.write_text('frame\tcpu_cycle\taddress\tvalue\tkind\n'
                                 '1\t10\t8002\t80\tW\n1\t14\t3FFA\t00\tR\n'
                                 '3\t100\t200D\t22\tW\n')
        frame_prefix=log_prefixes(self.log)
        cycle_prefix=log_prefixes(self.cyclelog)
        self.props['event_checksum']='adler32_v1'
        self.props['frame_log_adler32']=frame_prefix[-1]
        self.props['cycle_log_adler32']=cycle_prefix[-1]
        for frame,props in self.frames.items():
            checkpoint=int(props['logged_register_writes'])
            props['event_checksum']='adler32_v1'
            props['frame_log_prefix_adler32']=frame_prefix[checkpoint]
            props['cycle_log_prefix_adler32']=cycle_prefix[checkpoint]
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
        self.assertTrue(report['snapshot_bytes_verified'])
        self.assertEqual(report['checksum_type'],'adler32_v1')
        self.assertTrue(report['event_logs_verified'])
        self.assertEqual(report['event_checksum_type'],'adler32_v1')
        self.assertTrue(report['cpu_cycle_order_verified'])
        self.assertEqual(report['cpu_cycle_equal_adjacent'],0)

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
        self.props['cycle_log_adler32']='not_captured'
        for meta in self.frames.values():
            meta['cycle_trace_available']='no'
            meta['cycle_log_prefix_adler32']='not_captured'
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
        self.frames[1]['screen_rgb_adler32']=checksum_file(
            self.root/'frame_000001.screen.rgb.bin')
        self.frames[1]['screen_pal_adler32']=checksum_file(
            self.root/'frame_000001.screen.pal.bin')
        self.finalize()
        self.assertTrue(verify(self.manifest)['complete'])

    def test_same_size_ppu_bit_flip_is_rejected(self):
        path=self.root/'frame_000001.ppu.bin'
        payload=bytearray(path.read_bytes())
        payload[123]^=0x01
        path.write_bytes(payload)
        self.assertEqual(path.stat().st_size,0x4000)
        with self.assertRaisesRegex(SessionError,'checksum mismatch'):
            verify(self.manifest)

    def test_same_size_ram_bit_flip_is_rejected(self):
        path=self.root/'frame_000003.ram.bin'
        payload=bytearray(path.read_bytes())
        payload[-3]^=0x40
        path.write_bytes(payload)
        self.assertEqual(path.stat().st_size,0x800)
        with self.assertRaisesRegex(SessionError,'checksum mismatch'):
            verify(self.manifest)

    def test_missing_snapshot_checksum_metadata_rejected(self):
        self.frames[1].pop('ppu_adler32')
        self.finalize()
        self.fail_if(True)

    def test_legacy_snapshot_without_checksum_version_rejected(self):
        self.frames[3].pop('snapshot_checksum')
        self.finalize()
        self.fail_if(True)

    def test_bad_declared_checksum_rejected(self):
        self.frames[1]['ram_adler32']='00000000'
        self.finalize()
        with self.assertRaisesRegex(SessionError,'checksum mismatch'):
            verify(self.manifest)

    def test_no_screen_requires_explicit_absent_checksum(self):
        self.frames[3]['screen_rgb_adler32']='00000000'
        self.finalize()
        self.fail_if(True)

    def test_screen_same_size_corruption_rejected(self):
        self.frames[1]['screen_reference']='yes'
        rgb=self.root/'frame_000001.screen.rgb.bin'
        pal=self.root/'frame_000001.screen.pal.bin'
        data_file(rgb,256*240*3)
        data_file(pal,256*240)
        self.frames[1]['screen_rgb_adler32']=checksum_file(rgb)
        self.frames[1]['screen_pal_adler32']=checksum_file(pal)
        self.finalize()
        self.assertTrue(verify(self.manifest)['complete'])
        data=bytearray(rgb.read_bytes());data[2048]^=0x20;rgb.write_bytes(data)
        with self.assertRaisesRegex(SessionError,'checksum mismatch'):
            verify(self.manifest)
        data[2048]^=0x20;rgb.write_bytes(data)
        palbytes=bytearray(pal.read_bytes());palbytes[11]^=0x01
        pal.write_bytes(palbytes)
        with self.assertRaisesRegex(SessionError,'checksum mismatch'):
            verify(self.manifest)

    def test_same_size_frame_tsv_corruption_rejected(self):
        text=self.log.read_text()
        self.log.write_text(text.replace('1\t8002\t80','1\t8002\t81'))
        self.assertEqual(len(self.log.read_bytes()),len(text.encode()))
        with self.assertRaisesRegex(SessionError,'checksum mismatch'):
            verify(self.manifest)

    def test_same_size_cycle_counter_corruption_rejected(self):
        text=self.cyclelog.read_text()
        self.cyclelog.write_text(text.replace('1\t10\t','1\t11\t'))
        self.assertEqual(len(self.cyclelog.read_bytes()),len(text.encode()))
        with self.assertRaisesRegex(SessionError,'checksum mismatch'):
            verify(self.manifest)

    def test_wrong_frame_log_prefix_rejected(self):
        self.frames[1]['frame_log_prefix_adler32']='00000000'
        self.finalize()
        with self.assertRaisesRegex(SessionError,'frame_log_prefix_adler32'):
            verify(self.manifest)

    def test_wrong_cycle_log_prefix_rejected(self):
        self.frames[3]['cycle_log_prefix_adler32']='00000000'
        self.finalize()
        with self.assertRaisesRegex(SessionError,'cycle_log_prefix_adler32'):
            verify(self.manifest)

    def test_missing_full_log_checksum_rejected(self):
        self.props.pop('frame_log_adler32')
        self.finalize()
        self.fail_if(True)

    def test_missing_cycle_log_checksum_rejected(self):
        self.props.pop('cycle_log_adler32')
        self.finalize()
        self.fail_if(True)

    def test_legacy_missing_event_checksum_schema_rejected(self):
        self.props.pop('event_checksum')
        self.finalize()
        self.fail_if(True)

    def test_wrong_event_checksum_version_rejected(self):
        self.frames[1]['event_checksum']='legacy'
        self.finalize()
        self.fail_if(True)

    def test_truncated_event_log_does_not_pass(self):
        original=self.log.read_bytes()
        self.log.write_bytes(original[:-1])
        self.fail_if(True)

    def test_truncated_cycle_log_does_not_pass(self):
        original=self.cyclelog.read_bytes()
        self.cyclelog.write_bytes(original[:-1])
        self.fail_if(True)

    def test_no_clock_requires_not_captured_checksums(self):
        self.props['cycle_trace_available']='no'
        self.props['cycle_log_adler32']='not_captured'
        for meta in self.frames.values():
            meta['cycle_trace_available']='no'
            meta['cycle_log_prefix_adler32']='not_captured'
        self.finalize()
        self.assertFalse(verify(self.manifest)['cycles_checked'])
        self.props['cycle_log_adler32']='00000000'
        self.finalize()
        self.fail_if(False)

    def test_rewritten_full_checksum_does_not_hide_damaged_frame_prefix(self):
        # Even if someone recalculates a corrupted full TSV checksum,
        # per-frame prefix commitments still detect the divergent bytes.
        content=self.log.read_text()
        self.log.write_text(content.replace('1\t8002\t80','1\t8002\t81'))
        self.cyclelog.write_text(self.cyclelog.read_text().replace('1\t10\t8002\t80','1\t10\t8002\t81'))
        self.props['frame_log_adler32']=checksum_file(self.log)
        self.props['cycle_log_adler32']=checksum_file(self.cyclelog)
        self.finalize()
        with self.assertRaisesRegex(SessionError,'frame_log_prefix_adler32'):
            verify(self.manifest)

    def test_snapshot_checkpoint_bound_to_exact_prefix(self):
        self.assertTrue(verify(self.manifest)['event_logs_verified'])
        self.frames[1]['logged_register_writes']='1'
        self.finalize()
        with self.assertRaisesRegex(SessionError,'frame_log_prefix_adler32'):
            verify(self.manifest)


    def test_same_frame_counter_regression_with_updated_checksum_rejected(self):
        self.cyclelog.write_text(self.cyclelog.read_text().replace('1\t14\t3FFA','1\t9\t3FFA'))
        self.props['cycle_log_adler32']=checksum_file(self.cyclelog)
        self.frames[1]['cycle_log_prefix_adler32']=log_prefixes(self.cyclelog)[2]
        self.frames[3]['cycle_log_prefix_adler32']=log_prefixes(self.cyclelog)[3]
        self.finalize()
        with self.assertRaisesRegex(SessionError,'CPU-cycle counter decreased'):
            verify(self.manifest)

    def test_cross_frame_counter_regression_with_updated_checksum_rejected(self):
        self.cyclelog.write_text(self.cyclelog.read_text().replace('3\t100\t200D','3\t3\t200D'))
        self.props['cycle_log_adler32']=checksum_file(self.cyclelog)
        self.frames[3]['cycle_log_prefix_adler32']=log_prefixes(self.cyclelog)[3]
        self.finalize()
        with self.assertRaisesRegex(SessionError,'CPU-cycle counter decreased'):
            verify(self.manifest)

    def test_equal_adjacent_cycle_counters_accepted_when_declared(self):
        self.cyclelog.write_text(self.cyclelog.read_text().replace('1\t14\t3FFA','1\t10\t3FFA'))
        self.props['cycle_equal_adjacent']='1'
        self.props['cycle_log_adler32']=checksum_file(self.cyclelog)
        self.frames[1]['cycle_log_prefix_adler32']=log_prefixes(self.cyclelog)[2]
        self.frames[3]['cycle_log_prefix_adler32']=log_prefixes(self.cyclelog)[3]
        self.finalize()
        report=verify(self.manifest)
        self.assertTrue(report['cpu_cycle_order_verified'])
        self.assertEqual(report['cpu_cycle_equal_adjacent'],1)

    def test_equal_adjacent_cycle_count_lie_rejected(self):
        self.cyclelog.write_text(self.cyclelog.read_text().replace('1\t14\t3FFA','1\t10\t3FFA'))
        self.props['cycle_log_adler32']=checksum_file(self.cyclelog)
        self.frames[1]['cycle_log_prefix_adler32']=log_prefixes(self.cyclelog)[2]
        self.frames[3]['cycle_log_prefix_adler32']=log_prefixes(self.cyclelog)[3]
        self.finalize()
        with self.assertRaisesRegex(SessionError,'equality count'):
            verify(self.manifest)

    def test_nonzero_regression_claim_invalidates_complete_manifest(self):
        self.props['cycle_regressions']='1'
        self.finalize()
        self.fail_if(True)

    def test_same_frame_regression_claim_rejected(self):
        self.props['cycle_regressions_same_frame']='1'
        self.finalize()
        self.fail_if(True)

    def test_cross_frame_regression_claim_rejected(self):
        self.props['cycle_regressions_between_frames']='1'
        self.finalize()
        self.fail_if(True)

    def test_legacy_manifest_missing_counter_policy_rejected(self):
        self.props.pop('cycle_order_policy')
        self.finalize()
        self.fail_if(True)

    def test_no_clock_mode_has_zero_order_counts(self):
        self.props['cycle_trace_available']='no'
        self.props['cycle_log_adler32']='not_captured'
        for meta in self.frames.values():
            meta['cycle_trace_available']='no'
            meta['cycle_log_prefix_adler32']='not_captured'
        self.finalize()
        result=verify(self.manifest)
        self.assertFalse(result['cpu_cycle_order_verified'])
        self.props['cycle_equal_adjacent']='1'
        self.finalize()
        self.fail_if(False)


    def test_future_frame_event_in_prior_snapshot_rejected_even_with_matching_hashes(self):
        # An event labeled frame 3 cannot already belong to the TSV prefix
        # committed by a snapshot taken at callback frame 1. Rewrite BOTH
        # traces and recompute all Adler digests to isolate this invariant.
        for log in (self.log,self.cyclelog):
            log.write_text(log.read_text().replace('\n1\t','\n3\t'))
        frame_hashes=log_prefixes(self.log)
        cycle_hashes=log_prefixes(self.cyclelog)
        self.props['frame_log_adler32']=frame_hashes[-1]
        self.props['cycle_log_adler32']=cycle_hashes[-1]
        for m in self.frames.values():
            count=int(m['logged_register_writes'])
            m['frame_log_prefix_adler32']=frame_hashes[count]
            m['cycle_log_prefix_adler32']=cycle_hashes[count]
        self.finalize()
        with self.assertRaisesRegex(SessionError,'future event-frame label'):
            verify(self.manifest)

    def test_verified_snapshot_frame_order_is_not_physical_frame_proof(self):
        result=verify(self.manifest)
        self.assertTrue(result['snapshot_event_frame_order_verified'])
        self.assertFalse(result['physical_frame_boundaries_proven'])
        self.assertEqual(result['frame_callback_clock_samples_verified'],0)
        self.assertFalse(result['frame_callback_clock_boundary_proven'])

    def test_counter_overflow_accepted_neither_by_checksum_nor_parser(self):
        self.cyclelog.write_text(self.cyclelog.read_text().replace('1\t14\t3FFA',
                                                                '1\t9007199254740992\t3FFA'))
        self.props['cycle_log_adler32']=checksum_file(self.cyclelog)
        self.frames[1]['cycle_log_prefix_adler32']=log_prefixes(self.cyclelog)[2]
        self.frames[3]['cycle_log_prefix_adler32']=log_prefixes(self.cyclelog)[3]
        self.finalize()
        with self.assertRaisesRegex(SessionError,'exact integer range'):
            verify(self.manifest)


    def enable_callback_clock(self, first=20, second=120):
        self.props['frame_callback_clock_mode']='sampled_snapshots_v1'
        self.props['frame_callback_clock_samples']='2'
        for frame,cycle in ((1,first),(3,second)):
            self.frames[frame]['frame_callback_clock_scope']='captured_frame_sample'
            self.frames[frame]['frame_callback_cpu_cycle']=str(cycle)
        self.finalize()

    def test_callback_clock_samples_bracket_snapshot_events(self):
        self.enable_callback_clock()
        r=verify(self.manifest, require_cycle=True)
        self.assertEqual(r['frame_callback_clock_samples_verified'],2)
        self.assertFalse(r['frame_callback_clock_boundary_proven'])

    def test_callback_clock_before_committed_event_rejected(self):
        self.enable_callback_clock(first=9)
        with self.assertRaisesRegex(SessionError,'precedes committed event'):
            verify(self.manifest)

    def test_callback_clock_after_next_event_rejected(self):
        self.enable_callback_clock(first=101)
        with self.assertRaisesRegex(SessionError,'later than next event'):
            verify(self.manifest)

    def test_callback_clock_decreasing_across_snapshots_rejected(self):
        self.enable_callback_clock(first=30,second=20)
        self.frames[3]['logged_register_writes']='2'
        self.frames[3]['frame_log_prefix_adler32']=log_prefixes(self.log)[2]
        self.frames[3]['cycle_log_prefix_adler32']=log_prefixes(self.cyclelog)[2]
        self.finalize()
        with self.assertRaisesRegex(SessionError,'regressed between snapshots'):
            verify(self.manifest)

    def test_callback_clock_missing_metadata_rejected(self):
        self.enable_callback_clock()
        self.frames[3].pop('frame_callback_cpu_cycle')
        self.finalize()
        self.fail_if(True)

    def test_callback_clock_rejects_unsafe_integer(self):
        self.enable_callback_clock(second=9007199254740992)
        with self.assertRaisesRegex(SessionError,'not an exact integer'):
            verify(self.manifest)

    def test_callback_clock_requires_cpu_cycle_trace(self):
        self.enable_callback_clock()
        self.props['cycle_trace_available']='no'
        self.props['cycle_log_adler32']='not_captured'
        for m in self.frames.values():
            m['cycle_trace_available']='no'
            m['cycle_log_prefix_adler32']='not_captured'
        self.finalize()
        with self.assertRaisesRegex(SessionError,'requires CPU-cycle trace'):
            verify(self.manifest)

    def test_callback_clock_count_lie_rejected(self):
        self.enable_callback_clock()
        self.props['frame_callback_clock_samples']='1'
        self.finalize()
        with self.assertRaisesRegex(SessionError,'sample count mismatch'):
            verify(self.manifest)

    def test_callback_clock_unproven_boundary_claim_rejected(self):
        self.props['frame_callback_clock_boundary_proven']='yes'
        self.finalize()
        self.fail_if(True)

    def test_callback_clock_disabled_must_not_have_implicit_sample(self):
        self.frames[1]['frame_callback_cpu_cycle']='20'
        self.finalize()
        self.fail_if(True)

    def test_stage88_inventory_reports_verified_snapshot_evidence_only(self):
        report=analyze_verified(self.manifest,require_cycle=True)
        self.assertEqual(report['format'],'vpd_verified_ppu_reference_inventory_v1')
        self.assertTrue(report['session_verified'])
        self.assertEqual(report['frames_captured'],2)
        self.assertEqual(report['recorded_event_count'],3)
        self.assertEqual(report['snapshot_comparisons'],1)
        self.assertEqual(report['rendered_screen_reference_frames'],0)
        self.assertEqual(report['distinct_chr_1k_page_versions_by_slot'],[1]*8)
        self.assertEqual(report['distinct_nametable_tile_versions_by_slot'],[1]*4)
        pair=report['changes_between_snapshots'][0]
        self.assertEqual((pair['from_frame'],pair['to_frame']),(1,3))
        self.assertEqual(pair['frame_label_distance'],2)
        self.assertEqual(pair['frame_labels_between_snapshots'],1)
        self.assertEqual(pair['ppu_changed_bytes'],0)
        self.assertEqual(pair['ram_changed_bytes'],0)
        self.assertTrue(report['cpu_cycle_trace_verified'])
        self.assertFalse(report['capture_provenance']['original_first_level_identified'])
        self.assertFalse(report['capture_provenance']['level_geometry_reconstructed'])
        self.assertFalse(report['capture_provenance']['physical_frame_boundaries_proven'])

    def test_stage88_inventory_counts_per_region_changes(self):
        ppu_path=self.root/'frame_000003.ppu.bin'
        data=bytearray(ppu_path.read_bytes())
        for position in (0x0002,0x2000,0x23C0,0x3F00):
            data[position]^=1
        ppu_path.write_bytes(data)
        self.frames[3]['ppu_adler32']=checksum_file(ppu_path)
        ram_path=self.root/'frame_000003.ram.bin'
        data=bytearray(ram_path.read_bytes())
        for position in (0x600,0x700):
            data[position]^=1
        ram_path.write_bytes(data)
        self.frames[3]['ram_adler32']=checksum_file(ram_path)
        self.finalize()
        report=analyze_verified(self.manifest)
        difference=report['changes_between_snapshots'][0]
        self.assertEqual(difference['ppu_changed_bytes'],4)
        self.assertEqual(difference['ram_changed_bytes'],2)
        self.assertEqual(difference['chr_1k_changed_bytes'],[1]+[0]*7)
        self.assertEqual(difference['nametable_tile_cells_changed'],[1,0,0,0])
        self.assertEqual(difference['nametable_attribute_bytes_changed'],[1,0,0,0])
        self.assertEqual(difference['palette_memory_bytes_changed'],1)
        self.assertEqual(difference['queue_0600_changed_bytes'],1)
        self.assertEqual(difference['oam_source_0700_changed_slots'],1)
        self.assertEqual(report['distinct_chr_1k_page_versions_by_slot'],[2]+[1]*7)
        self.assertEqual(report['distinct_nametable_tile_versions_by_slot'],[2,1,1,1])

    def test_stage88_inventory_rejects_corrupt_same_size_snapshot(self):
        p=self.root/'frame_000001.ppu.bin'
        data=bytearray(p.read_bytes());data[0x2010]^=1;p.write_bytes(data)
        with self.assertRaisesRegex(SessionError,'checksum mismatch'):
            analyze_verified(self.manifest)

    def test_stage88_inventory_rejects_unfinished_manifest(self):
        self.manifest.write_text('capture_in_progress=yes\\n')
        with self.assertRaises(SessionError):
            analyze_verified(self.manifest)

    def test_stage88_inventory_counts_only_verified_rendered_references(self):
        frame=1
        prefix=self.root/f'frame_{frame:06d}'
        self.frames[frame]['screen_reference']='yes'
        for suffix,size,key in (
            ('.screen.rgb.bin',256*240*3,'screen_rgb_adler32'),
            ('.screen.pal.bin',256*240,'screen_pal_adler32'),
        ):
            path=Path(str(prefix)+suffix)
            data_file(path,size)
            self.frames[frame][key]=checksum_file(path)
        self.finalize()
        report=analyze_verified(self.manifest)
        self.assertEqual(report['rendered_screen_reference_frames'],1)
        self.assertTrue(report['snapshots'][0]['rendered_screen_reference_present'])
        self.assertFalse(report['snapshots'][1]['rendered_screen_reference_present'])
        Path(str(prefix)+'.screen.pal.bin').write_bytes(b'bad')
        with self.assertRaises(SessionError):
            analyze_verified(self.manifest)

    def test_stage88_inventory_cycle_is_optional_unless_required(self):
        self.props['cycle_trace_available']='no'
        self.props['cycle_log_adler32']='not_captured'
        for meta in self.frames.values():
            meta['cycle_trace_available']='no'
            meta['cycle_log_prefix_adler32']='not_captured'
        self.finalize()
        report=analyze_verified(self.manifest)
        self.assertFalse(report['cpu_cycle_trace_verified'])
        with self.assertRaisesRegex(SessionError,'CPU-cycle trace unavailable'):
            analyze_verified(self.manifest,require_cycle=True)

    def test_stage88_inventory_json_excludes_original_raw_data(self):
        report=analyze_verified(self.manifest)
        text=json.dumps(report)
        self.assertNotIn('palette_entries_changed',text)
        self.assertNotIn('ppu_sha256',text)
        self.assertNotIn('original_rom_md5',text)
        self.assertNotIn('raw_ppu',text)
        self.assertEqual(len(report['snapshots']),2)


if __name__=='__main__': unittest.main()
