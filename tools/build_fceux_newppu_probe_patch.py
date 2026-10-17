#!/usr/bin/env python3
"""Stage98: create a *private, opt-in* FCEUX newppu raw-step hook candidate.

Requires the exact upstream src/ppu.cpp Git blob from the pinned revision.
Never modifies the upstream checkout or generates an authenticated raster
trace. It does not normalize ppur.status.sl/cycle to NES NTSC scanlines.
"""
import argparse
from pathlib import Path

from audit_fceux_native_ppu_hook_sites import (
    FCEUX_REVISION, PPU_CPP_GIT_BLOB, git_blob_sha,
)

HEADER_NAME = "vpd_newppu_raw_step_probe.h"
INCLUDE = b'#include "debug.h"'
STEP = b'\tppur.status.cycle = (ppur.status.cycle + x) % ppur.status.end_cycle;'
OPEN = b'void runppu(int x) {'
PROBE = b'VPD_NATIVE_RAW_PPU_PROBE'


def patch_source(raw, *, require_pinned=True):
    """Patch a local private copy. Test-only opt-out allows synthetic stubs."""
    if not isinstance(raw, bytes):
        raise TypeError("Source contents must be bytes")
    if require_pinned and git_blob_sha(raw) != PPU_CPP_GIT_BLOB:
        raise ValueError("Unpinned or modified upstream FCEUX ppu.cpp source")
    if raw.count(INCLUDE) != 1 or raw.count(OPEN) != 1 or raw.count(STEP) != 1:
        raise ValueError("Missing or repeated pinned newppu hook-site anchor")
    if PROBE in raw or HEADER_NAME.encode("ascii") in raw:
        raise ValueError("Source already contains a VPD native probe")
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    if b"\r\n" in raw and raw.count(b"\n") != raw.count(b"\r\n"):
        raise ValueError("Mixed source line endings")
    old = OPEN + newline + STEP
    if raw.count(old) != 1:
        raise ValueError("runppu cycle mutation moved from pinned hook site")

    include = (INCLUDE + newline +
               b"#ifdef VPD_NATIVE_RAW_PPU_PROBE" + newline +
               b'#include "vpd_newppu_raw_step_probe.h"' + newline +
               b"#endif")
    raw = raw.replace(INCLUDE, include, 1)
    patch = (OPEN + newline +
        b"#ifdef VPD_NATIVE_RAW_PPU_PROBE" + newline +
        b"\tconst int vpd_sl = ppur.status.sl;" + newline +
        b"\tconst int vpd_cycle_before = ppur.status.cycle;" + newline +
        b"\tconst int vpd_end_cycle = ppur.status.end_cycle;" + newline +
        b"#endif" + newline +
        STEP + newline +
        b"#ifdef VPD_NATIVE_RAW_PPU_PROBE" + newline +
        b"\tvpd_ppu_probe::observe(vpd_sl, vpd_cycle_before," + newline +
        b"\t                       ppur.status.cycle, vpd_end_cycle, x);" + newline +
        b"#endif")
    raw = raw.replace(old, patch, 1)
    if raw.count(PROBE) != 3:
        raise ValueError("Missing compile-time native-probe safety switches")
    return raw


def create_candidate(source, destination, header):
    source = Path(source)
    destination = Path(destination)
    if source.resolve() == (destination / "src" / "ppu.cpp").resolve():
        raise ValueError("Refusing to rewrite the upstream PPU source")
    original = source.read_bytes()
    patched = patch_source(original)
    header_bytes = Path(header).read_bytes()
    if (b"VPD_NEWPPU_RAW_STEP_PROBE_H" not in header_bytes or
            b"vpd_ppu_probe" not in header_bytes):
        raise ValueError("Invalid portable raw-step callback header")
    folder = destination / "src"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "ppu.cpp").write_bytes(patched)
    (folder / HEADER_NAME).write_bytes(header_bytes)
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ppu_cpp", type=Path,
                        help=f"Exact FCEUX {FCEUX_REVISION} src/ppu.cpp")
    parser.add_argument("private_output_directory", type=Path,
                        help="Local, private, non-repository output directory")
    parser.add_argument("--header", type=Path,
                        default=Path(__file__).with_name(HEADER_NAME))
    args = parser.parse_args()
    folder = create_candidate(args.ppu_cpp, args.private_output_directory,
                              args.header)
    print(f"Prepared disabled-by-default, unverified FCEUX newppu raw-step probe in {folder}")


if __name__ == "__main__":
    main()
