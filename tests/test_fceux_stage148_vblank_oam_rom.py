"""Stage148 ROM byte audits for a CPU-generated OAM change between frames.

These tests prove the generated 6502 instructions and timing-matched
controls, NOT actual CPU execution or real PPU XBuf. Native validation is
a separate stage gate.
"""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))

from make_stage144_stable_frame_rom import make_rom as make_stage144
from make_stage148_vblank_oam_rom import (
    MODES,POLL_VBLANK,STA_OAMADDR,STA_OAMDATA,
    BANK_SIZE,LOAD_ADDR,PRG_START,PRG_END,
    _program,_tail_site,make_rom,transform)


class VblankWrittenOAM(unittest.TestCase):
    def test_nine_activation_and_noop_have_identical_cpu_timing(self):
        for position in (250,1111,4000):
            with self.subTest(position=position):
                changed=_program("activate_ninth",position)
                control=_program("preserve_eight",position)
                self.assertEqual(len(changed),len(control))
                self.assertEqual(changed[:5],POLL_VBLANK)
                self.assertEqual(control[:5],POLL_VBLANK)
                self.assertEqual(changed[5:10],
                                 bytes((0xA9,31))+STA_OAMADDR)
                self.assertEqual(control[5:10],changed[5:10])
                self.assertEqual(changed.count(STA_OAMDATA),5)
                self.assertEqual(control.count(STA_OAMDATA),5)
                self.assertEqual(changed[-3:],control[-3:])
                self.assertEqual(changed[-3],0x4C)
                self.assertEqual(int.from_bytes(changed[-2:],"little"),
                                 LOAD_ADDR+position+len(changed)-3)
                self.assertEqual(
                    [changed[11+5*i] for i in range(5)],
                    [160,120,2,0,64])
                self.assertEqual(
                    [control[11+5*i] for i in range(5)],
                    [64,255,255,255,255])
                differences=[i for i,(a,b) in enumerate(zip(changed,control))
                             if a!=b]
                self.assertEqual(differences,[11,16,21,26,31])

    def test_fixtures_only_change_five_immediates_per_prg_bank(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            original=root/"old.nes"
            a=root/"activate.nes"
            b=root/"preserve.nes"
            make_stage144(original,"eight_visible")
            ha=make_rom(a,"activate_ninth")
            hb=make_rom(b,"preserve_eight")
            old=original.read_bytes()
            changed=a.read_bytes()
            control=b.read_bytes()
            self.assertEqual(changed,transform(old,"activate_ninth"))
            self.assertEqual(control,transform(old,"preserve_eight"))
            self.assertEqual(hashlib.sha256(changed).hexdigest(),ha)
            self.assertEqual(hashlib.sha256(control).hexdigest(),hb)
            self.assertEqual(len(old),49168)
            self.assertEqual(changed[:16],old[:16])
            self.assertEqual(control[:16],old[:16])
            self.assertEqual(changed[PRG_END:],old[PRG_END:])
            self.assertEqual(control[PRG_END:],old[PRG_END:])
            sites=_tail_site(old)
            self.assertEqual(len(sites),4)
            diffs={i for i,(x,y) in enumerate(zip(changed,control)) if x!=y}
            expected={
                start+position+11+5*i for start,position,_ in sites
                for i in range(5)}
            self.assertEqual(diffs,expected)
            self.assertEqual(len(diffs),20)
            for start,position,_ in sites:
                self.assertEqual(changed[start:start+position],
                                 old[start:start+position])
                self.assertEqual(control[start:start+position],
                                 old[start:start+position])
                self.assertEqual(
                    changed[start+position:start+position+38],
                    _program("activate_ninth",position))
                self.assertEqual(
                    control[start+position:start+position+38],
                    _program("preserve_eight",position))

    def test_both_fixtures_use_valid_6502_vblank_poll_branch(self):
        self.assertEqual(POLL_VBLANK,bytes((0x2c,0x02,0x20,0x10,0xfb)))
        # BIT $2002 reads the real PPU status flag; BPL $FB repeats
        # while bit7 is clear. The branch displacement -5 returns to BIT.
        self.assertEqual(int.from_bytes(POLL_VBLANK[-1:],"little",signed=True),
                         -5)
        program=_program("activate_ninth",500)
        self.assertEqual(program[:3],bytes((0x2C,0x02,0x20)))
        self.assertEqual(program[3:5],bytes((0x10,0xFB)))
        self.assertEqual(program[10:12],bytes((0xA9,160)))
        self.assertEqual(program[12:15],STA_OAMDATA)
        self.assertEqual(program[15:17],bytes((0xA9,120)))
        self.assertEqual(program[17:20],STA_OAMDATA)

    def test_fail_closed_on_corruption_and_unsupported_modes(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"base.nes"
            make_stage144(path,"eight_visible")
            old=path.read_bytes()
            site=_tail_site(old)[0]
            start,pos,_=site
            mutated=bytearray(old)
            mutated[start+pos]=0xEA
            tampered=bytearray(old)
            tampered[start+pos+3]=0x07
            broken_mirror=bytearray(old)
            broken_mirror[PRG_START+BANK_SIZE+45]^=0x01
            for name,invalid in (
                ("empty",b""),
                ("short",old[:-1]),
                ("header",b"\x00"+old[1:]),
                ("jmp",bytes(mutated)),
                ("pad",bytes(tampered)),
                ("mirror",bytes(broken_mirror))
            ):
                with self.subTest(name=name),self.assertRaises(ValueError):
                    transform(invalid,"activate_ninth")
            for invalid in (None,True,"", "nine_early","invalid"):
                with self.subTest(mode=invalid):
                    output=Path(td)/"invalid.nes"
                    with self.assertRaises(ValueError):
                        make_rom(output,invalid)
                    self.assertFalse(output.exists())

    def test_rom_is_not_game_data(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/"a.nes"
            b=Path(td)/"b.nes"
            make_rom(a,MODES[0])
            make_rom(b,MODES[1])
            self.assertNotEqual(a.read_bytes(),b.read_bytes())
            self.assertEqual(a.read_bytes()[:4],b"NES\x1a")
            self.assertTrue(all(not p.name.lower().endswith(".nro")
                                for p in Path(td).iterdir()))


if __name__=="__main__":
    unittest.main()
