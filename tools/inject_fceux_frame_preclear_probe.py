#!/usr/bin/env python3
"""Stage105: private FCEUX pre-clear PPUSTATUS hook from exact pinned source.

Hook immediately before the source-frame PPU_status = 0 assignment.
The existing Stage102 after-clear callback is retained unchanged.
"""
import argparse
from pathlib import Path

from audit_fceux_native_ppu_hook_sites import PPU_CPP_GIT_BLOB, git_blob_sha
from build_fceux_newppu_probe_patch import patch_source
from inject_fceux_vblank_status_probe import add_boundary_hooks
from inject_fceux_ppustatus_read_probe import add_read_hook

CLEAR = b"\t\tPPU_status = 0;"
STAGE102_GUARD = (
    b"#if defined(VPD_NATIVE_RAW_PPU_PROBE) && "
    b"defined(VPD_NATIVE_SYNTHETIC_VBLANK)"
)
GUARD = (
    b"#if defined(VPD_NATIVE_RAW_PPU_PROBE) && "
    b"defined(VPD_NATIVE_SYNTHETIC_PRECLEAR)"
)
CALL = b"vpd_ppu_probe::preclear_before_assignment"


def insert_preclear(source):
    if not isinstance(source, bytes):
        raise TypeError("Expected original FCEUX C++ bytes")
    if GUARD in source or CALL in source:
        raise ValueError("Stage105 pre-clear site already instrumented")
    nl = b"\r\n" if b"\r\n" in source else b"\n"
    if b"\r\n" in source and source.count(b"\r\n") != source.count(b"\n"):
        raise ValueError("Mixed upstream line endings")
    anchor = CLEAR + nl + STAGE102_GUARD + nl
    if source.count(anchor) != 1:
        raise ValueError("Missing/duplicate guarded source-frame clear")
    snippet = (
        GUARD + nl +
        b"\t\tvpd_ppu_probe::preclear_before_assignment(" +
        b"(PPU_status & 0x80) != 0);" + nl +
        b"#endif" + nl + anchor
    )
    updated = source.replace(anchor, snippet, 1)
    if updated.count(GUARD) != 1 or updated.count(CALL) != 1:
        raise ValueError("Incomplete Stage105 pre-clear hook")
    return updated


def patch_checked(original, stage103):
    if git_blob_sha(original) != PPU_CPP_GIT_BLOB:
        raise ValueError("Unpinned original FCEUX ppu.cpp source blob")
    expected = add_read_hook(add_boundary_hooks(patch_source(original)))
    if expected != stage103:
        raise ValueError("Unverified Stage103 candidate, refusing pre-clear patch")
    return insert_preclear(stage103)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pinned_original", type=Path)
    parser.add_argument("stage103_candidate", type=Path)
    parser.add_argument("private_output", type=Path)
    args = parser.parse_args()
    if args.private_output.resolve() in (
        args.pinned_original.resolve(), args.stage103_candidate.resolve()
    ):
        parser.error("Refusing to overwrite source inputs")
    patched = patch_checked(args.pinned_original.read_bytes(),
                            args.stage103_candidate.read_bytes())
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    args.private_output.write_bytes(patched)
    print("Private Stage105 FCEUX pre-clear candidate generated; NES hardware timing unproven")


if __name__ == "__main__":
    main()
