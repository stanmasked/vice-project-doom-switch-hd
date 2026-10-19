#!/usr/bin/env python3
"""Native third-playthrough first-guard defeat: source + X11 host + pixels."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import re

PREFIX="VPD_ROMFREE_THIRD_GUARD_CLEAR_V1"
KEYS=("event","frame","hero_x","hero_hp","guard_hp",
      "previous_guard_hp","guard_hits","previous_guard_hits",
      "guard_attacks","shots","sentry_hp","wave","clear","dash",
      "input_fire","source","original_game_proven")
NUMS=("frame","hero_x","hero_hp","guard_hp","previous_guard_hp",
      "guard_hits","previous_guard_hits","guard_attacks","shots",
      "sentry_hp","wave","clear","dash","input_fire")
P6=re.compile(rb"\AP6\n(?:\#[ -~]{1,200}\n){0,3}1280 720\n255\n")
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "third_fire_source",ROOT/"tools/audit_nexium_third_run_fire.py")
previous=importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)

def verify(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>550:
        raise ValueError("third guard clear guest event absent or oversized")
    string=raw.decode("ascii")
    if (not string.endswith("\n") or string.count("\n")!=1 or
        "\r" in string or "\x00" in string):
        raise ValueError("third guard clear record must be exactly one line")
    cols=string[:-1].split(" ")
    if cols[0]!=PREFIX or len(cols)!=len(KEYS)+1:
        raise ValueError("third guard clear record prefix/shape incorrect")
    pairs=[item.split("=",1) for item in cols[1:]]
    if (any(len(p)!=2 for p in pairs) or
        tuple(p[0] for p in pairs)!=KEYS):
        raise ValueError("guard clear field order or keys incorrect")
    v=dict(pairs)
    if (v["event"]!="guard_clear" or v["source"]!="live_guest" or
        v["original_game_proven"]!="no"):
        raise ValueError("non-live or forged guard defeat provenance")
    for k in NUMS:
        if not re.fullmatch(r"0|[1-9][0-9]*",v[k]):
            raise ValueError("noncanonical guard defeat numeric field: "+k)
    nums={k:int(v[k]) for k in NUMS}
    if (not 1<=nums["frame"]<=300 or
        not (3*16+16)*256<=nums["hero_x"]<=(3*16+80)*256 or
        nums["hero_hp"]!=5 or nums["guard_hp"]!=0 or
        nums["previous_guard_hp"]!=1 or nums["guard_hits"]!=3 or
        nums["previous_guard_hits"]!=2 or nums["guard_attacks"]!=0 or
        not 3<=nums["shots"]<=15 or nums["sentry_hp"]!=2 or
        nums["input_fire"]!=1 or
        any(nums[k]!=0 for k in ("wave","clear","dash"))):
        raise ValueError("guard was not killed by genuine third-run swept shot")
    return nums

def raster(base,name):
    png=base/(name+".png")
    ppm=base/(name+".ppm")
    if not png.is_file() or not png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("missing native X11 guard raster PNG: "+name)
    if not ppm.is_file():
        raise ValueError("missing native X11 guard raster P6: "+name)
    data=ppm.read_bytes()
    h=P6.match(data)
    if not h or len(data)!=h.end()+3*1280*720:
        raise ValueError("invalid raw X11 guard-kill framebuffer")
    return data[h.end():],hashlib.sha256(data).hexdigest()

def audit(evidence):
    base=Path(evidence)
    record=base/"guest-third-guard-clear-witness.txt"
    if not record.is_file():
        raise ValueError("native third-guard SD event missing")
    clear=verify(record.read_bytes())
    first=base/"guest-post-defeat-fire-witness.txt"
    if not first.is_file():
        raise ValueError("initial third-run live Fire/impact record missing")
    hit=previous.verify(first.read_bytes())
    if not (hit["hit_frame"]<clear["frame"]<=hit["hit_frame"]+160 and
            hit["hero_x"]==clear["hero_x"]):
        raise ValueError("guard-kill event not tied to previous live impact")
    result=base/"third-run-fire-result.txt"
    if not result.is_file() or not result.read_text(encoding="ascii").startswith(
        "VPD_NEXIUM_THIRD_RUN_FIRE_PASS "):
        raise ValueError("preceding real X11 first impact proof missing")
    host=base/"input-probe.txt"
    if not host.is_file() or (
        "host_third_guard_clear_sent=yes key=Z observed=yes"
        not in host.read_text(encoding="ascii").splitlines()
    ):
        raise ValueError("real held Fire/guard-kill host proof absent")
    timeline=base/"visual-probe.txt"
    if not timeline.is_file():
        raise ValueError("real native X11 capture history missing")
    events=timeline.read_text(encoding="ascii").splitlines()
    for tag in ("capture=screen-live-third-run-impact",
                "capture=screen-live-third-guard-clear",
                "live_third_guard_clear_raster_after_guest_event=yes"):
        if tag not in events:
            raise ValueError("guard-kill X11 capture not event aligned: "+tag)
    before,sha1=raster(base,"screen-live-third-run-impact")
    after,sha2=raster(base,"screen-live-third-guard-clear")
    # Grounded guard spans world x 224..320 => display x 448..640
    # and bottom half of X11 y 550..620 in the original arena.
    difference=0
    for y in range(530,631):
        lo=(y*1280+405)*3
        hi=(y*1280+690)*3
        a=before[lo:hi]
        b=after[lo:hi]
        difference+=sum(a[j:j+3]!=b[j:j+3] for j in range(0,len(a),3))
    if difference<300:
        raise ValueError("no visible native third-run guard removal/impact")
    summary=("VPD_NEXIUM_THIRD_GUARD_CLEAR_PASS "
             f"frame={clear['frame']} shots_fired={clear['shots']} "
             "hero_hp=5 guard_hp_before=1 guard_hp_after=0 "
             "guard_hits_total=3 real_pad_fire=yes source=live_guest "
             f"changed_guard_pixels={difference} "
             f"before_ppm_sha256={sha1} after_ppm_sha256={sha2} "
             "native_x11_evidence=yes original_game_proven=no "
             "physical_switch_proven=no\n")
    (base/"third-guard-clear-result.txt").write_text(summary,encoding="ascii")
    print(summary,end="")
    return clear

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (OSError,UnicodeError,ValueError) as exc:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"third-guard-clear-result.txt").write_text(
            "INCONCLUSIVE: "+str(exc)+"\n",encoding="ascii")
        parser.exit(1,"Native third-run guard kill unverified: "+str(exc)+"\n")
