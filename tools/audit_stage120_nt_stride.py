#!/usr/bin/env python3
"""Stage120: fail-closed second witness for synthetic FCEUX BGData NT strides.

The Stage119 parser must separately validate the same native process log.
This module does not infer real-game geometry or cycle-accurate PPU timing.
"""
import re

PHASES = (1, 3, 5, 7)
MARKER = "VPD_STAGE120_NATIVE_NT_STRIDE_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE120_NATIVE_NT_STRIDE_PASS "
    r"fine1=(\d+) fine2=(\d+) nt_addr0=([0-9A-F]{4}) "
    r"nt_addr1=([0-9A-F]{4}) samples0=(\d+) samples1=(\d+) "
    r"transitions0=(\d+) transitions1=(\d+) invalid=0 "
    r"real_fceux_nt_to_xbuf=yes synthetic_only=yes "
    r"original_game_nt_stride_proven=no$", re.MULTILINE,
)


class NametableStrideError(ValueError):
    """Missing, duplicated or inconsistent native address-stride evidence."""


def verify_stride_report(log, fine, stage119):
    if not isinstance(log, str) or type(fine) is not int:
        raise NametableStrideError("Invalid native log or fine-X phase")
    found = list(PATTERN.finditer(log))
    if (len(found) != 1 or log.count(MARKER) != 1 or
            "VPD_STAGE120_REJECTED_NT_STRIDE" in log):
        raise NametableStrideError("Native stride witness missing, duplicated or rejected")
    f, second, addr0, addr1, samples0, samples1, changes0, changes1 = (
        int(x, 16) if i in (2, 3) else int(x)
        for i, x in enumerate(found[0].groups())
    )
    if (fine not in PHASES or f != fine or second != 8-fine or
            (addr0, addr1) != (0x2000, 0x2001) or
            (samples0, samples1) != (16, 16) or
            (changes0, changes1) != (2, 2)):
        raise NametableStrideError("Wrong phase, address or tile transitions")
    if (not isinstance(stage119, dict) or
            stage119.get("fine_first") != fine or
            stage119.get("fine_second") != second or
            stage119.get("first_nametable_source_address") != addr0 or
            stage119.get("second_nametable_source_address") != addr1 or
            stage119.get("original_game_coarse_scroll_proven") is not False):
        raise NametableStrideError("Stage119 and Stage120 describe different origins")
    return {"fine": fine, "addresses": [addr0, addr1],
            "sampled_pixels": 32, "tile_transitions": 4,
            "original_game_nt_stride_proven": False}


def verify_stride_sweep(records):
    if len(records) != 4 or [fine for fine, _ in records] != list(PHASES):
        raise NametableStrideError("Four ordered independent fine-X runs required")
    for fine, item in records:
        if (item.get("fine") != fine or item.get("addresses") != [0x2000, 0x2001] or
                item.get("sampled_pixels") != 32 or
                item.get("tile_transitions") != 4 or
                item.get("original_game_nt_stride_proven") is not False):
            raise NametableStrideError("Inconsistent native stride sweep")
    return {"phases": list(PHASES), "total_samples": 128,
            "total_tile_transitions": 16,
            "original_game_nt_stride_proven": False}
