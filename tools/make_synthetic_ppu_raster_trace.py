#!/usr/bin/env python3
"""Create synthetic, ROM-free Stage96 NTSC raster contract data only."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_native_ppu_raster_contract import FORMAT


def synthetic_capture(folder, *, frames=2, first_frame=0):
    if (not isinstance(frames, int) or not 1 <= frames <= 1000
            or not isinstance(first_frame, int) or not 0 <= first_frame <= 500000-frames):
        raise ValueError("Invalid synthetic frame span")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rows = ["frame\tscanline\tdot\tkind"]
    for frame in range(first_frame, first_frame+frames):
        for scan, dot, kind in (
            (0, 0, "frame_anchor"), (10, 12, "pixel_fetch_sample"),
            (60, 48, "chr_context"), (130, 12, "scroll_context"),
            (241, 1, "vblank_enter"), (261, 1, "vblank_exit"),
        ):
            rows.append(f"{frame}\t{scan}\t{dot}\t{kind}")
    events = ("\n".join(rows) + "\n").encode("ascii")
    manifest = {
        "format": FORMAT,
        "source_class": "synthetic_fixture",
        "engine_id": "fceux_candidate",
        "engine_revision": "0"*40,
        "timing_model": "ntsc_262_lines_341_dots",
        "native_hook_phase": "before_ppu_tick",
        "first_frame": first_frame,
        "frames_captured": frames,
        "events_recorded": len(rows)-1,
        "events_sha256": hashlib.sha256(events).hexdigest(),
        "dropped_events": 0,
        "counter_discontinuities": 0,
        "capture_complete": True,
    }
    (folder / "ppu_raster_events.tsv").write_bytes(events)
    target = folder / "ppu_raster_manifest.json"
    target.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf8")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--frames", type=int, default=2)
    parser.add_argument("--first-frame", type=int, default=0)
    args = parser.parse_args()
    print(synthetic_capture(args.directory, frames=args.frames,
                            first_frame=args.first_frame))


if __name__ == "__main__":
    main()
