#!/usr/bin/env python3
"""Stage96: validate *candidate* NTSC native PPU raster trace structure.

Passing integrity and shape checks does NOT prove emulator provenance, ROM
identity, physical VBlank, CHR visibility, or any level geometry.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

FORMAT = "vpd_native_ppu_raster_contract_v1"
HEADER = b"frame\tscanline\tdot\tkind\n"
KINDS = ("frame_anchor", "pixel_fetch_sample", "chr_context",
         "scroll_context", "ppu_write", "vblank_enter", "vblank_exit")
MANIFEST_KEYS = {
    "format", "source_class", "engine_id", "engine_revision", "timing_model",
    "native_hook_phase", "first_frame", "frames_captured", "events_recorded",
    "events_sha256", "dropped_events", "counter_discontinuities",
    "capture_complete",
}
DECIMAL = re.compile(r"(0|[1-9][0-9]*)\Z")
MAX_BYTES = 32 * 1024 * 1024
MAX_ROWS = 500000


class RasterContractError(ValueError):
    pass


def unsigned(value, name, *, maximum=MAX_ROWS):
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= maximum:
        raise RasterContractError("Invalid number: " + name)
    return value


def dec(raw, name, maximum=MAX_ROWS):
    if DECIMAL.fullmatch(raw) is None:
        raise RasterContractError("Invalid unsigned decimal: " + name)
    value = int(raw)
    if value > maximum:
        raise RasterContractError("Out of range: " + name)
    return value


def validate_manifest(raw):
    if len(raw) > 8192:
        raise RasterContractError("Oversized manifest")
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise RasterContractError("Malformed manifest JSON") from exc
    if not isinstance(data, dict) or set(data) != MANIFEST_KEYS:
        raise RasterContractError("Unexpected or missing manifest fields")
    if data["format"] != FORMAT:
        raise RasterContractError("Unsupported native raster format")
    if data["source_class"] not in ("synthetic_fixture", "candidate_native_unverified"):
        raise RasterContractError("Invalid candidate provenance")
    if data["engine_id"] != "fceux_candidate":
        raise RasterContractError("Unverified engine must be declared candidate")
    if (not isinstance(data["engine_revision"], str)
            or re.fullmatch("[0-9a-f]{40}", data["engine_revision"]) is None):
        raise RasterContractError("Unspecified pinned engine revision")
    if data["timing_model"] != "ntsc_262_lines_341_dots":
        raise RasterContractError("Unsupported raster timing model")
    if data["native_hook_phase"] not in ("before_ppu_tick", "after_ppu_tick"):
        raise RasterContractError("Unspecified PPU hook phase")
    unsigned(data["first_frame"], "first_frame")
    if unsigned(data["frames_captured"], "frames_captured") == 0:
        raise RasterContractError("Missing captured frames")
    if unsigned(data["events_recorded"], "events_recorded") == 0:
        raise RasterContractError("Missing event rows")
    if (not isinstance(data["events_sha256"], str)
            or re.fullmatch("[0-9a-f]{64}", data["events_sha256"]) is None):
        raise RasterContractError("Invalid event-stream SHA256")
    for key in ("dropped_events", "counter_discontinuities"):
        if unsigned(data[key], key) != 0:
            raise RasterContractError("Incomplete event coverage or clock resets")
    if data["capture_complete"] is not True:
        raise RasterContractError("Unfinished native raster trace")
    return data


def check_rows(blob, manifest):
    if len(blob) > MAX_BYTES or not blob.startswith(HEADER):
        raise RasterContractError("Invalid raster TSV header or length")
    if not blob.endswith(b"\n") or b"\r" in blob or b"\x00" in blob:
        raise RasterContractError("Truncated or invalid raster TSV")
    try:
        lines = blob.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise RasterContractError("Non-ASCII raster data") from exc
    if len(lines)-1 != manifest["events_recorded"] or len(lines)-1 > MAX_ROWS:
        raise RasterContractError("Raster row count disagreement")
    counts = {kind: 0 for kind in KINDS}
    prev = None
    frame = None
    frames = 0
    state = "before_vblank"
    anchor = enter = leave = 0
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) != 4:
            raise RasterContractError("Unexpected TSV columns")
        fr = dec(fields[0], "frame")
        y = dec(fields[1], "scanline", 261)
        x = dec(fields[2], "dot", 340)
        kind = fields[3]
        if kind not in KINDS:
            raise RasterContractError("Unrecognized raster event kind")
        position = (fr, y, x)
        if prev is not None and position < prev:
            raise RasterContractError("Nonmonotonic PPU raster coordinates")
        prev = position
        if fr != frame:
            if frame is not None and (anchor, enter, leave) != (1, 1, 1):
                raise RasterContractError("Incomplete VBlank markers in previous frame")
            if fr != manifest["first_frame"] + frames:
                raise RasterContractError("Nonconsecutive raster frame labels")
            if kind != "frame_anchor" or (y, x) != (0, 0):
                raise RasterContractError("Frame missing position-zero anchor")
            frame = fr
            frames += 1
            anchor = enter = leave = 0
            state = "before_vblank"
        if kind == "frame_anchor":
            anchor += 1
            if (y, x) != (0, 0) or anchor != 1:
                raise RasterContractError("Repeated or misplaced frame anchor")
        elif kind == "vblank_enter":
            enter += 1
            if (y, x) != (241, 1) or enter != 1 or state != "before_vblank":
                raise RasterContractError("Invalid NTSC VBlank start marker")
            state = "within_vblank"
        elif kind == "vblank_exit":
            leave += 1
            if (y, x) != (261, 1) or leave != 1 or state != "within_vblank":
                raise RasterContractError("Invalid NTSC VBlank end marker")
            state = "after_vblank"
        elif kind == "pixel_fetch_sample":
            if not (y <= 239 and 1 <= x <= 256):
                raise RasterContractError("Pixel sample not in visible area")
        counts[kind] += 1
    if (anchor, enter, leave) != (1, 1, 1):
        raise RasterContractError("Incomplete final frame VBlank markers")
    if frames != manifest["frames_captured"]:
        raise RasterContractError("Raster frame count mismatch")
    return counts, frames


def audit_verified(manifest_path, events_path=None):
    path = Path(manifest_path)
    meta = validate_manifest(path.read_text(encoding="utf8"))
    log = Path(events_path) if events_path is not None else path.parent / "ppu_raster_events.tsv"
    if log.stat().st_size > MAX_BYTES:
        raise RasterContractError("Oversized raster event log")
    bytes_ = log.read_bytes()
    if hashlib.sha256(bytes_).hexdigest() != meta["events_sha256"]:
        raise RasterContractError("Raster event stream checksum mismatch")
    counts, frames = check_rows(bytes_, meta)
    return {
        "format": "vpd_checked_native_ppu_raster_shape_v1",
        "event_stream_sha256_verified": True,
        "declared_ntsc_raster_shape_valid": True,
        "source_class_declared": meta["source_class"],
        "frames_accounted_for": frames,
        "events_accounted_for": sum(counts.values()),
        "aggregate_event_types": counts,
        "independent_native_fceux_origin_verified": False,
        "actual_ppu_vblank_observation_verified": False,
        "ppu_dot_hook_placement_verified": False,
        "cpu_to_raster_visibility_verified": False,
        "real_first_level_geometry_verified": False,
        "hd_background_cells_ready": 0,
        "raw_ppu_positions_or_game_data_exported": False,
        "next_gate": "Native FCEUX PPU-step hook, pinned source, synthetic golden comparisons and independent raster evidence",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = json.dumps(audit_verified(args.manifest, args.events), indent=2)+"\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf8")
    print(report, end="")


if __name__ == "__main__":
    main()
