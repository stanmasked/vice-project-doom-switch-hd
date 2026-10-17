#!/usr/bin/env python3
"""Stage121: verify native buffered attribute-fetch evidence for synthetic ROM.

This is not evidence of original-game palettes, NES PPU dot accuracy or
unmodified FCEUX graphics. Requires an independently accepted Stage119 report.
"""
import re

MARKER = "VPD_STAGE121_NATIVE_ATTRIBUTE_PASS"
PATTERN = re.compile(
    r"^VPD_STAGE121_NATIVE_ATTRIBUTE_PASS "
    r"fine1=(\d+) fine2=(\d+) attr_addr0=([0-9A-F]{4}) "
    r"attr_addr1=([0-9A-F]{4}) samples0=16 samples1=16 invalid=0 "
    r"buffered_attribute_to_pixel=yes synthetic_only=yes "
    r"original_game_palette_proven=no$", re.MULTILINE,
)


class AttributeEvidenceError(ValueError):
    pass


def expected_attribute_address(ntaddr):
    if type(ntaddr) is not int or not 0x2000 <= ntaddr < 0x3000:
        raise AttributeEvidenceError("Invalid nametable source address")
    return (0x23C0 + (ntaddr & 0x0C00) +
            ((ntaddr & 0x0380) >> 4) + ((ntaddr & 0x001C) >> 2))


def verify_attribute_report(log, fine, stage119, stage120):
    if type(fine) is not int or fine not in (1, 3, 5, 7) or not isinstance(log, str):
        raise AttributeEvidenceError("Invalid native log/phase")
    matches = list(PATTERN.finditer(log))
    if (len(matches) != 1 or log.count(MARKER) != 1 or
            "VPD_STAGE121_REJECTED_ATTRIBUTE" in log):
        raise AttributeEvidenceError("Missing, duplicated or rejected attribute witness")
    f, second, a0, a1 = matches[0].groups()
    a0, a1 = int(a0, 16), int(a1, 16)
    if int(f) != fine or int(second) != 8-fine:
        raise AttributeEvidenceError("Mismatched fine-X phases")
    if not isinstance(stage119, dict) or not isinstance(stage120, dict):
        raise AttributeEvidenceError("Both earlier native witness reports required")
    source0 = stage119.get("first_nametable_source_address")
    source1 = stage119.get("second_nametable_source_address")
    if (stage119.get("fine_first") != fine or
            stage119.get("fine_second") != 8-fine or
            stage119.get("original_game_coarse_scroll_proven") is not False or
            stage120.get("fine") != fine or
            stage120.get("addresses") != [source0, source1] or
            stage120.get("original_game_nt_stride_proven") is not False or
            (a0, a1) != (expected_attribute_address(source0),
                         expected_attribute_address(source1))):
        raise AttributeEvidenceError("NT origin and palette quadrant provenance differ")
    return {"fine": fine, "attribute_addresses": [a0, a1],
            "sampled_pixels": 32, "original_game_palette_proven": False}


def verify_attribute_sweep(records):
    if len(records) != 4 or [f for f, _ in records] != [1, 3, 5, 7]:
        raise AttributeEvidenceError("All four ordered native phases required")
    for f, report in records:
        if (report.get("fine") != f or report.get("sampled_pixels") != 32 or
                report.get("original_game_palette_proven") is not False):
            raise AttributeEvidenceError("Incomplete attribute proof")
    origins = [tuple(item["attribute_addresses"]) for _, item in records]
    if len(set(origins)) != 1:
        raise AttributeEvidenceError("Attribute table differs across fine-X controls")
    return {"phases": [1, 3, 5, 7], "total_samples": 128,
            "original_game_palette_proven": False}
