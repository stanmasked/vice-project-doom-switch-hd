"""Synthetic-only Stage344 motion tests; no ROM/FM2, copyrighted pixels or PPU trace."""
from __future__ import annotations
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

source=Path(__file__).resolve().parents[1]/'tools'/'audit_private_stage344_motion.py'
spec=importlib.util.spec_from_file_location('stage344_auditor',source)
aud=importlib.util.module_from_spec(spec);spec.loader.exec_module(aud)


def synthetic_rgb(offset:int,*,flat=False,hud:int=0,sprite:int=0,right_offset:int|None=None)->bytes:
    w,h=aud.WIDTH,aud.HEIGHT
    a=bytearray(bytes((117,117,117))*w*h)
    for name,(x0,x1,y0,y1) in aud.BANDS.items():
        o=(right_offset if name=='right_environment' and right_offset is not None else offset)
        for y in range(h):
            position=y-o
            if name.endswith('marking'):
                rgb=(247,239,105) if position%21 in (0,1,2,3) else (117,117,117)
            else:
                rgb=((position*7+10)%256, (position*13+name.count('right')*30)%256,(position*17)%256)
            if flat: rgb=(117,117,117)
            for x in range(x0,x1):
                k=(y*w+x)*3;a[k:k+3]=bytes(rgb)
    # Deliberately mutate excluded sprite/HUD regions; should not shift background.
    for y in range(62+sprite,70+sprite):
        for x in range(114,135):
            idx=(y*w+x)*3;a[idx:idx+3]=bytes((sprite+55,22,31))
    for y in range(202,220):
        for x in range(22,65):
            idx=(y*w+x)*3;a[idx:idx+3]=bytes((hud+7,12,15))
    return bytes(a)


def gd(rgb:bytes)->bytes:
    raw=bytearray(aud.GD_HEADER)
    for k in range(0,len(rgb),3):raw.extend((0,*rgb[k:k+3]))
    return bytes(raw)


class Stage344SourceFree(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.samples=[420,421,422]
        self.make()

    def make(self,*,offsets=(0,0,1),flat=False,wrong_right=False,wrong_probe=False):
        self.root.joinpath('COMPLETE.txt').write_text('rom_identity_verified=yes\nfm2_readonly=yes\nframes=261\nfirst_frame=380\nlast_frame=640\n')
        for name,field,event in [('stage335_ppu_latch_ram0d_events.tsv','frame','frame_begin'),('stage341_classic_refreshaddr.tsv','core_frame_ordinal','core_frame_start')]:
            with (self.root/name).open('w',newline='') as f:
                w=csv.writer(f,delimiter='\t');w.writerow([field,'event']);w.writerows((frame,event) for frame in range(380,641))
        for frame,offset in zip(self.samples,offsets):
            rgb=synthetic_rgb(offset,flat=flat,hud=frame-420,sprite=frame-420,right_offset=offset+1 if wrong_right and frame==422 else None)
            (self.root/f'stage343_rgb_{frame:04}.gd').write_bytes(gd(rgb))
            (self.root/f'stage343_palette_{frame:04}.idx').write_bytes(bytes([12])*(aud.WIDTH*aud.HEIGHT))
        with (self.root/'stage343_rgb_palette_probes.tsv').open('w',newline='') as f:
            writer=csv.writer(f,delimiter='\t');writer.writerow(['frame','x','y','r','g','b','palette_index'])
            for frame in self.samples:
                raw=(self.root/f'stage343_rgb_{frame:04}.gd').read_bytes()
                for x,y in aud.POINTS:
                    k=12+(y*aud.WIDTH+x)*4;rgb=list(raw[k:k+3]);
                    if wrong_probe and frame==422 and x==128:rgb[0]^=1
                    writer.writerow([frame,x,y,*rgb,12])
        hashes={f.name:aud.digest(f) for f in self.root.iterdir() if f.is_file()}
        m={'format':'vpd_stage344_original_consecutive_rgb_private_manifest_v1','original_readonly':True,'newppu':0,'frames':self.samples,'palette_frames':self.samples,
           'sha256':hashes,'sealed_cpu_sha256':hashes['stage335_ppu_latch_ram0d_events.tsv'],'sealed_native_sha256':hashes['stage341_classic_refreshaddr.tsv']}
        (self.root/'manifest.json').write_text(json.dumps(m))

    def report(self):return aud.audit(self.root,self.root/'manifest.json',first=420,last=422)

    def test_background_shift_recovered_despite_sprite_hud_changes(self):
        a=self.report()
        self.assertEqual(a['masked_background_vertical_shift_pixel_counts'],{'0':1,'1':1})
        self.assertEqual(a['adjacent_frame_pairs_verified'],2)
        self.assertFalse(a['general_camera_speed_proven'])

    def test_shift_measuring_actual_native_pixel_values(self):
        rgb=synthetic_rgb(0)
        self.assertEqual(aud.score_band(rgb,synthetic_rgb(1),aud.BANDS['left_environment'],name='left_environment')[0],1)
        self.assertEqual(aud.score_band(rgb,synthetic_rgb(0),aud.BANDS['right_environment'],name='right_environment')[0],0)

    def test_flat_texture_rejected(self):
        r=synthetic_rgb(0,flat=True)
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            aud.score_band(r,r,aud.BANDS['left_marking'],name='left_marking')

    def test_background_disagreement_rejected(self):
        self.make(wrong_right=True)
        with self.assertRaisesRegex(ValueError,'bands disagree'):
            self.report()

    def test_pixel_tamper_detected_by_manifest(self):
        p=self.root/'stage343_rgb_0421.gd';d=bytearray(p.read_bytes());d[300]^=1;p.write_bytes(d)
        with self.assertRaisesRegex(ValueError,'SHA-256'):self.report()

    def test_wrong_palette_probe_rejected(self):
        self.make(wrong_probe=True)
        with self.assertRaisesRegex(ValueError,'RGB does not match'):self.report()

    def test_incorrect_gd_magic_rejected(self):
        p=self.root/'stage343_rgb_0422.gd';d=bytearray(p.read_bytes());d[0]=254;p.write_bytes(d)
        m=json.loads((self.root/'manifest.json').read_text());m['sha256'][p.name]=aud.digest(p);(self.root/'manifest.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'GD pixel format'):self.report()

    def test_indexed_source_palette_probe_mismatch(self):
        p=self.root/'stage343_palette_0421.idx';d=bytearray(p.read_bytes());d[0]=44;p.write_bytes(d)
        m=json.loads((self.root/'manifest.json').read_text());m['sha256'][p.name]=aud.digest(p);(self.root/'manifest.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'indexed source palette probe differs'):self.report()

    def test_sealed_cpu_digest_mismatch(self):
        m=json.loads((self.root/'manifest.json').read_text());m['sealed_cpu_sha256']='0'*64;(self.root/'manifest.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'sealed previous'):self.report()

    def test_missing_complete_provenance_rejected(self):
        p=self.root/'COMPLETE.txt';p.write_text('frames=261\nfirst_frame=380\nlast_frame=640\n')
        m=json.loads((self.root/'manifest.json').read_text());m['sha256'][p.name]=aud.digest(p);(self.root/'manifest.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'completion marker'):self.report()

    def test_duplicate_source_frame_anchor_rejected(self):
        p=self.root/'stage341_classic_refreshaddr.tsv';p.write_text(p.read_text()+'421\tcore_frame_start\n')
        m=json.loads((self.root/'manifest.json').read_text());m['sha256'][p.name]=aud.digest(p);m['sealed_native_sha256']=aud.digest(p);(self.root/'manifest.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'frame coverage'):self.report()

    def test_unexpected_original_frame_rejected(self):
        (self.root/'stage343_rgb_0423.gd').write_bytes((self.root/'stage343_rgb_0422.gd').read_bytes())
        with self.assertRaisesRegex(ValueError,'unselected'):self.report()

    def test_palette_missing_rejected(self):
        (self.root/'stage343_palette_0421.idx').unlink()
        with self.assertRaisesRegex(ValueError,'source'):self.report()

    def test_symlinked_original_source_rejected(self):
        p=self.root/'stage343_rgb_0422.gd';p.rename(self.root/'backing.gd');p.symlink_to('backing.gd')
        with self.assertRaisesRegex(ValueError,'linked'):self.report()

    def test_displacement_scope_restrictions(self):
        with self.assertRaisesRegex(ValueError,'unsupported original source frame interval'):
            aud.audit(self.root,self.root/'manifest.json',first=420,last=460)

if __name__=='__main__':unittest.main()
