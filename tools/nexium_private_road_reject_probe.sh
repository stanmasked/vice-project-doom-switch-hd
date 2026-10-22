#!/usr/bin/env bash
# Independent anti-false-positive NeXium emulator process. This scenario
# runs AFTER all existing successful realistic guest evidence (separate
# processes). File contents are exclusively invented road intervals.
set -euo pipefail
[[ $# -eq 3 ]] || { echo "Usage: probe emulator nro out"; exit 2; }
emulator="$1"; nro="$2"; out="$3"
mkdir -p "$out"
timeout --signal=TERM --kill-after=5s 85s "$emulator" "$nro"   > "$out/emulator-stdout.txt" 2>&1 &
emu_pid=$!
cleanup(){ kill "$emu_pid" 2>/dev/null||true;wait "$emu_pid" 2>/dev/null||true; }
trap cleanup EXIT
base="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom"
startup="$base/private_road_sd_guest.txt"
rejected="$base/private_road_reject_guest.txt"
r3="$base/private_road_r3_guest.txt"
builtin="$base/road_review_guest.txt"
sleep 10
win="$(xdotool search --onlyvisible --name '[Nn]e[Xx]ium'|tail -n 1)"
[[ -n "$win" ]] || { echo "BLOCKED: no NeXium window" >&2;exit 1; }
xdotool windowfocus "$win"
[[ -f "$startup" ]]
grep -q '^VPD_PRIVATE_ROAD_SD_V1 mounted=1 loaded=0 samples=0 first_frame=0 last_frame=0 ' "$startup"
cp "$startup" "$out/guest-private-road-sd-startup.txt"
# Established NeXium keyboard layout R+T+V enters manual driving.
xdotool keydown --clearmodifiers e
sleep 0.15
xdotool key --clearmodifiers --delay 130 c
xdotool keyup e
sleep 0.18
xdotool keydown --clearmodifiers r
xdotool keydown --clearmodifiers t
sleep 0.1
xdotool key --clearmodifiers --delay 130 v
sleep 0.24
# G maps to Right Stick click in NeXium's controller_config.rs.
xdotool key --clearmodifiers --delay 145 g
confirmed=no
for ((i=0;i<180;++i));do
  if [[ -f "$rejected" ]] &&
     grep -q '^VPD_PRIVATE_ROAD_REJECT_V1 loaded=0 native_r3=1 private_active=0 ' "$rejected";then
    confirmed=yes
    break
  fi
  sleep 0.045
done
[[ "$confirmed" == yes ]] || { echo "BLOCKED: source guest did not reject corrupted R3" >&2;exit 1; }
[[ ! -s "$r3" ]] || { echo "FALSE POSITIVE: private R3 guest activated invalid file" >&2;exit 1; }
capture() {
  local name="$1"
  xwd -root -screen -silent -out "$out/$name.xwd"
  convert "$out/$name.xwd" -depth 8 -define ppm:format=raw "ppm:$out/$name.ppm"
}
sleep 0.12
capture screen-corrupt-r3-off
# The independent built-in seven-observation Y mode must remain usable.
xdotool key --clearmodifiers --delay 140 z
found=no
for ((i=0;i<180;++i));do
  if [[ -f "$builtin" ]] &&
     grep -q '^VPD_ROAD_REVIEW_V1 seq=1 original_frame=600 ' "$builtin";then
    found=yes
    break
  fi
  sleep 0.045
done
[[ "$found" == yes ]] || { echo "BLOCKED: built-in Y review failed after invalid R3" >&2;exit 1; }
sleep 0.12
capture screen-corrupt-y-reference
xdotool keyup t
xdotool keyup r
cp "$rejected" "$out/guest-private-road-reject-witness.txt"
cp "$builtin" "$out/guest-original-seven-fallback.txt"
[[ ! -s "$r3" ]] || { echo "FALSE POSITIVE: invalid SD enabled R3" >&2;exit 1; }
echo "native_bad_r3_rejected=yes builtin_y_fallback=yes" > "$out/host-input.txt"
