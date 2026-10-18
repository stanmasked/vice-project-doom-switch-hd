#!/usr/bin/env python3
"""Audit real X11 capture produced by NeXium (not guest game fidelity).

Rejects missing, blank, truncated, unchanged or wholly synthetic captures.
Only the presence of a dynamic nonblack host framebuffer can be asserted;
this does not prove frame pacing, console hardware, or original game assets.
"""
import argparse
import hashlib
from pathlib import Path


def parse_ppm(data):
    if not isinstance(data, bytes) or len(data) > 15_000_000:
        raise ValueError("bad PPM type or size")
    cursor = 0
    fields = []
    while len(fields) < 4:
        while cursor < len(data) and data[cursor] in b" \r\n\t":
            cursor += 1
        if cursor < len(data) and data[cursor] == 35:
            while cursor < len(data) and data[cursor] != 10:
                cursor += 1
            continue
        start = cursor
        while cursor < len(data) and data[cursor] not in b" \r\n\t":
            cursor += 1
        if start == cursor:
            raise ValueError("missing PPM header token")
        fields.append(data[start:cursor])
    magic, raw_width, raw_height, raw_max = fields
    if magic != b"P6" or not all(x.isdigit() for x in fields[1:]):
        raise ValueError("not binary 8-bit PPM")
    width, height, maximum = map(int, fields[1:])
    if not (width == 1280 and height == 720 and maximum == 255):
        raise ValueError("unexpected Xvfb image shape/depth")
    if cursor >= len(data) or data[cursor] not in b" \r\n\t":
        raise ValueError("no PPM pixel delimiter")
    # Exactly one required whitespace byte; pixel data itself may start
    # with a whitespace-value byte and must not be stripped.
    rgb = data[cursor + 1:]
    if len(rgb) != width * height * 3:
        raise ValueError("truncated or extended framebuffer pixels")
    return rgb


def evaluate(before, after):
    first = parse_ppm(before)
    second = parse_ppm(after)
    sampled = list(range(0, len(first) // 3, 97))
    colored = 0
    varied = 0
    changed = 0
    palette = set()
    for index in sampled:
        j = 3 * index
        a = tuple(first[j:j+3])
        b = tuple(second[j:j+3])
        palette.add(a)
        if max(a) >= 18:
            varied += 1
        if max(a) - min(a) >= 18:
            colored += 1
        if a != b:
            changed += 1
    if len(palette) < 24 or varied < len(sampled) // 20:
        raise ValueError("X11 host image looks blank or lacks scene detail")
    if colored < len(sampled) // 100:
        raise ValueError("no substantial colored scene pixels detected")
    if changed < 10:
        raise ValueError("X11 presentation samples unchanged (no motion proof)")
    return {
        "samples": len(sampled),
        "colored": colored,
        "nonblack": varied,
        "changed": changed,
        "before_sha256": hashlib.sha256(before).hexdigest(),
        "after_sha256": hashlib.sha256(after).hexdigest()
    }


def audit_evidence(folder):
    folder = Path(folder)
    meta = folder / "visual-probe.txt"
    if not meta.is_file() or "visual_probe=finished" not in meta.read_text():
        raise ValueError("headless capture did not finish")
    first = folder / "screen-before.ppm"
    second = folder / "screen-after.ppm"
    for label in ("screen-before.png", "screen-after.png"):
        if not (folder / label).is_file():
            raise ValueError("PNG capture missing: " + label)
    return evaluate(first.read_bytes(), second.read_bytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", type=Path, required=True)
    args = ap.parse_args()
    try:
        outcome = audit_evidence(args.evidence)
    except (OSError, ValueError, UnicodeError) as exc:
        (args.evidence / "visual-result.txt").write_text(f"INCONCLUSIVE: {exc}\n")
        ap.exit(1, f"Visual capture inconclusive: {exc}\n")
    label = ("VPD_NEXIUM_VISUAL_FRAME_PASS "
             f"nonblack_sampled={outcome['nonblack']} "
             f"colored_sampled={outcome['colored']} "
             f"changed_sampled={outcome['changed']} "
             f"samples={outcome['samples']} "
             f"before_sha256={outcome['before_sha256']} "
             f"after_sha256={outcome['after_sha256']} "
             "native_x11_image=yes actual_fps_proven=no "
             "original_game_proven=no\n")
    (args.evidence / "visual-result.txt").write_text(label)
    print(label, end="")


if __name__ == "__main__":
    main()
