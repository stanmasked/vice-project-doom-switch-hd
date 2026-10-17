#!/usr/bin/env python3
"""Stage106: patch a private copy of precisely pinned FCEUX MMC3 $8001 source.

Observe actual CHR register writes (selectors 0..5), not CHR pixel fetches.
Never alter the upstream checkout or publish ROM/mapper register contents.
"""
import argparse
from pathlib import Path

from audit_fceux_native_ppu_hook_sites import git_blob_sha

MMC3_CPP_GIT_BLOB = "f0eb52d2a862c87e1617974de0d0c486aac6c240"
INCLUDES = b'#include "mapinc.h"\r\n#include "mmc3.h"'
TAIL = (
    b'\t\tcase 7:\r\n'
    b'\t\t\tpwrap(0xA000, V);\r\n'
    b'\t\t\tbreak;\r\n'
    b'\t\t}\r\n'
    b'\t\tbreak;\r\n'
    b'\t}\r\n'
    b'\tcase 0xA000:'
)
GUARD = b"#if defined(VPD_NATIVE_SYNTHETIC_MMC3_CHR) && defined(VPD_NATIVE_SYNTHETIC_EVENT_ORDER)"
CALL = b"vpd_ppu_probe::observe_native_mmc3_chr_write"


def patch_mmc3(raw, *, require_pinned=True):
    if not isinstance(raw, bytes):
        raise TypeError("Expected raw C++ source bytes")
    if require_pinned and git_blob_sha(raw) != MMC3_CPP_GIT_BLOB:
        raise ValueError("MMC3 source differs from pinned FCEUX Git blob")
    if GUARD in raw or CALL in raw:
        raise ValueError("MMC3 native CHR hook already instrumented")
    if b"\r\n" in raw and raw.count(b"\n") != raw.count(b"\r\n"):
        raise ValueError("Mixed upstream MMC3 line endings")
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    includes = INCLUDES.replace(b"\r\n", nl)
    tail = TAIL.replace(b"\r\n", nl)
    if raw.count(includes) != 1 or raw.count(tail) != 1:
        raise ValueError("Missing/ambiguous pinned MMC3 CHR write anchors")
    start = raw.find(b"DECLFW(MMC3_CMDWrite) {")
    end = raw.find(b"DECLFW(MMC3_IRQWrite) {")
    if not (0 <= start < end and
            raw.count(b"DECLFW(MMC3_CMDWrite) {") == 1 and
            start < raw.find(tail) < end):
        raise ValueError("MMC3 $8001 write site outside expected handler")
    includes_after = (
        includes + nl + GUARD + nl +
        b'#include "../vpd_newppu_raw_step_probe.h"' + nl + b"#endif"
    )
    original = b"\t\t}\r\n\t\tbreak;\r\n\t}\r\n\tcase 0xA000:".replace(b"\r\n", nl)
    inserted = (
        b"\t\t}" + nl + GUARD + nl +
        b"\t\tif ((MMC3_cmd & 0x07) < 6)" + nl +
        b"\t\t\tvpd_ppu_probe::observe_native_mmc3_chr_write(" +
        b"MMC3_cmd & 0x07, V);" + nl +
        b"#endif" + nl +
        b"\t\tbreak;" + nl + b"\t}" + nl + b"\tcase 0xA000:"
    )
    if raw.count(original) != 1:
        raise ValueError("Cannot safely locate unique MMC3 register-data case tail")
    result = raw.replace(includes, includes_after, 1).replace(original, inserted, 1)
    if result.count(GUARD) != 2 or result.count(CALL) != 1:
        raise ValueError("Incomplete CHR-register instrumentation")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pinned_mmc3_cpp", type=Path)
    parser.add_argument("private_destination", type=Path)
    args = parser.parse_args()
    if args.pinned_mmc3_cpp.resolve() == args.private_destination.resolve():
        parser.error("Refusing to overwrite FCEUX original MMC3 source")
    content = patch_mmc3(args.pinned_mmc3_cpp.read_bytes())
    args.private_destination.parent.mkdir(parents=True, exist_ok=True)
    args.private_destination.write_bytes(content)
    print("Stage106: pinned MMC3 CHR write hook generated into private runner only")


if __name__ == "__main__":
    main()
