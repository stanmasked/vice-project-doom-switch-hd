#!/usr/bin/env python3
"""Aggregate-only audit of owner-local RAM $25/$26 indirect-access traces.

The input is a private CSV/TSV event stream. The aggregate report never
prints raw CPU addresses, RAM bytes, effective addresses, or source identities.
An optional observed-site list writes PC/opcode/operand triples only to the
explicitly chosen private output path; do not commit that file.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

MAX_INPUT_BYTES = 256 * 1024 * 1024
FIRST_FRAME_DEFAULT = 600
LAST_FRAME_DEFAULT = 920
INDIRECT_INDEXED = {
    0x11: "ORA", 0x31: "AND", 0x51: "EOR", 0x71: "ADC",
    0xB1: "LDA", 0xD1: "CMP", 0xF1: "SBC",
}
TARGET_WRITES = {0x25, 0x26, 0x0B, 0x0C, 0x0D}
TWO_BYTE_WRITE_OPS = {
    0x06, 0x16, 0x26, 0x36, 0x46, 0x56, 0x66, 0x76,
    0x84, 0x85, 0x86, 0x94, 0x95, 0x96,
    0xC6, 0xD6, 0xE6, 0xF6,
}
THREE_BYTE_WRITE_OPS = {
    0x0E, 0x1E, 0x2E, 0x3E, 0x4E, 0x5E, 0x6E, 0x7E,
    0x8C, 0x8D, 0x8E, 0xCE, 0xDE, 0xEE, 0xFE,
}

ALIASES = {
    "frame": ("frame", "sourceframe", "movieframe", "frameid"),
    "cycle": ("cycle", "cpucycle", "absolutecycle", "cycles"),
    "pc": ("instructionpc", "executionpc", "pcbefore", "pcat", "pc"),
    "pc_after": ("pcafter", "postpc", "pcafterinstruction"),
    "opcode": ("opcode", "op", "instructionopcode"),
    "operand": ("operand", "operandbyte", "zpoperand", "instructionoperand"),
    "event": ("event", "kind", "type", "action"),
    "address": ("ramaddress", "writeaddress", "writtenaddress", "address"),
    "value": ("newvalue", "writtenvalue", "bytevalue", "value"),
    "old_value": ("oldvalue", "previousvalue", "old"),
    "pointer_low": ("pointerlow", "ptrlow", "ptr25", "ram25", "lowbyte", "low25"),
    "pointer_high": ("pointerhigh", "ptrhigh", "ptr26", "ram26", "highbyte", "high26"),
    "y": ("yregister", "registery", "regy", "y"),
    "effective_address": ("effectiveaddress", "effectiveaddr", "effective", "ea", "targetaddress"),
    "bank_context": ("bankcontext", "prgbankcontext", "mappedbankcontext", "bankcontextid"),
    "sequence": ("sequence", "seq", "ordinal", "eventsequence"),
}


def _normal_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _read_rows(path: Path) -> tuple[list[dict[str, str]], dict[str, str]]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("trace file missing, linked, or oversized")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        first = stream.readline()
        if not first:
            raise ValueError("trace file is empty")
        delimiter = "\t" if "\t" in first else "," if "," in first else None
        if delimiter is None:
            raise ValueError("trace must be CSV or TSV")
        stream.seek(0)
        reader = csv.DictReader(stream, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError("trace header is missing")
        normalized = [_normal_header(x) for x in reader.fieldnames]
        if len(normalized) != len(set(normalized)):
            raise ValueError("trace contains duplicate headers")
        rows = list(reader)
        if not rows or any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError("trace contains no rows or truncated rows")
        header_map = dict(zip(normalized, reader.fieldnames))
        return rows, header_map


def _field(row: dict[str, str], header_map: dict[str, str], name: str) -> str | None:
    for alias in ALIASES[name]:
        original = header_map.get(alias)
        if original is not None and row.get(original, "").strip() != "":
            return row[original].strip()
    return None


def _number(value: str | None, name: str, *, hexadecimal: bool = False, optional: bool = False) -> int | None:
    if value is None or value == "":
        if optional:
            return None
        raise ValueError(f"missing {name}")
    try:
        if value.lower().startswith("0x"):
            return int(value, 16)
        return int(value, 16 if hexadecimal else 10)
    except ValueError as exc:
        raise ValueError(f"invalid {name}") from exc


def _event_kind(row: dict[str, str], header_map: dict[str, str], opcode: int | None, operand: int | None) -> str | None:
    if opcode in INDIRECT_INDEXED and operand in (0x25, 0xAA):
        return "indirect25" if operand == 0x25 else "indirectAA"
    event = (_field(row, header_map, "event") or "").lower()
    if "write" not in event and "store" not in event and "ram" not in event:
        return None
    address_text = _field(row, header_map, "address")
    if address_text is None:
        match = re.search(r"(?:write|store|ram)[^0-9a-f]*([0-9a-f]{2,4})", event)
        if match:
            address_text = match.group(1)
    address = _number(address_text, "RAM address", hexadecimal=True, optional=True)
    if address in TARGET_WRITES:
        return f"write{address:04X}"
    return None


def _parse_event(row: dict[str, str], header_map: dict[str, str], ordinal: int, first: int, last: int) -> dict | None:
    frame = _number(_field(row, header_map, "frame"), "frame")
    cycle = _number(_field(row, header_map, "cycle"), "cycle")
    if frame is None or cycle is None or not first <= frame <= last or cycle < 0:
        raise ValueError("event frame/cycle outside the requested capture window")
    pc = _number(_field(row, header_map, "pc"), "PC", hexadecimal=True, optional=True)
    opcode = _number(_field(row, header_map, "opcode"), "opcode", hexadecimal=True, optional=True)
    operand = _number(_field(row, header_map, "operand"), "operand", hexadecimal=True, optional=True)
    if pc is not None and not 0 <= pc <= 0xFFFF:
        raise ValueError("PC is outside the 6502 address space")
    if opcode is not None and not 0 <= opcode <= 0xFF:
        raise ValueError("opcode is not a byte")
    if operand is not None and not 0 <= operand <= 0xFF:
        raise ValueError("operand is not a byte")
    kind = _event_kind(row, header_map, opcode, operand)
    if kind is None:
        # Some trace formats omit an explicit event name for RAM write rows.
        address_text = _field(row, header_map, "address")
        value_text = _field(row, header_map, "value")
        if address_text is not None and value_text is not None:
            address = _number(address_text, "RAM address", hexadecimal=True)
            if address in TARGET_WRITES:
                kind = f"write{address:04X}"
    if kind is None:
        return None
    if pc is None:
        pc_after_text = _field(row, header_map, "pc_after")
        if pc_after_text is not None:
            pc_after = _number(pc_after_text, "post-instruction PC", hexadecimal=True)
            if kind.startswith("indirect"):
                pc = (pc_after - 2) & 0xFFFF
            elif opcode in TWO_BYTE_WRITE_OPS:
                pc = (pc_after - 2) & 0xFFFF
            elif opcode in THREE_BYTE_WRITE_OPS:
                pc = (pc_after - 3) & 0xFFFF
    event = {"frame": frame, "cycle": cycle, "pc": pc, "opcode": opcode,
             "operand": operand, "kind": kind, "ordinal": ordinal}
    bank = _field(row, header_map, "bank_context")
    event["bank_context"] = bank if bank else None
    sequence = _number(_field(row, header_map, "sequence"), "sequence", optional=True)
    event["sequence"] = sequence if sequence is not None else ordinal
    if kind.startswith("write"):
        address = int(kind[5:], 16)
        value = _number(_field(row, header_map, "value"), "write value", hexadecimal=True)
        old = _number(_field(row, header_map, "old_value"), "old write value", hexadecimal=True, optional=True)
        if value is None or not 0 <= value <= 0xFF or (old is not None and not 0 <= old <= 0xFF):
            raise ValueError("RAM write value is not a byte")
        event.update(address=address, value=value, old_value=old)
    else:
        if opcode not in INDIRECT_INDEXED or operand not in (0x25, 0xAA):
            raise ValueError("unsupported indirect-indexed opcode")
        low = _number(_field(row, header_map, "pointer_low"), "pointer low byte", hexadecimal=True)
        high = _number(_field(row, header_map, "pointer_high"), "pointer high byte", hexadecimal=True)
        y = _number(_field(row, header_map, "y"), "Y register", hexadecimal=True)
        effective = _number(_field(row, header_map, "effective_address"), "effective address", hexadecimal=True)
        if any(v is None or not 0 <= v <= 0xFF for v in (low, high, y)):
            raise ValueError("pointer/Y field is not a byte")
        if effective is None or not 0 <= effective <= 0xFFFF:
            raise ValueError("effective address is outside the 6502 address space")
        if (((high << 8) | low) + y) & 0xFFFF != effective:
            raise ValueError("effective address disagrees with pointer bytes plus Y")
        event.update(pointer_low=low, pointer_high=high, y=y, effective_address=effective)
    return event


def analyze(path: Path, first_frame: int = FIRST_FRAME_DEFAULT, last_frame: int = LAST_FRAME_DEFAULT) -> dict:
    if not (0 <= first_frame <= last_frame <= 100_000_000):
        raise ValueError("invalid frame window")
    rows, header_map = _read_rows(path)
    events = []
    previous_order = None
    for ordinal, row in enumerate(rows):
        event = _parse_event(row, header_map, ordinal, first_frame, last_frame)
        if event is not None:
            order = (event["frame"], event["cycle"], event["sequence"], event["ordinal"])
            if previous_order is not None and order < previous_order:
                raise ValueError("trace events are not in chronological order")
            previous_order = order
            events.append(event)
    if not events:
        raise ValueError("no relevant RAM $25/$26, ($25)/Y, ($AA)/Y, or RAM $0B-$0D events found")

    pointer_writes = Counter()
    write_sites = Counter()
    access_sites = Counter()
    access_frames = defaultdict(set)
    pointer_updates = Counter()
    pointer_value_changes = Counter()
    pending = Counter()
    previous_pointer = None
    ea_by_frame = {"indirect25": defaultdict(set), "indirectAA": defaultdict(set)}
    accesses_by_frame = {"indirect25": Counter(), "indirectAA": Counter()}
    ram_writes = Counter()
    ram_write_frames = defaultdict(set)
    frames_with_25 = set()
    frames_with_aa = set()
    latest_frame = -1
    latest_cycle = -1
    for event in events:
        frame, cycle = event["frame"], event["cycle"]
        if frame < latest_frame or (frame == latest_frame and cycle < latest_cycle):
            raise ValueError("events are not in chronological order")
        latest_frame, latest_cycle = frame, cycle
        kind = event["kind"]
        if kind.startswith("write"):
            address = event["address"]
            ram_writes[address] += 1
            ram_write_frames[address].add(frame)
            if address in (0x25, 0x26):
                pointer_writes[address] += 1
                pending[address] += 1
                key = (event["pc"], event["opcode"], event["operand"], address, event["bank_context"])
                write_sites[key] += 1
        else:
            key = (event["pc"], event["opcode"], event["operand"], event["bank_context"])
            access_sites[key] += 1
            access_frames[key].add(frame)
            accesses_by_frame[kind][frame] += 1
            ea_by_frame[kind][frame].add(event["effective_address"])
            if kind == "indirect25":
                frames_with_25.add(frame)
                low_written = pending[0x25] > 0
                high_written = pending[0x26] > 0
                update_class = "both_bytes_written" if low_written and high_written else (
                    "low_only_written" if low_written else "high_only_written" if high_written else "no_pointer_write")
                pointer_updates[update_class] += 1
                pair = (event["pointer_low"], event["pointer_high"])
                if previous_pointer is not None:
                    low_changed = pair[0] != previous_pointer[0]
                    high_changed = pair[1] != previous_pointer[1]
                    value_class = "both_bytes_changed" if low_changed and high_changed else (
                        "low_only_changed" if low_changed else "high_only_changed" if high_changed else "pointer_unchanged")
                    pointer_value_changes[value_class] += 1
                previous_pointer = pair
                pending.clear()
            else:
                frames_with_aa.add(frame)
    ram0b0d_frames = set().union(*(ram_write_frames[a] for a in (0x0B, 0x0C, 0x0D)))
    frames_with_25_and_ram = frames_with_25 & ram0b0d_frames
    frames_with_aa_and_ram = frames_with_aa & ram0b0d_frames
    both_decoder_frames = set(ea_by_frame["indirect25"]) & set(ea_by_frame["indirectAA"])
    equal_ea_pairs = sum(len(ea_by_frame["indirect25"][frame] & ea_by_frame["indirectAA"][frame])
                         for frame in both_decoder_frames)

    bank_contexts = sorted({key[3] for key in access_sites if key[3] is not None})
    bank_ids = {value: f"M{index + 1:03d}" for index, value in enumerate(bank_contexts)}
    sorted_sites = sorted(access_sites.items(), key=lambda item: (-item[1], str(item[0])))
    site_ids = {key: f"S{index + 1:03d}" for index, (key, _) in enumerate(sorted_sites)}
    top_access_sites = []
    for key, count in sorted_sites[:32]:
        _, opcode, operand, bank = key
        mnemonic = INDIRECT_INDEXED.get(opcode, "IND")
        pointer_name = "$25" if operand == 0x25 else "$AA"
        top_access_sites.append({
            "site_id": site_ids[key],
            "instruction": f"{mnemonic} ({pointer_name}),Y",
            "bank_context_id": bank_ids.get(bank, "unknown"),
            "accesses": count,
            "frames": len(access_frames[key]),
        })
    sorted_write_sites = sorted(write_sites.items(), key=lambda item: (-item[1], str(item[0])))
    top_write_sites = []
    for index, (key, count) in enumerate(sorted_write_sites[:24], 1):
        _, opcode, _, address, bank = key
        top_write_sites.append({
            "site_id": f"W{index:03d}",
            "target": "$25" if address == 0x25 else "$26",
            "bank_context_id": bank_ids.get(bank, "unknown"),
            "writes": count,
            "instruction_opcode_known": opcode is not None,
        })

    frames_observed = sorted({e["frame"] for e in events})
    return {
        "schema": "vpd_private_ram2526_stage326_aggregate_v1",
        "frame_window": [first_frame, last_frame],
        "frames_with_relevant_events": len(frames_observed),
        "relevant_event_rows": len(events),
        "pointer_write_counts": {"$25": pointer_writes[0x25], "$26": pointer_writes[0x26]},
        "indirect_access_counts": {
            "$25": sum(accesses_by_frame["indirect25"].values()),
            "$AA": sum(accesses_by_frame["indirectAA"].values()),
            "lda": sum(count for (_, op, operand, _), count in access_sites.items() if op == 0xB1),
            "adc": sum(count for (_, op, operand, _), count in access_sites.items() if op == 0x71),
            "$25_by_opcode": {
                "lda": sum(count for (_, op, operand, _), count in access_sites.items() if operand == 0x25 and op == 0xB1),
                "adc": sum(count for (_, op, operand, _), count in access_sites.items() if operand == 0x25 and op == 0x71),
                "other": sum(count for (_, op, operand, _), count in access_sites.items() if operand == 0x25 and op not in (0xB1, 0x71)),
            },
            "$AA_by_opcode": {
                "lda": sum(count for (_, op, operand, _), count in access_sites.items() if operand == 0xAA and op == 0xB1),
                "adc": sum(count for (_, op, operand, _), count in access_sites.items() if operand == 0xAA and op == 0x71),
                "other": sum(count for (_, op, operand, _), count in access_sites.items() if operand == 0xAA and op not in (0xB1, 0x71)),
            },
            "frames_with_access": {"$25": len(frames_with_25), "$AA": len(frames_with_aa)},
        },
        "pointer_update_classes_since_previous_$25_access": dict(sorted(pointer_updates.items())),
        "pointer_value_change_classes_between_$25_accesses": dict(sorted(pointer_value_changes.items())),
        "access_site_count": len(access_sites),
        "bank_context_available": bool(bank_contexts) and all(key[3] is not None for key in access_sites),
        "distinct_bank_contexts": len(bank_contexts),
        "top_access_sites": top_access_sites,
        "top_pointer_write_sites": top_write_sites,
        "decoder_comparison": {
            "frames_with_both_$25_and_$AA_accesses": len(both_decoder_frames),
            "same_effective_address_pairs_within_frame": equal_ea_pairs,
            "causal_or_semantic_relation_proven": False,
        },
        "ram_0b_0c_0d_write_counts": {
            "$0B": ram_writes[0x0B], "$0C": ram_writes[0x0C], "$0D": ram_writes[0x0D],
        },
        "frames_with_$25_access_and_any_$0b_0c_0d_write": len(frames_with_25_and_ram),
        "frames_with_$AA_access_and_any_$0b_0c_0d_write": len(frames_with_aa_and_ram),
        "semantics_confirmed": False,
        "raw_values_disclosed": False,
    }


def verify_stage325_baseline(result: dict) -> None:
    """Reject a trace that does not match the already reported Stage 325 counts."""
    expected = {
        "pointer_write_counts": {"$25": 22146, "$26": 31474},
        "indirect_access_counts": {
            "$25": 20524,
            "$25_by_opcode": {"lda": 20508, "adc": 16, "other": 0},
            "frames_with_access": {"$25": 319},
        },
    }
    for section, wanted in expected.items():
        actual = result.get(section, {})
        for key, value in wanted.items():
            if isinstance(value, dict):
                nested = actual.get(key, {})
                if any(nested.get(subkey) != subvalue for subkey, subvalue in value.items()):
                    raise ValueError("trace does not match the Stage 325 aggregate baseline")
            elif actual.get(key) != value:
                raise ValueError("trace does not match the Stage 325 aggregate baseline")


def extract_sites(path: Path, output_path: Path,
                  first_frame: int = FIRST_FRAME_DEFAULT,
                  last_frame: int = LAST_FRAME_DEFAULT) -> int:
    """Write the exact observed indirect-instruction sites to a private TSV."""
    if output_path.exists() or output_path.is_symlink():
        raise ValueError("site-list output already exists")
    rows, header_map = _read_rows(path)
    sites = set()
    for ordinal, row in enumerate(rows):
        event = _parse_event(row, header_map, ordinal, first_frame, last_frame)
        if event and event["kind"].startswith("indirect"):
            if event["pc"] is None or event["opcode"] is None or event["operand"] is None:
                raise ValueError("indirect event lacks a verified instruction site")
            sites.add((event["pc"], event["opcode"], event["operand"]))
    if not sites or len(sites) > 4096:
        raise ValueError("indirect site count is empty or exceeds the safety limit")
    with output_path.open("x", encoding="ascii", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(("pc", "opcode", "operand"))
        for pc, opcode, operand in sorted(sites):
            writer.writerow((f"{pc:04X}", f"{opcode:02X}", f"{operand:02X}"))
    return len(sites)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--first-frame", type=int, default=FIRST_FRAME_DEFAULT)
    parser.add_argument("--last-frame", type=int, default=LAST_FRAME_DEFAULT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sites-output", type=Path,
                        help="write the observed PC/opcode/operand site list privately")
    parser.add_argument("--require-stage325-baseline", action="store_true",
                        help="require the known Stage 325 aggregate counts before continuing")
    args = parser.parse_args()
    try:
        result = analyze(args.input, args.first_frame, args.last_frame)
        if args.require_stage325_baseline:
            verify_stage325_baseline(result)
        report = json.dumps(result, sort_keys=True, indent=2) + "\n"
        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise ValueError("output already exists")
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(report)
        site_count = extract_sites(args.input, args.sites_output, args.first_frame, args.last_frame) if args.sites_output else 0
    except (OSError, ValueError, UnicodeError):
        parser.exit(1, "VPD_PRIVATE_RAM2526_STAGE326_INCONCLUSIVE: trace validation failed; raw evidence remains local\n")
    print(
        "VPD_PRIVATE_RAM2526_STAGE326_AUDIT_PASS"
        f" rows={result['relevant_event_rows']}"
        f" sites={result['access_site_count']}"
        f" lda25={result['indirect_access_counts']['$25_by_opcode']['lda']}"
        f" adc25={result['indirect_access_counts']['$25_by_opcode']['adc']}"
        f" ram25_writes={result['pointer_write_counts']['$25']}"
        f" ram26_writes={result['pointer_write_counts']['$26']}"
        f" bank_context={'yes' if result['bank_context_available'] else 'no'}"
        f" sites_exported={site_count}"
        " raw_values_disclosed=no semantics_confirmed=no"
    )


if __name__ == "__main__":
    main()
