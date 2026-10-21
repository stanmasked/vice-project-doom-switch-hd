#!/usr/bin/env python3
"""Audit exact fully-black scene gaps in PRIVATE FCEUX captures.

Inputs may contain copyrighted game pixels: keep them outside Git and CI.
This analyzer reports only frame numbers, booleans, and consistency counts.
A blackout is not proof of a named game stage or gameplay fidelity.
"""
import argparse
import json
from pathlib import Path

from audit_private_fceux_storyboard import audit, parse_meta, P6_HEADER, WIDTH, HEIGHT

RGB_BYTES = WIDTH * HEIGHT * 3


def _frames(directory):
    directory = Path(directory)
    return sorted(
        int(p.name[6:-9])
        for p in directory.glob("frame_*.meta.txt")
    )


def _rgb(directory, frame):
    path = Path(directory) / ("frame_%06d.ppm" % frame)
    raw = path.read_bytes()
    if len(raw) != len(P6_HEADER) + RGB_BYTES or not raw.startswith(P6_HEADER):
        raise ValueError("invalid private P6 capture")
    return raw[len(P6_HEADER):]


def _compare(reference_dir, other_dir):
    other = audit(other_dir, require_complete=True)
    current = set(_frames(reference_dir))
    common = sorted(current & set(_frames(other_dir)))
    if not common:
        raise ValueError("no common frames between private captures")
    original_id = parse_meta(Path(reference_dir) /
                             ("frame_%06d.meta.txt" % common[0]))["rom_md5"].lower()
    comparison_id = parse_meta(Path(other_dir) /
                               ("frame_%06d.meta.txt" % common[0]))["rom_md5"].lower()
    if original_id != comparison_id:
        raise ValueError("private captures disagree on ROM identity")
    for frame in common:
        name = "frame_%06d" % frame
        for ext in (".ppm", ".pal.bin"):
            a = (Path(reference_dir) / (name + ext)).read_bytes()
            b = (Path(other_dir) / (name + ext)).read_bytes()
            if a != b:
                raise ValueError("private captures are not byte-identical at overlapping frame")
    return {"overlapping_frames_verified": len(common),
            "rgb_palette_pairs_identical": True,
            "comparison_storyboard_complete": other["complete_window_verified"]}


def audit_transition(directory, *, compare=None, minimum_black_frames=1):
    if type(minimum_black_frames) is not int or not 1 <= minimum_black_frames <= 64:
        raise ValueError("invalid minimum black-frame length")
    report = audit(directory, require_complete=True)
    if report["capture_interval"] != 1:
        raise ValueError("exact transition requires one image per movie frame")
    frames = _frames(directory)
    if len(frames) < 3 or any(b != a + 1 for a, b in zip(frames, frames[1:])):
        raise ValueError("exact transition requires consecutive frame captures")
    black = [not any(_rgb(directory, f)) for f in frames]
    transitions = []
    i = 0
    while i < len(frames):
        if not black[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(frames) and black[j + 1]:
            j += 1
        if i > 0 and j < len(frames) - 1 and j - i + 1 >= minimum_black_frames:
            transitions.append((frames[i - 1], frames[i], frames[j], frames[j + 1]))
        i = j + 1
    if len(transitions) != 1:
        raise ValueError("expected one unambiguous, fully bracketed black-screen interval")
    prior, first_black, last_black, after = transitions[0]
    result = {
        "classification": "private FCEUX fully-black screen interval only",
        "first_capture_frame": frames[0],
        "last_capture_frame": frames[-1],
        "sample_count": len(frames),
        "last_visible_frame_before_black": prior,
        "first_black_frame": first_black,
        "last_black_frame": last_black,
        "first_visible_frame_after_black": after,
        "black_frame_count": last_black - first_black + 1,
        "storyboard_complete": bool(report["complete_window_verified"]),
        "visual_black_interval_verified": True,
        "named_stage_identity_proven_by_this_analyzer": False,
        "full_movie_replay_proven_by_this_analyzer": False
    }
    if compare is not None:
        result.update(_compare(directory, compare))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_capture", type=Path)
    parser.add_argument("--compare-private-capture", type=Path)
    parser.add_argument("--min-black-frames", type=int, default=1)
    args = parser.parse_args()
    try:
        report = audit_transition(
            args.private_capture,
            compare=args.compare_private_capture,
            minimum_black_frames=args.min_black_frames)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(1, "PRIVATE_FCEUX_TRANSITION_INCONCLUSIVE: " + str(exc) + "\n")
    print("PRIVATE_FCEUX_TRANSITION_BLACK_INTERVAL_PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
