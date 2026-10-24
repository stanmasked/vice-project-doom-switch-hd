#!/usr/bin/env python3
"""Stage364 strict source-free NeXium real guest ON/LAST audit.

Never mistake host-only keyboard events or synthetic C++ host tests for an
actual libnx guest framebuffer record. No original NES media is used.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


MARKER = "VPD_STAGE363_NUMERIC_DEMO_V1"
EXPECTED_PIXEL = "ffefda66"
EXPECTED_PANEL = "ff5b4118"
REQUIRED = {
    "source":"libnx_drawScene",
    "actual_original_rom_source_verification":"0",
    "original_game_physics_proven":"0",
    "raw_rom_fm2_present":"0",
}


def parse_line(line: str)->dict:
    parts=line.strip().split()
    if not parts or parts[0]!=MARKER:
        raise ValueError("not a real Stage363 guest record")
    parsed={}
    for part in parts[1:]:
        if part.count("=")!=1:
            raise ValueError("invalid guest field")
        key,value=part.split("=")
        if key in parsed or not key or not value:
            raise ValueError("duplicate/missing guest field")
        parsed[key]=value
    required={"event","original_pair_start","guest_frame","image_shift",
              "panel_pixel","edge_pixel","demo_glyph_pixel","platform_fp",*REQUIRED}
    if set(parsed)!=required:
        raise ValueError("wrong guest witness schema")
    for key,value in REQUIRED.items():
        if parsed[key]!=value:
            raise ValueError("unverified source or false physical proof marker")
    for key,value in (("panel_pixel",EXPECTED_PANEL),
                      ("edge_pixel",EXPECTED_PIXEL),
                      ("demo_glyph_pixel",EXPECTED_PIXEL)):
        if parsed[key].lower()!=value:
            raise ValueError("real NRO RGBA source pixel sample wrong")
    for key in ("original_pair_start","guest_frame","image_shift"):
        if not parsed[key].isdigit():
            raise ValueError("invalid guest numeric value")
    if not (len(parsed["platform_fp"])==16 and
            all(c in "0123456789abcdefABCDEF" for c in parsed["platform_fp"])):
        raise ValueError("platform state fingerprint invalid")
    return parsed


def audit_evidence(host:str,driving:str,guest:str)->dict:
    if ("physical_keyboard_chord=R+T+Q Switch=ZL+ZR+L" not in host or
        "native_driving_enter=yes" not in host or
        "guest_on=yes" not in host or "guest_last=yes" not in host or
        "STAGE364_REAL_NEXIUM_SCROLL_DEMO_GUEST_EVENTS_OBSERVED" not in host):
        raise ValueError("no exact real NeXium host controller witness")
    if "VPD_DRIVING_GUEST_V1 seq=1 event=enter " not in driving:
        raise ValueError("no real game guest driving entry")
    rows=guest.splitlines()
    if len(rows)!=2:
        raise ValueError("exactly on and last physical guest records required")
    a,b=[parse_line(row) for row in rows]
    if (a["event"]!="on" or b["event"]!="last" or
        int(a["original_pair_start"])!=519 or
        int(b["original_pair_start"])!=559 or
        int(a["image_shift"])!=3 or
        int(b["image_shift"])!=5 or
        int(b["guest_frame"])-int(a["guest_frame"])!=40 or
        int(a["guest_frame"])<1 or
        a["platform_fp"]!=b["platform_fp"]):
        raise ValueError("guest manual DEMO did not show real 41-frame finite cycle")
    return {
        "format":"vpd_stage364_real_nexium_manual_scroll_source_safe_guest_v1",
        "real_native_guest_on_and_last":True,
        "real_controller_chord":"NeXium Q+R+T => Switch L+ZL+ZR",
        "first_numeric_pair":519,
        "last_numeric_pair":559,
        "guest_presentation_steps":40,
        "first_observed_image_shift_px":3,
        "last_observed_image_shift_px":5,
        "identical_guest_platform_fingerprint_at_both_endpoints":True,
        "libnx_guest_road_panel_and_DEMO_glyph_rgba_checked":True,
        "new_original_rom_or_fm2_source_used":False,
        "original_camera_or_vehicle_physics_proven":False,
        "host_screenshot_automatically_checked":False,
    }


def audit_dir(path:Path)->dict:
    def read(name:str)->str:
        p=path/name
        if p.is_symlink() or not p.is_file() or p.stat().st_size>1000000:
            raise ValueError("missing, symlinked or overlarge guest evidence "+name)
        return p.read_text(encoding="utf8")
    result=audit_evidence(read("host-events.txt"),read("guest-driving-enter.txt"),
                          read("guest-scroll-demo.txt"))
    # Corroborate live HOST/X11 screenshot separately, but don't fabricate a
    # screenshot or call its absence guest proof. Full X11 pixel snapshot is
    # stronger when it captures the very short guest DEMO frame interval.
    try:
        from PIL import Image
    except ImportError:
        result["host_screenshot_check"]="unavailable_pillow"
        return result
    matches=[]
    for p in sorted(path.glob("screen-demo-*.png")):
        with Image.open(p) as im:
            if im.width<1000 or im.height<600:
                continue
            rgb=im.convert("RGB")
            px=rgb.load()
            count=0
            for y in range(250,min(rgb.height,380),3):
                for x in range(850,min(rgb.width,1280),3):
                    R,G,B=px[x,y]
                    if 95<=R<=110 and 210<=G<=228 and 231<=B<=246:
                        count+=1
            if count>=5:
                matches.append(p.name)
    result["host_screenshot_check"]="present" if matches else "not_captured_at_short_overlay_window"
    result["host_screenshot_automatically_checked"]=True
    result["host_screenshot_matching_files"]=matches
    return result


def main()->None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence",required=True,type=Path)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    try:
        result=audit_dir(args.evidence)
        msg=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if args.output:
            if args.output.exists() or args.output.is_symlink():
                raise ValueError("cannot overwrite prior witness")
            args.output.write_text(msg)
        else: print(msg,end="")
    except (OSError,ValueError,KeyError,TypeError,UnicodeError) as exc:
        ap.exit(1,"STAGE364_REAL_NEXIUM_SCROLL_DEMO_UNCONFIRMED: "+str(exc)+"\n")


if __name__=="__main__":main()
