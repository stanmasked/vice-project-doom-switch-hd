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
