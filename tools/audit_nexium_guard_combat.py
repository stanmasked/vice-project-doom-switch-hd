#!/usr/bin/env python3
"""Fail-closed audit of a *scripted*, in-guest ROM-free guard combat probe.

This is native NRO gameplay-core execution, not observed user-driven combat
or evidence of recovered Vice: Project Doom enemy AI.
"""
import argparse
from pathlib import Path
import re

PREFIX = "VPD_ROMFREE_GUARD_COMBAT_V1"
NAMES = ("alert", "attack", "hit1", "hit2", "defeat")
FIELDS = ("seq", "event", "scenario", "frame", "guard_x", "guard_hp",
          "player_hp", "hits", "attacks", "cooldown", "alerted",
          "source", "original_game_proven")
LIMIT = 1800
GUARD_X_MIN = 14 * 16 * 256
GUARD_X_MAX = 20 * 16 * 256


def verify(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > LIMIT:
        raise ValueError("guest combat proof missing or oversized")
    text = raw.decode("ascii")
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise ValueError("malformed combat guest line endings")
    rows = text.splitlines()
    if len(rows) != 5:
        raise ValueError("five native combat events required")
    frames = []
    for idx, (event, line) in enumerate(zip(NAMES, rows), 1):
        cells = line.split(" ")
        if len(cells) != 1 + len(FIELDS) or cells[0] != PREFIX:
            raise ValueError("wrong native combat row length or marker")
        pairs = [cell.split("=", 1) for cell in cells[1:]]
        if any(len(pair) != 2 for pair in pairs):
            raise ValueError("invalid combat key/value separator")
        if tuple(pair[0] for pair in pairs) != FIELDS:
            raise ValueError("combat schema order differs from game core")
        data = dict(pairs)
        expected_scenario = "approach" if idx <= 2 else "shoot"
        if (data["seq"] != str(idx) or data["event"] != event or
            data["scenario"] != expected_scenario or
            data["source"] != "guest_script" or
            data["original_game_proven"] != "no"):
            raise ValueError("incorrect event or source provenance")
        for key in ("frame", "guard_x", "guard_hp", "player_hp",
                    "hits", "attacks", "cooldown", "alerted"):
            if not re.fullmatch(r"0|[1-9][0-9]*", data[key]):
                raise ValueError("noncanonical native combat numeric value")
        frame = int(data["frame"])
        x = int(data["guard_x"])
        health = int(data["guard_hp"])
        player = int(data["player_hp"])
        hits = int(data["hits"])
        attacks = int(data["attacks"])
        cooldown = int(data["cooldown"])
        alerted = int(data["alerted"])
        if (not 1 <= frame <= (210 if idx <= 2 else 150) or
            not GUARD_X_MIN <= x <= GUARD_X_MAX or
            x % 256 != 0):
            raise ValueError("impossible combat world coordinate or frame")
        if idx == 1 and (health, player, hits, attacks, cooldown, alerted) != (
            3, 5, 0, 0, 0, 1
        ):
            raise ValueError("detection lacks source guard transition")
        if idx == 2 and (health, player, hits, attacks, cooldown, alerted) != (
            3, 4, 0, 1, 32, 1
        ):
            raise ValueError("contact attack lacks real damage and cooldown")
        if idx >= 3 and (health, player, hits, attacks, cooldown, alerted) != (
            5 - idx, 5, idx - 2, 0, 0, 0
        ):
            raise ValueError("swept bullet damage/destroy state inconsistent")
        frames.append(frame)
    if frames[1] <= frames[0] or not (
        frames[2] < frames[3] < frames[4]
    ):
        raise ValueError("native combat events out of scenario order")
    return {"alert_frame": frames[0], "attack_frame": frames[1],
            "hit_frames": frames[2:]}


def audit(folder):
    root = Path(folder)
    path = root / "guest-guard-combat-witness.txt"
    if not path.is_file():
        raise ValueError("NeXium guest did not create scripted combat proof")
    found = verify(path.read_bytes())
    prerequisites = (
        ("manual-result.txt", "VPD_NEXIUM_GUEST_MANUAL_EXIT_PASS "),
        ("dash-result.txt", "VPD_NEXIUM_GUEST_DASH_PASS "),
        ("guard-result.txt", "VPD_NEXIUM_GUARD_PATROL_PASS "),
        ("native-exit-result.txt", "VPD_NEXIUM_NATIVE_GUEST_EXIT_PASS "),
    )
    for name, marker in prerequisites:
        p = root / name
        if not p.is_file() or not p.read_text(encoding="ascii").startswith(marker):
            raise ValueError("independent NeXium evidence missing: " + name)
    result = (
        "VPD_NEXIUM_GUARD_COMBAT_SCRIPT_PASS "
        f"alert_frame={found['alert_frame']} "
        f"attack_frame={found['attack_frame']} "
        f"hit_frames={','.join(map(str, found['hit_frames']))} "
        "contact_damage=1 attack_cooldown=32 guard_hits=3 "
        "guard_defeated=yes execution=guest_script "
        "manual_combat_input_proven=no original_game_proven=no\n"
    )
    (root / "guard-combat-result.txt").write_text(result, encoding="ascii")
    print(result, end="")
    return found


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError, UnicodeError, ValueError) as err:
        args.evidence.mkdir(parents=True, exist_ok=True)
        (args.evidence / "guard-combat-result.txt").write_text(
            "INCONCLUSIVE: " + str(err) + "\n", encoding="ascii"
        )
        parser.exit(1, "Guest-scripted combat unverified: " + str(err) + "\n")
