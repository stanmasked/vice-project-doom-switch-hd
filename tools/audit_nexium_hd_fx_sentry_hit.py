#!/usr/bin/env python3
"""Fail-closed source/X11 proof of actual sentry bullet HP loss after guest HD L+R."""
import argparse
from pathlib import Path
import re
from audit_nexium_fourth_stage import raster, verify as verify_stage
from audit_nexium_hd_fx_sentry import verify as verify_sentry

RECORD=re.compile(
    r"^VPD_HD_FX_SENTRY_HIT_V1 frame=([0-9]+) on_frame=([0-9]+) "
    r"bullet_slot=([0-2]) bullet_age_before=([0-9]+) "
    r"bullet_x_before=([0-9]+) bullet_y=([0-9]+) bullet_vx=-768 "
    r"hero_x=([0-9]+) hero_y=([0-9]+) "
    r"hero_hp_before=([1-5]) hero_hp_after=([0-5]) "
    r"shots_hit_before=([0-9]+) shots_hit_after=([0-9]+) "
    r"input=idle mode=on wave=1 guard_hp=0 "
    r"sentry_hp=2 bullet_consumed=yes "
    r"simulation_before=([0-9a-f]{16}) simulation_after=([0-9a-f]{16}) "
    r"source=libnx_tick collision=swept original_game_proven=no$"
)
FIELDS=("frame","on_frame","bullet_slot","bullet_age_before","bullet_x_before",
        "bullet_y","hero_x","hero_y","hero_hp_before","hero_hp_after",
        "shots_hit_before","shots_hit_after")

def verify(raw, on):
    if not isinstance(raw,bytes) or len(raw)>850 or not raw.endswith(b"\n"):
        raise ValueError("real sentry hit guest record missing/truncated/oversized")
    try:
        lines=raw.decode("ascii").splitlines()
    except UnicodeError as error:
        raise ValueError("non-ASCII source sentry collision trace") from error
    if len(lines)!=1:
        raise ValueError("exactly one real projectile hit after L+R required")
    m=RECORD.fullmatch(lines[0])
    if not m:
        raise ValueError("malformed source sentry swept-hit trace")
    v={key:int(m.group(i+1)) for i,key in enumerate(FIELDS)}
    old,new=m.group(13),m.group(14)
    if old==new:
        raise ValueError("a physics hit must change authoritative source state")
    delta=v["frame"]-on["frame"]
    before=delta-1
    if not 1<=delta<=90-on["age"] or not 0<=before<90:
        raise ValueError("source hit not after live HD ON while bullet exists")
    if (v["on_frame"]!=on["frame"] or
        v["bullet_slot"]!=on["slot"] or
        v["bullet_age_before"]!=on["age"]+before or
        v["bullet_x_before"]!=on["x"]-768*before or
        v["bullet_y"]!=on["y"]):
        raise ValueError("hit not caused by same moving HD-witnessed bullet")
    if not (v["hero_hp_before"]==on["hero_hp"] and
            v["hero_hp_after"]==on["hero_hp"]-1 and
            v["hero_hp_after"]>=1 and
            v["shots_hit_before"]==0 and
            v["shots_hit_after"]==1):
        raise ValueError("real first sentry collision HP/shot counters invalid")
    if (not v["hero_y"]<=v["bullet_y"]<v["hero_y"]+14*256 or
        not v["bullet_x_before"]>=v["hero_x"] or
        not v["bullet_x_before"]-3*256<v["hero_x"]+12*256):
        raise ValueError("swept hostile bullet never intersected hero hitbox")
    return v

# Exact per-heart horizontal bounds from the preserved 1280x720 NeXium
# native capture. Keep these disjoint from the fifth heart's cell.
LIVE_HEART_RECTS=((757,766),(771,781),(786,795),(800,810))
FIFTH_HEART_RECT=(814,824)

def fifth_heart_loss(before,after):
    """Verify one lost heart AND the survival of *each* of the other four.

    All coordinates are captured native X11 pixels, not untransformed
    renderer coordinates. The earlier sum-only guard admitted small,
    localized loss in another cell if enough other healthy pixels remained.
    """
    if len(before)!=1280*720*3 or len(after)!=len(before):
        raise ValueError("native X11 heart raster dimensions invalid")
    healthy=bytes((106,198,174))
    empty=bytes((55,64,79))
    flashed=bytes((255,220,153))
    changed=0
    for y in range(15,32):
        for x in range(FIFTH_HEART_RECT[0],FIFTH_HEART_RECT[1]+1):
            ix=(y*1280+x)*3
            if before[ix:ix+3]==healthy and after[ix:ix+3]==empty:
                changed+=1
    kept_total=0
    for number,(left,right) in enumerate(LIVE_HEART_RECTS,1):
        kept=0
        lost=0
        for y in range(15,32):
            for x in range(left,right+1):
                ix=(y*1280+x)*3
                if before[ix:ix+3]!=healthy:
                    continue
                current=after[ix:ix+3]
                if current in (healthy,flashed):
                    kept+=1
                elif current==empty:
                    lost+=1
        # The authentic post-collision image yields 120/132/120/132.
        # Reject even partial teal-to-empty changes in any previous cell:
        # a global 440-pixel sum could previously mask a damaged cell.
        if kept<105 or lost:
            raise ValueError(
                f"remaining heart {number} changed or disappeared in X11 "
                f"(preserved={kept}, lost={lost})")
        kept_total+=kept
    if changed<80 or kept_total<440:
        raise ValueError(
            "fifth heart did not turn from healthy to empty with four "
            "remaining hearts in genuine X11 pixels")
    return changed

def audit(base):
    base=Path(base)
    prior=(base/"hd-fx-sentry-result.txt").read_text("ascii")
    stage_result=(base/"fourth-stage-result.txt").read_text("ascii")
    if (not prior.startswith("VPD_NEXIUM_HD_FX_SENTRY_PASS ") or
        not stage_result.startswith("VPD_NEXIUM_FOURTH_STAGE_PASS ")):
        raise ValueError("independent real L+R and earned fourth-stage proof absent")
    stages=verify_stage((base/"guest-fourth-stage-witness.txt").read_bytes())
    off,on=verify_sentry((base/"guest-hd-fx-sentry-witness.txt").read_bytes())
    witness=base/"guest-hd-fx-sentry-hit-witness.txt"
    if not witness.is_file():
        raise ValueError("native sentry hit file absent")
    hit=verify(witness.read_bytes(),on)
    if not (stages["wave_frame"]<off["frame"]<
            on["frame"]<hit["frame"]<stages["exit_frame"]):
        raise ValueError("sentry projectile hit not inside same fourth-wave run")
    host=(base/"input-probe.txt").read_text("ascii").splitlines()
    visual=(base/"visual-probe.txt").read_text("ascii").splitlines()
    if host.count("host_sentry_projectile_hit_observed=yes source=live_guest")!=1:
        raise ValueError("real host never saw guest source projectile hit")
    if visual.count("capture=screen-live-sentry-after-hit")!=1:
        raise ValueError("X11 capture after real source collision absent")
    if visual.count("live_sentry_damage_raster_after_guest_event=yes")!=1:
        raise ValueError("damage X11 event-capture chronology not recorded")
    before,sha_before=raster(base,"screen-live-sentry-hd-fx-on")
    after,sha_after=raster(base,"screen-live-sentry-after-hit")
    if sha_before==sha_after:
        raise ValueError("X11 image did not change after genuine hero HP loss")
    changed=fifth_heart_loss(before,after)
    result=(
        "VPD_NEXIUM_HD_FX_SENTRY_HIT_PASS "
        f"on_frame={on['frame']} hit_frame={hit['frame']} "
        f"bullet_slot={hit['bullet_slot']} "
        f"bullet_age_before={hit['bullet_age_before']} "
        f"hero_hp_before={hit['hero_hp_before']} "
        f"hero_hp_after={hit['hero_hp_after']} "
        "source_collision=swept first_hostile_hit=yes "
        "source_simulation_changed_from_physics=yes "
        f"fifth_heart_x11_changed_pixels={changed} "
        f"before_ppm_sha256={sha_before} after_ppm_sha256={sha_after} "
        "source=libnx_tick native_x11_evidence=yes "
        "original_game_proven=no physical_switch_proven=no\n"
    )
    (base/"hd-fx-sentry-hit-result.txt").write_text(result,encoding="ascii")
    print(result,end="")
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",required=True,type=Path)
    args=parser.parse_args()
    try:
        audit(args.evidence)
    except (ValueError,OSError,UnicodeError) as error:
        args.evidence.mkdir(parents=True,exist_ok=True)
        (args.evidence/"hd-fx-sentry-hit-result.txt").write_text(
            "INCONCLUSIVE: "+str(error)+"\n",encoding="ascii")
        parser.exit(1,"Real sentry projectile collision unverified: "+str(error)+"\n")
