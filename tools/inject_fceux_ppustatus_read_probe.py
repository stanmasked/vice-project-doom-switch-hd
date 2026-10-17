#!/usr/bin/env python3
"""Stage103: guarded $2002 read-clear probe on pinned FCEUX PPU source.

This is an emulator source-level register-read event, not physical VBlank.
Never modify the upstream checkout or log returned byte/pixel/ROM data.
"""
import argparse
from pathlib import Path

from audit_fceux_native_ppu_hook_sites import PPU_CPP_GIT_BLOB, git_blob_sha
from build_fceux_newppu_probe_patch import patch_source
from inject_fceux_vblank_status_probe import add_boundary_hooks

BEFORE = b"\t\tvtoggle = 0;"
CLEAR = b"\t\tPPU_status &= 0x7F;"
AFTER = b"\t\tPPUGenLatch = ret;"
GUARD = b"#if defined(VPD_NATIVE_RAW_PPU_PROBE) && defined(VPD_NATIVE_SYNTHETIC_PPUSTATUS_READ)"
CALL = b"observe_native_ppustatus_read"


def add_read_hook(patched):
    if not isinstance(patched, bytes):
        raise TypeError("Expected source byte string")
    if GUARD in patched or CALL in patched:
        raise ValueError("Already instrumented FCEUX $2002 read")
    nl = b"\r\n" if b"\r\n" in patched else b"\n"
    if b"\r\n" in patched and patched.count(b"\n") != patched.count(b"\r\n"):
        raise ValueError("Mixed source newlines")
    old = BEFORE + nl + CLEAR + nl + AFTER
    if patched.count(old) != 1:
        raise ValueError("Missing/ambiguous pinned A2002 read-clear site")
    replacement = (
        BEFORE + nl +
        GUARD + nl +
        b"\t\tconst bool vpd_2002_before = (PPU_status & 0x80) != 0;" + nl +
        b"#endif" + nl +
        CLEAR + nl +
        GUARD + nl +
        b"\t\tif (newppu) vpd_ppu_probe::observe_native_ppustatus_read(" + nl +
        b"\t\t\t(ret & 0x80) != 0, vpd_2002_before," + nl +
        b"\t\t\t(PPU_status & 0x80) != 0);" + nl +
        b"#endif" + nl +
        AFTER
    )
    result = patched.replace(old, replacement, 1)
    if result.count(GUARD) != 2 or result.count(CALL) != 1:
        raise ValueError("Incomplete guarded $2002 instrumentation")
    return result


def patch_checked(original, candidate102):
    if git_blob_sha(original) != PPU_CPP_GIT_BLOB:
        raise ValueError("Unpinned original FCEUX src/ppu.cpp")
    expected = add_boundary_hooks(patch_source(original))
    if candidate102 != expected:
        raise ValueError("Stage102 candidate does not match verified pinned patches")
    return add_read_hook(candidate102)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("stage102_candidate", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.resolve() in (args.original.resolve(),
                                 args.stage102_candidate.resolve()):
        parser.error("Refusing to overwrite a source input")
    source = patch_checked(args.original.read_bytes(),
                           args.stage102_candidate.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(source)
    print("Prepared opt-in pinned FCEUX A2002 register-read instrumentation; physical VBlank unproven")


if __name__ == "__main__":
    main()
