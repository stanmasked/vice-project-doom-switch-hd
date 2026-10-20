#!/usr/bin/env python3
"""Fail-closed check of actual NeXium-created SD witness.

No claim about physical pixels, frame pacing or original game content.
"""
import argparse
from pathlib import Path
import re

EXPECTED_FNV = "5947277116621119566"
MARKER = "VPD_ROMFREE_DEMO_WITNESS_V1"
COLUMNS = (
    "cycle", "frames", "shots", "hits", "health", "fnv",
    "state_match", "frame_submitted", "original_game_proven"
)


def audit_lines(raw):
    if not raw or len(raw) > 2048 or b"\r" in raw or b"\x00" in raw:
        raise ValueError("missing, oversized or binary guest trace")
    text = raw.decode("ascii")
    if not text.endswith("\n"):
        raise ValueError("missing final newline")
    lines = text.splitlines()
    if not (1 <= len(lines) <= 4):
        raise ValueError("guest report must contain 1-4 bounded cycles")
    for count, line in enumerate(lines, 1):
        parts = line.split()
        if len(parts) != len(COLUMNS) + 1 or parts[0] != MARKER:
            raise ValueError("unexpected witness line format")
        pairs = []
        for part in parts[1:]:
            if part.count("=") != 1:
                raise ValueError("malformed witness key/value")
            pairs.append(part.split("=", 1))
        keys = tuple(k for k, _ in pairs)
        if keys != COLUMNS or len(set(keys)) != len(keys):
            raise ValueError("reordered or repeated witness fields")
        props = dict(pairs)
        if any(not re.fullmatch(r"[0-9]+", props[key]) for key in
               ("cycle", "frames", "shots", "hits", "health", "fnv")):
            raise ValueError("noncanonical numeric fields")
        expected = {
            "cycle": str(count), "frames": "200", "shots": "11",
            "hits": "3", "health": "0", "fnv": EXPECTED_FNV,
            "state_match": "yes", "frame_submitted": "yes",
            "original_game_proven": "no"
        }
        if props != expected:
            raise ValueError(f"guest cycle {count} mismatches golden state")
    return len(lines)



# Verify exactly the release-asset proof emitted by verify_nexium_release.py,
# rather than the obsolete hardcoded sha256sum "...: OK" convention.
# The upstream tag moves; this records the *observed verified* artifact ID.
RELEASE_KEYS = (
    "release_id", "asset_id", "tag", "published_at", "archive_sha256",
    "asset_size_bytes", "digest_source", "mutable_tag"
)
RELEASE_LOG = re.compile(
    r"VERIFIED: official GitHub NeXium release asset SHA-256 "
    r"([0-9a-f]{64}) asset_id ([1-9][0-9]*)\n?"
)

def audit_release_evidence(folder):
    folder = Path(folder)
    proof = folder / "emulator-release-attestation.txt"
    log = folder / "emulator-sha256.txt"
    meta = folder / "metadata.txt"
    for path in (proof, log, meta):
        if not path.is_file() or path.stat().st_size > 8192:
            raise ValueError("NeXium publisher release attestation absent/oversized")
    data = proof.read_text("ascii")
    metadata = meta.read_text("ascii")
    if not data.endswith("\n") or not metadata.endswith("\n"):
        raise ValueError("truncated NeXium archive identity metadata")
    expected = ["nexium_"+name for name in RELEASE_KEYS]
    rows = data.splitlines()
    if len(rows) != len(expected):
        raise ValueError("incomplete NeXium publisher release attestation")
    fields = {}
    for line, key in zip(rows, expected):
        if not line.startswith(key+"=") or line.count("=") != 1:
            raise ValueError("noncanonical NeXium publisher asset field")
        fields[key] = line[len(key)+1:]
        if metadata.splitlines().count(line) != 1:
            raise ValueError("NeXium metadata does not match verified asset")
    if (not re.fullmatch(r"[1-9][0-9]*",fields["nexium_release_id"]) or
        not re.fullmatch(r"[1-9][0-9]*",fields["nexium_asset_id"]) or
        fields["nexium_tag"] != "nightly" or
        not re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T"
                         r"[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
                         fields["nexium_published_at"]) or
        not re.fullmatch(r"[0-9a-f]{64}",fields["nexium_archive_sha256"]) or
        not re.fullmatch(r"[1-9][0-9]*",fields["nexium_asset_size_bytes"]) or
        fields["nexium_digest_source"] != "github_release_api" or
        fields["nexium_mutable_tag"] != "yes"):
        raise ValueError("invalid NeXium release digest provenance")
    matched = RELEASE_LOG.fullmatch(log.read_text("ascii"))
    if not matched or (matched.group(1) != fields["nexium_archive_sha256"] or
                       matched.group(2) != fields["nexium_asset_id"]):
        raise ValueError("NeXium release verification log mismatch")
    return fields["nexium_archive_sha256"]


def audit_evidence(folder):
    folder = Path(folder)
    guest = folder / "guest-demo-witness.txt"
    if not guest.is_file():
        raise ValueError("no actual NeXium guest-created demo witness found")
    for required in ("emulator-stdout.txt", "vulkan.txt"):
        if not (folder / required).is_file():
            raise ValueError("required emulator evidence missing: "+required)
    audit_release_evidence(folder)
    count = audit_lines(guest.read_bytes())
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True, type=Path)
    ap.add_argument("--require-guest", action="store_true")
    args = ap.parse_args()
    result = args.evidence / "result.txt"
    try:
        count = audit_evidence(args.evidence)
    except (ValueError, OSError, UnicodeError) as exc:
        result.write_text(f"INCONCLUSIVE: {exc}\n")
        if args.require_guest:
            ap.exit(1, f"NeXium guest witness not confirmed: {exc}\n")
        return
    result.write_text(
        f"VPD_NEXIUM_GUEST_DEMO_WITNESS_PASS cycles={count} "
        f"frames_per_cycle=200 total_frames={200*count} "
        "shots_per_cycle=11 hits_per_cycle=3 "
        f"fnv={EXPECTED_FNV} state_match=yes "
        "guest_sd_witness=yes original_game_proven=no "
        "physical_video_scanout_proven=no\n"
    )
    print(result.read_text().strip())


if __name__ == "__main__":
    main()
