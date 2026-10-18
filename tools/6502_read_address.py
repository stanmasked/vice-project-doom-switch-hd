#!/usr/bin/env python3
"""Stage55: tiny, strict 6502 read-address calculator for synthetic opcode bytes.

NOT a disassembler of original code, and NOT proof of a CPU bus read.
"""
from dataclasses import dataclass

# Only non-store instructions with one explicit memory-read operand.
OPS = {
    0xAD: ("LDA", "absolute", 3), 0xBD: ("LDA", "absolute_x", 3),
    0xB9: ("LDA", "absolute_y", 3), 0xB1: ("LDA", "indirect_y", 2),
    0xAE: ("LDX", "absolute", 3), 0xAC: ("LDY", "absolute", 3),
}

def _byte(value):
    return type(value) is int and 0 <= value <= 255

def calculate(opcode_bytes, *, x=None, y=None, zp_low=None, zp_high=None):
    """Return explicit status; never invent bytes or register values."""
    if not isinstance(opcode_bytes, (bytes, bytearray)) or not opcode_bytes:
        raise ValueError("opcode_bytes must be nonempty bytes")
    op=OPS.get(opcode_bytes[0])
    if op is None:
        return {"status":"unsupported_opcode","effective_address":None}
    mnemonic,mode,length=op
    if len(opcode_bytes)!=length:
        raise ValueError("Instruction byte count mismatch")
    if mode=="indirect_y":
        if y is None or zp_low is None or zp_high is None:
            return {"status":"missing_pointer_or_register","effective_address":None}
        if not all(_byte(v) for v in (y,zp_low,zp_high)):
            raise ValueError("Expected byte registers/pointer bytes")
        base=zp_low|(zp_high<<8)
        addr=(base+y)&0xFFFF
        crossed=(base&0xFF00)!=(addr&0xFF00)
    else:
        base=opcode_bytes[1]|(opcode_bytes[2]<<8)
        index=None
        if mode=="absolute_x": index=x
        elif mode=="absolute_y": index=y
        if mode!="absolute" and index is None:
            return {"status":"missing_index_register","effective_address":None}
        if index is not None and not _byte(index):
            raise ValueError("Expected byte index register")
        addr=(base+(index or 0))&0xFFFF
        crossed=(base&0xFF00)!=(addr&0xFF00)
    return {"status":"computed_from_supplied_bytes","mnemonic":mnemonic,
            "mode":mode,"effective_address":addr,"page_crossed":crossed,
            "prg_window":addr>=0x8000,
            "read_executed_proven":False,"physical_bank_proven":False}
