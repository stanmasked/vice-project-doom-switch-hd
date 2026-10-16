"""Invented 6502 fixtures only; never include copyrighted game data."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from inspect_ppu_queue import inspect,SIGNATURES,BASE,LOW,HIGH

def synthetic_bank():
    bank=bytearray([0xEA]*8192)
    # Synthetic costs, eight distinct handlers and RTS opcodes.
    for i in range(1,9):
        bank[BASE+i-0xE000]=i+3
        ptr=0xE7FF+4*i
        bank[LOW+i*2-0xE000]=ptr&255
        bank[HIGH+i*2-0xE000]=ptr>>8
        bank[ptr+1-0xE000]=0x60
    opcodes={'TAX':0xAA,'TXA':0x8A,'SEC':0x38,'PHA':0x48,'RTS':0x60,'ASL':0x0A}
    for pc,statement in SIGNATURES.items():
        name=statement.split()[0]
        if len(statement.split())==1 or statement=='ASL A':
            encoded=bytes([opcodes[name]])
        else:
            raw=statement.split(' ',1)[1]
            v=int(raw.lstrip('#$').removesuffix(',X').removesuffix(',Y'),16)
            if name=='LDA':
                encoded=(bytes([0xA9,v]) if raw.startswith('#')
                    else bytes([0xB9,v&255,v>>8]) if raw.endswith(',Y')
                    else bytes([0xBD,v&255,v>>8]) if raw.endswith(',X')
                    else bytes([0xA5,v]) if v<256
                    else bytes([0xAD,v&255,v>>8]))
            elif name=='STA':
                encoded=bytes([0x85,v]) if v<256 else bytes([0x8D,v&255,v>>8])
            elif name=='SBC':encoded=bytes([0xFD,v&255,v>>8])
            elif name in ('BEQ','BCC'):
                encoded=bytes([0xF0 if name=='BEQ' else 0x90,(v-(pc+2))&255])
            elif name=='JSR':encoded=bytes([0x20,v&255,v>>8])
            elif name=='JMP':encoded=bytes([0x4C,v&255,v>>8])
            else:raise AssertionError(statement)
        bank[pc-0xE000:pc-0xE000+len(encoded)]=encoded
    return bytes(bank)

class PpuQueueTests(unittest.TestCase):
    def test_all_command_handlers_and_signatures(self):
        r=inspect(synthetic_bank())
        self.assertEqual(r['command_count'],8)
        self.assertEqual(r['frame_budget_units'],60)
        self.assertEqual(r['distinct_handler_count'],8)
        self.assertTrue(all(r['dispatcher_code_anchors'].values()))
    def test_rts_increment(self):
        r=inspect(synthetic_bank())
        self.assertEqual(r['commands'][0]['stack_return_address'],'0xE803')
        self.assertEqual(r['commands'][0]['handler_entry'],'0xE804')
    def test_signature_change(self):
        b=bytearray(synthetic_bank());b[0xE5DC-0xE000]=0
        with self.assertRaisesRegex(ValueError,'signature mismatch'):inspect(bytes(b))
    def test_zero_budget_cost(self):
        b=bytearray(synthetic_bank());b[BASE+1-0xE000]=0
        with self.assertRaisesRegex(ValueError,'Unusable command'):inspect(bytes(b))
    def test_wrong_prg_size(self):
        with self.assertRaisesRegex(ValueError,'multiple of 8KiB'):inspect(bytes(40))

if __name__=='__main__':unittest.main()
