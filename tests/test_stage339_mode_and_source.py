"""Synthetic-only regression tests: do not ship the owner's FM2 in GitHub."""
import hashlib
import importlib.util
import pathlib
import tempfile
import unittest

TOOLS=pathlib.Path(__file__).resolve().parents[1]/'tools'
def load(name,mod):
    spec=importlib.util.spec_from_file_location(name,TOOLS/mod)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

fm2=load('stage339_fm2','audit_private_stage339_core_mode.py')
src=load('stage339_source','verify_stage339_legacy_ppu_source.py')

class Stage339ModeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.movie=pathlib.Path(self.temp.name)/'synthetic.fm2'
    def make(self,*,newppu='0',pal='0',frames=3,extra='',v='3',duplicated=False):
        text=f'version {v}\nemuVersion 22020\npalFlag {pal}\nNewPPU {newppu}\n'+extra
        if duplicated: text+='NewPPU 0\n'
        text+='|0|........|\n'*frames
        self.movie.write_text(text)
        return hashlib.sha256(self.movie.read_bytes()).hexdigest()
    def test_canonical_legacy_source(self):
        sha=self.make();d=fm2.enforce_legacy_ntsc(fm2.parse_fm2(self.movie,expected_sha256=sha),3)
        self.assertTrue(d['legacy_ppu_source'])
        self.assertTrue(d['ntsc_source'])
        self.assertFalse(d['ppu_scanline_dot_observed'])
    def test_newppu_explicitly_rejected(self):
        self.make(newppu='1')
        with self.assertRaisesRegex(ValueError,'core/TV mode'):
            fm2.enforce_legacy_ntsc(fm2.parse_fm2(self.movie),3)
    def test_pal_explicitly_rejected(self):
        self.make(pal='1')
        with self.assertRaisesRegex(ValueError,'core/TV mode'):
            fm2.enforce_legacy_ntsc(fm2.parse_fm2(self.movie),3)
    def test_fullfile_sha_mismatch(self):
        self.make()
        with self.assertRaisesRegex(ValueError,'SHA-256'):
            fm2.parse_fm2(self.movie,expected_sha256='0'*64)
    def test_bad_hash_rejected(self):
        self.make()
        with self.assertRaisesRegex(ValueError,'invalid private source hash'):
            fm2.parse_fm2(self.movie,expected_sha256='oops')
    def test_frame_count_guard(self):
        self.make(frames=2)
        with self.assertRaisesRegex(ValueError,'input count'):
            fm2.enforce_legacy_ntsc(fm2.parse_fm2(self.movie),3)
    def test_duplicate_flag_rejected(self):
        self.make(duplicated=True)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            fm2.parse_fm2(self.movie)
    def test_missing_mode_rejected(self):
        self.movie.write_text('version 3\nemuVersion 20\npalFlag 0\n|0|........|\n')
        with self.assertRaisesRegex(ValueError,'required'):
            fm2.parse_fm2(self.movie)
    def test_bad_version_rejected(self):
        self.make(v='2')
        with self.assertRaisesRegex(ValueError,'version'):
            fm2.parse_fm2(self.movie)
    def test_invalid_mode_bytes(self):
        self.make(newppu='maybe')
        with self.assertRaisesRegex(ValueError,'non-numeric'):
            fm2.parse_fm2(self.movie)
    def test_symlink_rejected(self):
        self.make()
        link=self.movie.parent/'link.fm2'; link.symlink_to(self.movie)
        with self.assertRaisesRegex(ValueError,'linked'):
            fm2.parse_fm2(link)
    def test_non_ascii_rejected(self):
        self.movie.write_bytes(b'version 3\nNewPPU 0\npalFlag 0\nemuVersion 2\n\xff\n|0|........|\n')
        with self.assertRaisesRegex(ValueError,'non-ASCII'):
            fm2.parse_fm2(self.movie)
    def test_no_input_rejected(self):
        self.movie.write_text('version 3\nemuVersion 1\npalFlag 0\nNewPPU 0\n')
        with self.assertRaisesRegex(ValueError,'required'):
            fm2.parse_fm2(self.movie)
    def test_source_contract_bad_blob(self):
        p=self.movie.parent/'ppu.cpp';p.write_bytes(b'123456'*500)
        with self.assertRaisesRegex(ValueError,'pinned'):
            src.verify(p)
    def test_source_contract_one_anchor_only_fails(self):
        p=self.movie.parent/'ppu.cpp'
        # Contract can be tested on a synthetic fixture with its synthetic Git blob.
        content='int newppu = 0;\n' + '\n'.join(src.REQUIRED[1:])+'\nstatic void Fixit1(void) {}\nstatic void Fixit1(void);\nif (newppu) {}\n' + ('//padding\n'*120)
        p.write_text(content)
        blob=hashlib.sha1(f'blob {p.stat().st_size}\0'.encode()+p.read_bytes()).hexdigest()
        self.assertTrue(src.verify(p,expected_blob_sha=blob)['pinned_upstream_source_verified'])
        p.write_text(content+src.REQUIRED[1]+'\n')
        blob=hashlib.sha1(f'blob {p.stat().st_size}\0'.encode()+p.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            src.verify(p,expected_blob_sha=blob)
    def test_source_contract_tiny_rejected(self):
        p=self.movie.parent/'ppu.cpp';p.write_text('x')
        with self.assertRaisesRegex(ValueError,'invalid'):
            src.verify(p)

if __name__=='__main__':unittest.main()
