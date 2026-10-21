"""Wholly synthetic and ROM-free-on-repo FM2 tests."""
import base64
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_fm2 import audit_movie


def fixture(root, frames=None, wrong_checksum=False, extra_header=''):
    rom=root/'fabricated.nes'
    header=b'NES\x1a'+bytes([1,1])+bytes(10)
    content=b'P'*16384+b'C'*8192
    rom.write_bytes(header+content)
    checksum=hashlib.md5(content).digest()
    if wrong_checksum:checksum=b'0'*16
    movie=root/'fabricated.fm2'
    if frames is None:frames=['|2|........|........||','|0|....T...|........||','|0|R......A|........||']
    movie.write_text('\n'.join(['version 3','emuVersion 9813','rerecordCount 7','palFlag 0',
       'romFilename fabricated','romChecksum base64:'+base64.b64encode(checksum).decode(),
       'fourscore 0','port0 1','port1 1','port2 0','FDS 0','NewPPU 0',extra_header,*frames])+'\n',encoding='ascii')
    return movie,rom

class FM2AuditTests(unittest.TestCase):
    def test_matching_rom_and_power_on(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d))
            v=audit_movie(movie,rom)
            self.assertTrue(v['rom_identity_matched'])
            self.assertTrue(v['starts_from_power_on'])
            self.assertEqual(v['frames'],3)
            self.assertEqual(v['start_button_press_frames'],[1])
            self.assertFalse(v['original_stage_proven'])

    def test_reject_rom_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d),wrong_checksum=True)
            with self.assertRaisesRegex(ValueError,'identity mismatch'):
                audit_movie(movie,rom)

    def test_rom_is_optional_but_match_unproven(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d))
            self.assertIsNone(audit_movie(movie)['rom_identity_matched'])

    def test_long_idle_windows_are_only_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            frames=['|2|........|........||']+['|0|........|........||']*15+['|0|R.......|........||']
            movie,rom=fixture(Path(d),frames)
            result=audit_movie(movie,rom,threshold=10,interval=8,frames_per_window=3)
            self.assertEqual(result['candidate_capture_windows'][0]['resume_frame'],16)
            self.assertFalse(result['original_stage_proven'])

    def test_invalid_controller_width(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d),frames=['|2|.......|........||'])
            with self.assertRaisesRegex(ValueError,'controller width'):
                audit_movie(movie,rom)

    def test_unsupported_command(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d),frames=['|64|........|........||'])
            with self.assertRaisesRegex(ValueError,'command bits'):
                audit_movie(movie,rom)

    def test_no_savestate_start_overclaim(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d),extra_header='savestate 0x00')
            self.assertFalse(audit_movie(movie,rom)['starts_from_power_on'])

    def test_invalid_frame_header(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d),extra_header='length 12')
            with self.assertRaisesRegex(ValueError,'declared length'):
                audit_movie(movie,rom)

    def test_no_raw_rom_hash_in_report(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d))
            report=str(audit_movie(movie,rom))
            self.assertNotIn(hashlib.md5(rom.read_bytes()[16:]).hexdigest(),report)

    def test_one_controller_port_and_implicit_power_on(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            movie,rom=fixture(root,frames=['|0|........|||','|0|....T...|||'])
            movie.write_text(movie.read_text().replace('port1 1\n','port1 0\n'))
            report=audit_movie(movie,rom)
            self.assertEqual(report['frames'],2)
            self.assertTrue(report['starts_from_power_on'])
            self.assertFalse(report['has_explicit_power_command_at_start'])
            self.assertEqual(report['start_button_press_frames'],[1])

    def test_reject_disabled_controller_with_input(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            movie,rom=fixture(root,frames=['|0|........|........||'])
            movie.write_text(movie.read_text().replace('port1 1\n','port1 0\n'))
            with self.assertRaisesRegex(ValueError,'controller width'):
                audit_movie(movie,rom)

    def test_supported_nes2_fixed_size_header(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            movie,rom=fixture(root)
            data=bytearray(rom.read_bytes())
            data[7]=0x08
            rom.write_bytes(data)
            report=audit_movie(movie,rom)
            self.assertTrue(report['rom_identity_matched'])

    def test_reject_nes2_exponent_encoding(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            movie,rom=fixture(root)
            data=bytearray(rom.read_bytes())
            data[7]=0x08
            data[9]=0x0f
            rom.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'exponent-size'):
                audit_movie(movie,rom)

    def test_uniform_checkpoints_when_no_idle(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d),frames=['|0|R.......|........||']*120)
            report=audit_movie(movie,rom,threshold=10)
            self.assertEqual(len(report['candidate_capture_windows']),1)
            win=report['candidate_capture_windows'][0]
            self.assertIn('uniform timeline',win['reason'])
            self.assertIsNone(win['resume_frame'])
            self.assertLess(win['capture_end_frame'],120)
            self.assertTrue(report['rom_identity_matched'])

    def test_uniform_checkpoint_does_not_claim_stages(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d),frames=['|0|R.......|........||']*3000)
            report=audit_movie(movie,rom,threshold=10)
            self.assertGreaterEqual(len(report['candidate_capture_windows']),2)
            self.assertFalse(report['original_stage_proven'])
            self.assertEqual(report['long_idle_periods'],[])

    def test_input_window_reports_only_compact_button_runs(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d))
            report=audit_movie(movie,rom,window_start=0,window_stop=2)
            window=report['input_window']
            self.assertEqual(window['frames'],3)
            self.assertEqual(window['button_runs'],[
                {'start_frame':0,'end_frame':0,
                 'player_one_buttons':'........','player_two_buttons':'........',
                 'player_one_pressed':[],'player_two_pressed':[]},
                {'start_frame':1,'end_frame':1,
                 'player_one_buttons':'....T...','player_two_buttons':'........',
                 'player_one_pressed':['T'],'player_two_pressed':[]},
                {'start_frame':2,'end_frame':2,
                 'player_one_buttons':'R......A','player_two_buttons':'........',
                 'player_one_pressed':['R','A'],'player_two_pressed':[]}
            ])
            self.assertFalse(window['visual_scene_identity_proven'])

    def test_input_window_run_length_encodes_held_buttons(self):
        with tempfile.TemporaryDirectory() as d:
            frames=['|0|R.......|........||']*4
            movie,rom=fixture(Path(d),frames=frames)
            report=audit_movie(movie,rom,window_start=1,window_stop=3)
            self.assertEqual(report['input_window']['button_runs'],[
                {'start_frame':1,'end_frame':3,
                 'player_one_buttons':'R.......','player_two_buttons':'........',
                 'player_one_pressed':['R'],'player_two_pressed':[]}
            ])

    def test_input_window_requires_both_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d))
            with self.assertRaisesRegex(ValueError,'together'):
                audit_movie(movie,rom,window_start=0)

    def test_input_window_rejects_reversed_or_out_of_timeline(self):
        with tempfile.TemporaryDirectory() as d:
            movie,rom=fixture(Path(d))
            with self.assertRaisesRegex(ValueError,'bounds'):
                audit_movie(movie,rom,window_start=2,window_stop=1)
            with self.assertRaisesRegex(ValueError,'beyond'):
                audit_movie(movie,rom,window_start=1,window_stop=3)

    def test_reject_symlink_movie(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            movie,rom=fixture(root)
            link=root/'pointer.fm2'
            try:link.symlink_to(movie)
            except OSError:self.skipTest('No symlink support')
            with self.assertRaisesRegex(ValueError,'linked'):
                audit_movie(link,rom)

if __name__=='__main__':unittest.main()
