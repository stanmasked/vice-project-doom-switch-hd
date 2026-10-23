"""Synthetic-only tests; never include actual Nintendo imagery or FM2 in GitHub."""
from __future__ import annotations
import csv
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

DIR=Path(__file__).resolve().parents[1]/'tools'
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,DIR/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
cap=load('stage343_gen','generate_private_stage343_rgb_capture.py')
aud=load('stage343_audit','audit_private_stage343_rgb_frames.py')

class Stage343Synthetic(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.p=Path(tmp.name)
        (self.p/'COMPLETE.txt').write_text('rom_identity_verified=yes\nfm2_readonly=yes\nfirst_frame=380\nlast_frame=381\nframes=2\n')
        self.cpu=self.p/'stage335_ppu_latch_ram0d_events.tsv'
        self.native=self.p/'stage341_classic_refreshaddr.tsv'
        self.cpu.write_text('frame\tevent\n380\tframe_begin\n381\tframe_begin\n')
        self.native.write_text('core_frame_ordinal\tevent\n380\tcore_frame_start\n381\tcore_frame_start\n')
        colors={380:(18,23,31),381:(22,30,46)}
        with (self.p/'stage343_rgb_palette_probes.tsv').open('w',newline='') as f:
            wr=csv.writer(f,delimiter='\t');wr.writerow(['frame','x','y','r','g','b','palette_index'])
            for frame,rgb in colors.items():
                rgbdata=bytes((0,*rgb))*(aud.W*aud.H)
                (self.p/f'stage343_rgb_{frame:04d}.gd').write_bytes(aud.HEADER+rgbdata)
                for x,y in aud.POINTS:wr.writerow([frame,x,y,*rgb,5])
        (self.p/'stage343_palette_0380.idx').write_bytes(bytes([5])*(aud.W*aud.H))

    def call(self):
        return aud.audit(self.p,frames=(380,381),palette_frames=(380,),
                         cpu_sha=aud.checksum(self.cpu),native_sha=aud.checksum(self.native),first=380,last=381)

    def test_valid_synthetic_image_and_palette_source(self):
        obj=self.call();self.assertEqual(obj['authentic_sampled_rgb_frames'],2)
        self.assertEqual(obj['source_rgb_palette_probe_matches'],12)
        self.assertEqual(obj['consecutive_sample_pairs_with_pixel_differences'],1)
        self.assertFalse(obj['effective_per_pixel_road_scroll_proven'])

    def test_reject_malformed_gd_magic(self):
        p=self.p/'stage343_rgb_0380.gd';b=bytearray(p.read_bytes());b[0]=254;p.write_bytes(b)
        with self.assertRaisesRegex(ValueError,'GD header'):self.call()

    def test_reject_wrong_native_resolution(self):
        p=self.p/'stage343_rgb_0380.gd';p.write_bytes(p.read_bytes()[:-4])
        with self.assertRaisesRegex(ValueError,'GD header'):self.call()

    def test_reject_source_pixel_mismatch(self):
        p=self.p/'stage343_rgb_0381.gd';b=bytearray(p.read_bytes());b[12]=0;b[13]^=1;p.write_bytes(b)
        with self.assertRaisesRegex(ValueError,'RGB palette probe'):self.call()

    def test_reject_paletted_source_mismatch(self):
        p=self.p/'stage343_palette_0380.idx';p.write_bytes(bytes([4])*(aud.W*aud.H))
        with self.assertRaisesRegex(ValueError,'palette index'):self.call()

    def test_reject_missing_palette(self):
        (self.p/'stage343_palette_0380.idx').unlink()
        with self.assertRaisesRegex(ValueError,'palette plane missing'):self.call()

    def test_reject_wrong_source_hash(self):
        with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):
            aud.audit(self.p,frames=(380,381),palette_frames=(380,),cpu_sha='0'*64,
                      native_sha=aud.checksum(self.native),first=380,last=381)

    def test_reject_missing_original_frame_anchor(self):
        self.native.write_text('core_frame_ordinal\tevent\n380\tcore_frame_start\n')
        with self.assertRaisesRegex(ValueError,'frame witness coverage'):self.call()

    def test_generator_authenticates_stage335_script(self):
        stub=(cap.ANCHOR_CALLBACK+cap.ANCHOR_FRAME_END+cap.ANCHOR_COMPLETE).encode()
        h=hashlib.sha256(stub).hexdigest()
        modified=cap.generate(stub,expected_sha256=h,frames=(380,400),palette_frames=(380,))
        self.assertIn(b'gui.gdscreenshot(false)',modified)
        self.assertIn(b'255 and h[2]==254',modified)
        with self.assertRaisesRegex(ValueError,'full-file SHA-256'):
            cap.generate(stub,expected_sha256='0'*64,frames=(380,400),palette_frames=(380,))

    def test_generator_rejects_ambiguous_layout(self):
        stub=(cap.ANCHOR_CALLBACK*2+cap.ANCHOR_FRAME_END+cap.ANCHOR_COMPLETE).encode()
        with self.assertRaisesRegex(ValueError,'layout'):
            cap.generate(stub,expected_sha256=hashlib.sha256(stub).hexdigest(),frames=(380,),palette_frames=(380,))

    def test_generator_rejects_palette_outside_images(self):
        stub=(cap.ANCHOR_CALLBACK+cap.ANCHOR_FRAME_END+cap.ANCHOR_COMPLETE).encode()
        with self.assertRaisesRegex(ValueError,'palette frame'):
            cap.generate(stub,expected_sha256=hashlib.sha256(stub).hexdigest(),frames=(380,),palette_frames=(381,))

    def test_reject_unrequested_palette_frame(self):
        (self.p/'stage343_palette_0381.idx').write_bytes(bytes([5])*(aud.W*aud.H))
        with self.assertRaisesRegex(ValueError,'unrequested palette'):self.call()

if __name__=='__main__':unittest.main()
