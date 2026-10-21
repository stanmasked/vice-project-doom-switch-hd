"""Wholly invented FCEUX storyboard test fixtures, never commercial game art."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_private_fceux_storyboard import audit, P6_HEADER, PAL_SIZE


def capture(root,frame,interval=8,start=8,stop=24,limit=3,
            rom='f'*32,unknown=0):
    prefix=root/f'frame_{frame:06d}'
    meta=prefix.with_suffix('.meta.txt')
    pal=prefix.with_suffix('.pal.bin')
    ppm=prefix.with_suffix('.ppm')
    pal.write_bytes(bytes([254])*unknown+bytes([16])*(PAL_SIZE-unknown))
    ppm.write_bytes(P6_HEADER+bytes([1,2,3])*PAL_SIZE)
    meta.write_text('\n'.join([
        'format=private_fceux_storyboard_v1',f'frame={frame}',
        f'rom_md5={rom}',f'interval={interval}',f'start_frame={start}',
        f'stop_frame={stop}',f'capture_limit={limit}',
        f'invalid_palette_values={unknown}', 'screen_size=256x240',
        'source=emu.getscreenpixel','']),encoding='ascii')
    return meta, ppm, pal


def replace(meta,old,new):
    text=meta.read_text()
    assert old in text
    meta.write_text(text.replace(old,new),encoding='ascii')


class StoryboardAuditTests(unittest.TestCase):
    def test_valid_synthetic_storyboard_pair(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,8,unknown=2)
            capture(root,16,unknown=3)
            report=audit(root)
            self.assertTrue(report['storyboard_integrity_verified'])
            self.assertEqual(report['sample_count'],2)
            self.assertEqual(report['unavailable_palette_pixels'],5)
            self.assertFalse(report['original_stage_identity_proven'])

    def test_missing_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            _,ppm,_=capture(root,8)
            ppm.unlink()
            with self.assertRaisesRegex(ValueError,'missing, symlinked'):
                audit(root)

    def test_truncated_ppm(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            _,ppm,_=capture(root,8)
            ppm.write_bytes(ppm.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError,'malformed storyboard artifact'):
                audit(root)

    def test_wrong_ppm_header(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            _,ppm,_=capture(root,8)
            ppm.write_bytes(b'P3'+ppm.read_bytes()[2:])
            with self.assertRaisesRegex(ValueError,'P6 header'):
                audit(root)

    def test_palette_invalid_index(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            _,_,pal=capture(root,8)
            raw=bytearray(pal.read_bytes());raw[4]=64;pal.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'NES palette value'):
                audit(root)

    def test_palette_missing_sentinel_count(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            meta,_,_=capture(root,8,unknown=3)
            replace(meta,'invalid_palette_values=3','invalid_palette_values=4')
            with self.assertRaisesRegex(ValueError,'palette count mismatch'):
                audit(root)

    def test_mixed_rom_identities(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,8)
            capture(root,16,rom='a'*32)
            with self.assertRaisesRegex(ValueError,'mixed storyboard sessions'):
                audit(root)

    def test_outside_window(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,32)
            with self.assertRaisesRegex(ValueError,'outside configured cadence'):
                audit(root)

    def test_mixed_interval(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,8)
            capture(root,16,interval=16)
            with self.assertRaisesRegex(ValueError,'mixed storyboard sessions'):
                audit(root)

    def test_noncanonical_name(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            m,p,q=capture(root,8)
            m.rename(root/'frame_00000008.meta.txt')
            with self.assertRaisesRegex(ValueError,'noncanonical storyboard filename'):
                audit(root)

    def test_reject_symlinked_capture(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            _,ppm,_=capture(root,8)
            ppm.unlink()
            try: ppm.symlink_to(root/'not_existing.ppm')
            except OSError as exc: self.skipTest(str(exc))
            with self.assertRaisesRegex(ValueError,'linked file'):
                audit(root)

    def test_reject_extra_unknown_file(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,8)
            (root/'unexpected.nes').write_bytes(b'NES')
            with self.assertRaisesRegex(ValueError,'unknown or linked file'):
                audit(root)

    def test_reject_duplicate_metadata_key(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            meta,_,_=capture(root,8)
            with meta.open('a') as f: f.write('frame=8\n')
            with self.assertRaisesRegex(ValueError,'duplicate storyboard metadata'):
                audit(root)

    def test_exceeds_sample_limit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,8,limit=1)
            capture(root,16,limit=1)
            with self.assertRaisesRegex(ValueError,'exceeds configured capture limit'):
                audit(root)

    def test_mismatched_frame_number(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            meta,_,_=capture(root,8)
            replace(meta,'frame=8\n','frame=9\n')
            with self.assertRaisesRegex(ValueError,'filename/metadata mismatch'):
                audit(root)

    def test_rollover_numeric_frame_order(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,999999,interval=1,start=999999,stop=1000000)
            capture(root,1000000,interval=1,start=999999,stop=1000000)
            r=audit(root)
            self.assertEqual(r['first_frame'],999999)
            self.assertEqual(r['last_frame'],1000000)


if __name__=='__main__':unittest.main()
