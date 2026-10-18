#!/usr/bin/env python3
"""Stage131 native overlapping OAM sprite selection and XBuf acceptance."""
import argparse
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from make_stage131_dual_sprite_rom import make_rom, MODES
from run_stage100_fceux_synthetic_smoke import backend_settings, categorize_exit

MARKER="VPD_STAGE131_NATIVE_DUAL_SPRITES_PASS"
REJECTED="VPD_STAGE131_REJECTED_DUAL_SPRITES"
PATTERN=re.compile(
    r"^VPD_STAGE131_NATIVE_DUAL_SPRITES_PASS "
    r"case=(first_front|palette_swapped|first_transparent|first_behind|first_behind_clear) "
    r"row=(\d+) quadrant=(\d+) sample_x=64 samples=8 "
    r"oam_count=2 first_pattern=(\d+) second_pattern=(\d+) "
    r"claimed_oam=(\d+) sprite0_hit=(yes|no) xbuf=(\d+) invalid=0 "
    r"actual_fceux_dual_oam_xbuf=yes synthetic_only=yes "
    r"original_game_sprites_proven=no$",re.MULTILINE)
REJECT_PATTERN=re.compile(
    r"^VPD_STAGE131_REJECTED_DUAL_SPRITES "
    r"case=(first_front|palette_swapped|first_transparent|first_behind|first_behind_clear) "
    r"invalid=(\d+) row=(\d+) quadrant=(\d+) xbuf=(\d+) "
    r"samples=8 synthetic_only=yes$",re.MULTILINE)


class DualSpriteError(ValueError):
    pass


def expectations(mode,q):
    if mode not in MODES or type(q) is not int or not 0<=q<4:
        raise DualSpriteError("Invalid dual sprite mode/quadrant")
    return dict(first_pattern=0 if mode=="first_transparent" else 3,
                second_pattern=3,
                claimed_oam=1 if mode=="first_transparent" else 0,
                sprite0_hit=mode not in ("first_transparent","first_behind_clear"),
                xbuf=(184 if mode in ("palette_swapped","first_transparent") else
                      176+q if mode=="first_behind" else 170))


def verify(log,mode):
    if mode not in MODES or not isinstance(log,str) or log.count(MARKER)!=1 or REJECTED in log:
        raise DualSpriteError("Missing, duplicate or contradicted dual sprite proof")
    records=list(PATTERN.finditer(log))
    if len(records)!=1:
        raise DualSpriteError("Malformed real FCEUX dual-sprite certificate")
    name,row,q,p0,p1,winner,hit,color=records[0].groups()
    row,q,p0,p1,winner,color=map(int,(row,q,p0,p1,winner,color))
    e=expectations(mode,q)
    if (name!=mode or not 120<=row<=140 or p0!=e["first_pattern"] or
            p1!=e["second_pattern"] or winner!=e["claimed_oam"] or
            hit!=("yes" if e["sprite0_hit"] else "no") or color!=e["xbuf"]):
        raise DualSpriteError("Native OAM winner, CHR, hit or framebuffer contradicts witness")
    return dict(mode=mode,quadrant=q,samples=8,xbuf=color,
                claimed_oam=winner,sprite0_hit=e["sprite0_hit"],
                original_game_sprites_proven=False)


def verify_rejection(log,mode):
    if mode not in MODES or not isinstance(log,str) or log.count(REJECTED)!=1 or MARKER in log:
        raise DualSpriteError("Missing, duplicate or false-positive dual sprite control")
    matches=list(REJECT_PATTERN.finditer(log))
    if len(matches)!=1:
        raise DualSpriteError("Malformed native rejected OAM observation")
    name,invalid,row,q,color=matches[0].groups()
    invalid,row,q,color=map(int,(invalid,row,q,color))
    if (name!=mode or invalid<=0 or not 120<=row<=140 or
            q not in range(4) or color!=176+q):
        raise DualSpriteError("Negative control did not observe both transparent sprites")
    return dict(mode=mode,rejected=True,invalid=invalid,xbuf=color)


def verify_sweep(items):
    if not isinstance(items,list) or [name for name,_ in items]!=list(MODES):
        raise DualSpriteError("Five paired-OAM scenarios required")
    for mode,report in items:
        e=expectations(mode,report.get("quadrant"))
        if (report.get("samples")!=8 or report.get("xbuf")!=e["xbuf"] or
                report.get("claimed_oam")!=e["claimed_oam"] or
                report.get("sprite0_hit")!=e["sprite0_hit"] or
                report.get("original_game_sprites_proven") is not False):
            raise DualSpriteError("Incomplete native dual sprite evidence")
    return dict(scenarios=5,pixel_samples=40,native_dual_oam_proven=True,
                original_game_sprites_proven=False)


def execute(binary,rom,folder,mode,*,enabled=True,reject=False,timeout=35):
    if mode not in MODES or (not enabled and reject):
        raise DualSpriteError("Invalid native control selection")
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
    env["VPD_STAGE124_QUADRANT_PROBE"]="0"
    env["VPD_STAGE129_SPRITE_PROBE"]="0"
    env["VPD_STAGE131_DUAL_PROBE"]="1" if enabled else "0"
    env["VPD_STAGE131_DUAL_CASE"]=mode
    env.pop("VPD_STAGE126_TARGET_QUADRANT",None)
    env.pop("VPD_STAGE127_BACKDROP",None)
    cmd=[str(Path(binary).resolve()),"--newppu","1","--sound","0",
         "--opengl","0","--no-config","1",str(Path(rom).resolve())]
    logfile=folder/"native.log"
    with logfile.open("wb") as sink:
        proc=subprocess.Popen(cmd,cwd=folder,env=env,stdin=subprocess.DEVNULL,
                              stdout=sink,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+(timeout if enabled else 2)
        running=False
        try:
            while time.monotonic()<deadline:
                time.sleep(.1)
                log=logfile.read_text(encoding="utf8",errors="replace")
                if enabled and (MARKER in log or REJECTED in log):
                    break
                if proc.poll() is not None:
                    break
            running=proc.poll() is None
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4)
    log=logfile.read_text(encoding="utf8",errors="replace")
    if not enabled:
        if not running or MARKER in log or REJECTED in log:
            raise DualSpriteError("Observer-off emitted witness or exited early")
        return None
    try:
        return verify_rejection(log,mode) if reject else verify(log,mode)
    except DualSpriteError as exc:
        details=re.findall(r"VPD_STAGE131_REJECTED_DUAL_SPRITES [^\r\n]{0,240}",log)
        raise DualSpriteError(str(exc)+": "+(details[-1] if details else
                             categorize_exit(proc.returncode,log))) from exc


def run(binary,temp):
    with tempfile.TemporaryDirectory(dir=temp) as dirname:
        root=Path(dirname)
        results=[]
        for mode in MODES:
            rom=root/(mode+".nes")
            make_rom(rom,mode)
            results.append((mode,execute(binary,rom,root/mode,mode)))
        bad=root/"two_transparent.nes"
        make_rom(bad,"first_transparent",second_opaque=False)
        negative=execute(binary,bad,root/"bad_second","first_transparent",reject=True)
        execute(binary,root/"first_front.nes",root/"off","first_front",enabled=False)
    summary=verify_sweep(results)
    if negative["invalid"]<=0:
        raise DualSpriteError("Native negative control was not rejected")
    print("STAGE131_NATIVE_DUAL_OAM_PRIORITY_PROOF "
          "native_fceux=yes synthetic_mapper4_only=yes scenarios=5 samples=40 "
          "first_wins=yes transparent_first_passes_second=yes "
          "hidden_first_blocks_second=yes sprite0_hit_separate=yes "
          "transparent_second_negative=rejected observer_off_control=clean "
          "original_game_sprites_proven=no")
    return summary


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("native_fceux",type=Path)
    cli.add_argument("private_temp",type=Path)
    a=cli.parse_args()
    run(a.native_fceux,a.private_temp)
