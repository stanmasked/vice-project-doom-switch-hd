#!/usr/bin/env python3
"""Stage135 strict pinned FCEUX 8x16 upper/lower CHR bank and XBuf proof."""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from make_stage134_sprite_8x16_rom import MODES, make_rom
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

PASS="VPD_STAGE135_NATIVE_8X16_PASS"
REJECT="VPD_STAGE135_REJECTED_8X16"
PASS_RE=re.compile(
    r"^VPD_STAGE135_NATIVE_8X16_PASS "
    r"mode=(odd_normal|odd_vertical|even_normal|even_vertical) "
    r"top_row=(\d+) bottom_row=(\d+) top_sl=(\d+) bottom_sl=(\d+) "
    r"top_xbuf=(\d+) bottom_xbuf=(\d+) samples=16 invalid=0 "
    r"actual_fceux_8x16_xbuf=yes synthetic_only=yes "
    r"original_game_8x16_proven=no$",re.MULTILINE)
REJECT_RE=re.compile(
    r"^VPD_STAGE135_REJECTED_8X16 "
    r"mode=(odd_normal|odd_vertical|even_normal|even_vertical) "
    r"invalid=(\d+) ordering_bad=(yes|no) "
    r"top_row=(\d+) bottom_row=(\d+) "
    r"top_sl=(\d+) bottom_sl=(\d+) "
    r"top_xbuf=(\d+) bottom_xbuf=(\d+) "
    r"samples=16 synthetic_only=yes$",re.MULTILINE)

class Native16Error(ValueError):
    pass

def expected(mode):
    if mode not in MODES:
        raise Native16Error("Unknown 8x16 OAM test scenario")
    odd=mode.startswith("odd_")
    return (154,170) if odd else (171,154)

def verify(log,mode):
    expected(mode)
    if not isinstance(log,str) or log.count(PASS)!=1 or REJECT in log:
        raise Native16Error("Absent, duplicate or contradicted FCEUX 8x16 evidence")
    found=list(PASS_RE.finditer(log))
    if len(found)!=1:
        raise Native16Error("Malformed 8x16 native certificate")
    actual,top,bottom,sl_top,sl_bottom,col_top,col_bottom=found[0].groups()
    numbers=(top,bottom,sl_top,sl_bottom,col_top,col_bottom)
    if any(str(int(token))!=token for token in numbers):
        raise Native16Error("Noncanonical numeric representation in native proof")
    top,bottom,sl_top,sl_bottom,col_top,col_bottom=map(int,numbers)
    flipped=mode.endswith("vertical")
    normal_order=sl_top<sl_bottom
    if (actual!=mode or not 0<=top<8 or not 8<=bottom<16 or
            not 120<=sl_top<=142 or not 120<=sl_bottom<=142 or
            normal_order==flipped or
            (col_top,col_bottom)!=expected(mode)):
        raise Native16Error("Native CHR pair, bank, scanline or pixel contradiction")
    return dict(mode=mode,source_top=top,source_bottom=bottom,
                top_scanline=sl_top,bottom_scanline=sl_bottom,
                upper_xbuf=col_top,lower_xbuf=col_bottom,
                samples=16,native_8x16_proven=True,
                original_game_8x16_proven=False)

def verify_rejection(log):
    if not isinstance(log,str) or log.count(REJECT)!=1 or PASS in log:
        raise Native16Error("Expected exactly one genuine native control rejection")
    found=list(REJECT_RE.finditer(log))
    if len(found)!=1:
        raise Native16Error("Malformed negative witness")
    mode,invalid,ordering,top,bottom,sl_top,sl_bottom,col_top,col_bottom=found[0].groups()
    numbers=(invalid,top,bottom,sl_top,sl_bottom,col_top,col_bottom)
    if any(str(int(token))!=token for token in numbers):
        raise Native16Error("Noncanonical numeric representation in rejection")
    invalid,top,bottom,sl_top,sl_bottom,col_top,col_bottom=map(int,numbers)
    if (mode!="even_normal" or invalid<=0 or invalid>16 or
            not 0<=top<8 or not 8<=bottom<16 or
            not 120<=sl_top<=142 or not 120<=sl_bottom<=142 or
            sl_top>=sl_bottom or ordering!="no" or
            (col_top,col_bottom)!=(154,170)):
        raise Native16Error("Negative 8x16 control did not demonstrate wrong bank")
    return dict(rejected=True,wrong_bank=True)

def verify_sweep(items):
    if (not isinstance(items,list) or
            [mode for mode,_ in items]!=list(MODES)):
        raise Native16Error("Four native 8x16 modes required in pinned order")
    scans=[]
    for mode,item in items:
        if (item.get("mode")!=mode or item.get("samples")!=16 or
                (item.get("upper_xbuf"),item.get("lower_xbuf"))!=expected(mode) or
                item.get("native_8x16_proven") is not True or
                item.get("original_game_8x16_proven") is not False):
            raise Native16Error("Eight-sixteen evidence incomplete")
        scans.append((item["top_scanline"],item["bottom_scanline"]))
    # Runs with the same OAM position must agree on physical raster rows.
    if (scans[0]!=scans[2] or scans[1]!=scans[3] or
            scans[0]!=(scans[1][1],scans[1][0])):
        raise Native16Error("Flip and bank controls render on different raster rows")
    return dict(modes=4,samples=64,native_8x16_proven=True,
                original_game_8x16_proven=False)

def execute(binary,rom,folder,mode,*,enabled=True,reject=False,timeout=40):
    expected(mode)
    if reject and not enabled:
        raise Native16Error("Disabled observer cannot prove a rejection")
    folder.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    env.update(backend_settings("xvfb",folder))
    for key in ("VPD_STAGE100_SYNTHETIC_SMOKE","VPD_STAGE102_STATUS_PROBE",
                "VPD_STAGE103_PPUSTATUS_READ_PROBE","VPD_STAGE104_EVENT_ORDER_PROBE",
                "VPD_STAGE105_PRECLEAR_PROBE","VPD_STAGE106_MMC3_CHR_PROBE",
                "VPD_STAGE107_BG_PIXEL_PROBE","VPD_STAGE108_BG_FETCH_PROBE",
                "VPD_STAGE109_CHR_TIMELINE_PROBE","VPD_STAGE111_BG_TILE_PROBE",
                "VPD_STAGE113_BG_PREFETCH_PROBE","VPD_STAGE114_PLANE_PAIR_PROBE",
                "VPD_STAGE115_SCANLINE_CARRY_PROBE","VPD_STAGE116_FINE_SCROLL_PROBE",
                "VPD_STAGE117_DYNAMIC_SCROLL_PROBE","VPD_STAGE118_TWO_SCROLL_PROBE",
                "VPD_STAGE119_NAMETABLE_PROBE"):
        env[key]="0"
    env["VPD_STAGE110_MIDFRAME_CHR_PROBE"]="1"
    for key in ("VPD_STAGE124_QUADRANT_PROBE","VPD_STAGE129_SPRITE_PROBE",
                "VPD_STAGE131_DUAL_PROBE","VPD_STAGE133_FLIP_PROBE"):
        env[key]="0"
    env["VPD_STAGE135_8X16_PROBE"]="1" if enabled else "0"
    env["VPD_STAGE135_8X16_MODE"]=mode
    env.pop("VPD_STAGE126_TARGET_QUADRANT",None)
    env.pop("VPD_STAGE127_BACKDROP",None)
    cmd=[str(Path(binary).resolve()),"--newppu","1","--sound","0",
         "--opengl","0","--no-config","1",str(Path(rom).resolve())]
    logfile=folder/"native.log"
    with logfile.open("wb") as sink:
        p=subprocess.Popen(cmd,cwd=folder,env=env,stdin=subprocess.DEVNULL,
                           stdout=sink,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+(timeout if enabled else 2)
        alive=False
        try:
            while time.monotonic()<deadline:
                time.sleep(0.1)
                content=logfile.read_text(encoding="utf8",errors="replace")
                if enabled and (PASS in content or REJECT in content):
                    break
                if p.poll() is not None:
                    break
            alive=p.poll() is None
        finally:
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    p.kill();p.wait(timeout=4)
    log=logfile.read_text(encoding="utf8",errors="replace")
    if not enabled:
        if not alive or PASS in log or REJECT in log:
            raise Native16Error("Disabled native observer supplied false proof")
        return None
    try:
        return verify_rejection(log) if reject else verify(log,mode)
    except Native16Error as exc:
        detail=re.findall(
            r"VPD_STAGE135_REJECTED_8X16 [^\r\n]{0,400}",log)
        raise Native16Error(str(exc)+": "+(
            detail[-1] if detail else categorize_exit(p.returncode,log))) from exc

def run(binary,temp):
    with tempfile.TemporaryDirectory(dir=temp) as name:
        root=Path(name)
        reports=[]
        for mode in MODES:
            path=root/(mode+".nes")
            make_rom(path,mode)
            reports.append((mode,execute(binary,path,root/mode,mode)))
        negative=execute(binary,root/"odd_normal.nes",root/"wrong_bank",
                         "even_normal",reject=True)
        execute(binary,root/"odd_normal.nes",root/"disabled","odd_normal",
                enabled=False)
    verify_sweep(reports)
    if not negative["wrong_bank"]:
        raise Native16Error("Invalid negative bank control")
    print("STAGE135_NATIVE_SPRITE_8X16_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes modes=4 samples=64 "
          "odd_even_bank_proven=yes vertical_tile_half_swap=yes "
          "wrong_bank_control=rejected disabled_observer_control=clean "
          "original_game_8x16_proven=no")
    return reports

if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("native_fceux",type=Path)
    cli.add_argument("private_temp",type=Path)
    args=cli.parse_args()
    run(args.native_fceux,args.private_temp)
