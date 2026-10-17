#!/usr/bin/env python3
"""Stage102: pinned, private FCEUX newppu PPU_status assignment instrumentation.

Adds two source-level status-write notifications to the Stage98 patched
*original pinned ppu.cpp*. Never labels them physical NES VBlank edges.
"""
import argparse
from pathlib import Path

from build_fceux_newppu_probe_patch import patch_source
from audit_fceux_native_ppu_hook_sites import PPU_CPP_GIT_BLOB, git_blob_sha

ENTER = b"\t\tPPU_status |= 0x80;"
ENTER_AFTER = b"\t\tppuphase = PPUPHASE_VBL;"
CLEAR = b"\t\tPPU_status = 0;"
CLEAR_AFTER = b"\t\t//this early out caused metroid to fail to boot."
GUARD = b"#if defined(VPD_NATIVE_RAW_PPU_PROBE) && defined(VPD_NATIVE_SYNTHETIC_VBLANK)"


def add_boundary_hooks(raw):
    if not isinstance(raw, bytes):
        raise TypeError("Candidate must be bytes")
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    if b"\r\n" in raw and raw.count(b"\n") != raw.count(b"\r\n"):
        raise ValueError("Mixed PPU source newlines")
    first = ENTER + nl + ENTER_AFTER
    second = CLEAR + nl + CLEAR_AFTER
    if GUARD in raw or b"observe_native_status_assignment" in raw:
        raise ValueError("Already instrumented native VBlank status assignment")
    if raw.count(first) != 1 or raw.count(second) != 1:
        raise ValueError("Missing/ambiguous pinned newppu status-write anchors")
    e = (ENTER + nl + GUARD + nl +
         b"\t\tvpd_ppu_probe::observe_native_status_assignment(" +
         b"true, (PPU_status & 0x80) != 0);" + nl +
         b"#endif" + nl + ENTER_AFTER)
    c = (CLEAR + nl + GUARD + nl +
         b"\t\tvpd_ppu_probe::observe_native_status_assignment(" +
         b"false, (PPU_status & 0x80) != 0);" + nl +
         b"#endif" + nl + CLEAR_AFTER)
    updated = raw.replace(first, e, 1).replace(second, c, 1)
    if updated.count(GUARD) != 2 or updated.count(
            b"observe_native_status_assignment") != 2:
        raise ValueError("Incomplete native status-write hook injection")
    return updated


def patch_checked(original, existing):
    if git_blob_sha(original) != PPU_CPP_GIT_BLOB:
        raise ValueError("Original FCEUX src/ppu.cpp is not the pinned blob")
    expected = patch_source(original)
    if expected != existing:
        raise ValueError("Existing Stage98 source patch is not byte-for-byte verified")
    return add_boundary_hooks(existing)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pinned_original", type=Path)
    parser.add_argument("stage98_candidate", type=Path)
    parser.add_argument("stage102_output", type=Path)
    args = parser.parse_args()
    for path in (args.pinned_original, args.stage98_candidate):
        if path.resolve() == args.stage102_output.resolve():
            parser.error("Refusing to replace original or Stage98 candidate")
    candidate = patch_checked(args.pinned_original.read_bytes(),
                              args.stage98_candidate.read_bytes())
    args.stage102_output.parent.mkdir(parents=True, exist_ok=True)
    args.stage102_output.write_bytes(candidate)
    print("Prepared private FCEUX native status-write candidate; no hardware VBlank proof")


if __name__ == "__main__":
    main()
