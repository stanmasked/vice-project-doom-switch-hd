"""ROM-free synthetic 6502 tests for the video pipeline analyzer."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from inspect_video_pipeline import (EVIDENCE, EXPECTED_SOURCES, inspect,
                                    trace_chr_selects, chr_1k_slots)

def synthetic_bank():
    b=bytearray([0xEA]*8192)
    # Invented straight-line 6502 routines, not a ROM dump.
    first=bytes([0xA2,0,0xA5,0x3D,0x8E,0,0x80,0x8D,1,0x80,
                 0xA2,1,0xA5,0x3E,0x8E,0,0x80,0x8D,1,0x80,0x60])
    b[0x8A3:0x8A3+len(first)]=first
    other=bytearray([0xA5,0x3F,0xA2,2])
    for index,r in enumerate(range(0x3F,0x43)):
        if index:other.extend([0xA5,r,0xE8])
        other.extend([0x8E,0,0x80,0x8D,1,0x80])
    other.append(0x60)
    b[0x8B8:0x8B8+len(other)]=other
    def assemble(pc,statement):
        op,raw=statement.split(' ',1)
        indexed=raw.endswith(',Y')
        value=int(raw.lstrip('#$').removesuffix(',Y'),16)
        if op=='LDA':
            if indexed:return bytes([0xB9,value&255,value>>8])
            if raw.startswith('#'):return bytes([0xA9,value])
            return bytes([0xA5,value]) if value<256 else bytes([0xAD,value&255,value>>8])
        if op=='STA':
            return bytes([0x85,value]) if value<256 else bytes([0x8D,value&255,value>>8])
        if op=='STX':return bytes([0x8E,value&255,value>>8])
        if op=='JSR':return bytes([0x20,value&255,value>>8])
        if op=='BEQ':return bytes([0xF0,(value-(pc+2))&255])
        raise AssertionError(statement)
    for _,(addr,asm,addr2,asm2) in EVIDENCE.items():
        for pc,statement in ((addr,asm),(addr2,asm2)):
            if pc is not None:
                data=assemble(pc,statement)
                b[pc-0xE000:pc-0xE000+len(data)]=data
    return bytes(b)

class PipelineTests(unittest.TestCase):
    def test_chr_bank_sources(self):
        b=synthetic_bank()
        got=trace_chr_selects(b,0xE8A3)+trace_chr_selects(b,0xE8B8)
        self.assertEqual(dict(got),{k:('ram',v) for k,v in EXPECTED_SOURCES.items()})

    def test_all_nmi_evidence(self):
        result=inspect(synthetic_bank(),131072)
        self.assertEqual(result['chr_1k_banks_in_cart'],128)
        self.assertEqual(result['reset_chr_r0_r1_ram_values'],[0,2])
        self.assertTrue(all(result['validated_nmi_ppu_evidence'].values()))

    def test_mutated_instruction_is_caught(self):
        b=bytearray(synthetic_bank())
        b[0xE5AC-0xE000]=0xEA
        with self.assertRaisesRegex(ValueError,'anchors changed'):inspect(bytes(b),131072)

    def test_unpaired_bank_write_is_caught(self):
        b=bytearray(synthetic_bank())
        b[0xE8A3-0xE000+8]=0
        with self.assertRaises(ValueError):trace_chr_selects(bytes(b),0xE8A3)

    def test_mmc3_2k_alignment_and_chr_inversion(self):
        regs=[3,7,8,9,10,11]
        self.assertEqual(chr_1k_slots(regs,False),[2,3,6,7,8,9,10,11])
        self.assertEqual(chr_1k_slots(regs,True),[8,9,10,11,2,3,6,7])
        self.assertEqual(chr_1k_slots([255]*6,False),[126,127,126,127,127,127,127,127])

    def test_bad_bank_count(self):
        with self.assertRaises(ValueError):chr_1k_slots([0]*5,False)
        with self.assertRaises(ValueError):chr_1k_slots([0]*6,False,127)
        with self.assertRaisesRegex(ValueError,'1KiB'):inspect(synthetic_bank(),1025)

if __name__=='__main__':unittest.main()
