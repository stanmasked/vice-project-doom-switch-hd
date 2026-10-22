#!/usr/bin/env python3
"""Private ROM/FM2 SHA-256 lock around FCEUX 321-frame PPU evidence.

A SHA-256 manifest created on the owner's *local* machine locks complete
ROM and FM2 file bytes before capture, and a sealed manifest checks that
the same bytes and raw PPU reports remain unchanged afterward.

Not a license to publish the digest, input paths, raw CPU data or assets.
Not a cryptographic proof of original game authenticity. Old Stage170
road observations do NOT carry comparable SHA-256 identities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from audit_private_fm2 import audit_movie, rom_payload
from audit_private_road_ppu_321_frame_phase import validate_clocked_capture

PRE="SOURCE_IDENTITY_BEFORE.json"
POST="SOURCE_IDENTITY_SEALED.json"
ARTIFACTS=("road_321_writers.tsv","road_321_postframe.tsv",
           "road_321_frame_clock.tsv","COMPLETE.txt")
VERSION="vpd-private-ppu321-identity-v1"
PRE_FIELDS={"format","rom_sha256","fm2_sha256",
            "rom_payload_md5","movie_frames","movie_power_on"}
POST_FIELDS={"format","rom_sha256","fm2_sha256","artifact_sha256",
             "content_seal_sha256","capture_completed",
             "source_rom_fm2_joined_to_legacy_road"}
MAX_FILE=100_000_000

def validate_regular(path:Path)->Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError("private source unavailable or symbolic link")
    if not 0<path.stat().st_size<=MAX_FILE:
        raise ValueError("private source size outside conservative bounds")
    return path

def sha256_file(path:Path)->str:
    digest=hashlib.sha256()
    source=validate_regular(path)
    with source.open("rb") as stream:
        while True:
            chunk=stream.read(1024*1024)
            if not chunk:break
            digest.update(chunk)
    return digest.hexdigest()

def private_dir(path:Path,require_empty:bool=False)->Path:
    if path.is_symlink() or not path.is_dir():
        raise ValueError("private evidence directory missing or linked")
    root=path.resolve(strict=True)
    if any((parent/".git").exists() for parent in (root,*root.parents)):
        raise ValueError("private evidence directory cannot be inside Git")
    if require_empty and any(root.iterdir()):
        raise ValueError("private FCEUX evidence folder must begin empty")
    return root

def _json(path:Path,expected:set[str])->dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>65536:
        raise ValueError("private identity manifest missing or linked")
    data=json.loads(path.read_text(encoding="utf8"))
    if type(data) is not dict or set(data)!=expected:
        raise ValueError("private identity manifest contains unsupported data")
    return data

def _create_json(path:Path,data:dict)->None:
    # Exclusive create, restrictive permissions. No source paths recorded.
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,"w",encoding="utf8") as stream:
        json.dump(data,stream,sort_keys=True,indent=2)
        stream.write("\n")

def source_identity(rom:Path,movie:Path)->dict:
    validate_regular(rom);validate_regular(movie)
    rom_sha=sha256_file(rom)
    fm2_sha=sha256_file(movie)
    payload_md5,_=rom_payload(rom)
    movie_audit=audit_movie(movie,rom=rom)
    if (not movie_audit["rom_identity_matched"] or
        not movie_audit["starts_from_power_on"] or
        movie_audit["frames"]<=920):
        raise ValueError("FM2 not proven to match ROM/power-on/321-window")
    if sha256_file(rom)!=rom_sha or sha256_file(movie)!=fm2_sha:
        raise ValueError("source ROM/FM2 changed during initial preflight")
    return {
        "format":VERSION,
        "rom_sha256":rom_sha,
        "fm2_sha256":fm2_sha,
        "rom_payload_md5":payload_md5.hex(),
        "movie_frames":movie_audit["frames"],
        "movie_power_on":True,
    }

def preflight(rom:Path,movie:Path,out:Path)->dict:
    dest=private_dir(out,require_empty=True)
    identity=source_identity(rom,movie)
    _create_json(dest/PRE,identity)
    return identity

def _preflight_matches(rom:Path,movie:Path,out:Path)->dict:
    before=_json(out/PRE,PRE_FIELDS)
    if (before["format"]!=VERSION or before["movie_power_on"] is not True
        or type(before["movie_frames"]) is not int
        or before["movie_frames"]<=920):
        raise ValueError("private source preflight invalid")
    fresh=source_identity(rom,movie)
    if fresh!=before:
        raise ValueError("actual source ROM/FM2 SHA-256 changed")
    return before

def capture_digest_payload(before:dict,artifacts:dict)->bytes:
    # Include both full source-file SHA-256 digests and every exact raw
    # capture file digest. Identifies one *private* input/output set.
    canonical={
        "format":VERSION,
        "rom_sha256":before["rom_sha256"],
        "fm2_sha256":before["fm2_sha256"],
        "artifact_sha256":artifacts,
    }
    return json.dumps(canonical,sort_keys=True,separators=(",",":")).encode("ascii")

def finalize(rom:Path,movie:Path,out:Path)->dict:
    root=private_dir(out)
    before=_preflight_matches(rom,movie,root)
    validate_clocked_capture(root)  # all 321 source-frame and 1284-PC gates
    hashes={name:sha256_file(root/name) for name in ARTIFACTS}
    after=_preflight_matches(rom,movie,root)
    if after!=before:
        raise ValueError("ROM/FM2 identity changed during source report hashing")
    identity={
        "format":VERSION,
        "rom_sha256":before["rom_sha256"],
        "fm2_sha256":before["fm2_sha256"],
        "artifact_sha256":hashes,
        "content_seal_sha256":hashlib.sha256(
            capture_digest_payload(before,hashes)).hexdigest(),
        "capture_completed":True,
        # Stage170's legacy road report lacks hashes. No provenance join!
        "source_rom_fm2_joined_to_legacy_road":False,
    }
    _create_json(root/POST,identity)
    return identity

def verify(rom:Path,movie:Path,out:Path)->dict:
    root=private_dir(out)
    before=_preflight_matches(rom,movie,root)
    sealed=_json(root/POST,POST_FIELDS)
    if (sealed["format"]!=VERSION or
        sealed["rom_sha256"]!=before["rom_sha256"] or
        sealed["fm2_sha256"]!=before["fm2_sha256"] or
        sealed["capture_completed"] is not True or
        sealed["source_rom_fm2_joined_to_legacy_road"] is not False or
        type(sealed["artifact_sha256"]) is not dict or
        set(sealed["artifact_sha256"])!=set(ARTIFACTS)):
        raise ValueError("private source-to-capture identity seal invalid")
    hashes={name:sha256_file(root/name) for name in ARTIFACTS}
    if hashes!=sealed["artifact_sha256"]:
        raise ValueError("private raw PPU witness changed after sealing")
    digest=hashlib.sha256(capture_digest_payload(before,hashes)).hexdigest()
    if sealed["content_seal_sha256"]!=digest:
        raise ValueError("private identity seal checksum mismatch")
    validate_clocked_capture(root)
    if before!=_preflight_matches(rom,movie,root):
        raise ValueError("ROM/FM2 input changed during verification")
    return {
        "original_source_full_file_sha256_stable":True,
        "source_fm2_matching_cartridge_payload_md5":True,
        "source_fm2_power_on_preflight":True,
        "ppu321_raw_reports_sealed":True,
        "full_ppu_writer_phase_frame_coverage":321,
        "source_cpu_events_verified":1284,
        "same_rom_fm2_joined_to_legacy_road":False,
        "effective_ppu_scroll_proven":False,
        "camera_speed_proven":False,
        "original_assets_in_public_report":False,
    }

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("preflight","finalize","verify"))
    p.add_argument("--rom",required=True,type=Path)
    p.add_argument("--movie",required=True,type=Path)
    p.add_argument("--capture-dir",required=True,type=Path)
    args=p.parse_args()
    target={"preflight":preflight,"finalize":finalize,"verify":verify}[args.action]
    target(args.rom,args.movie,args.capture_dir)
    print("VPD_PRIVATE_ROAD_PPU321_SHA256_"+args.action.upper()+"_PASS"
          " full_source_file_bytes_checked=yes"
          " original_rom_hash_disclosed=no"
          " full_road_rgb_report_identity_join_proven=no")

if __name__=="__main__":
    main()
