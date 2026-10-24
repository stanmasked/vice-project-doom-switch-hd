#!/usr/bin/env bash
# Stage365: capture all 41 genuine libnx guest framebuffer states.
# Never writes a guest record. No original NES ROM/FM2 is used.
set -euo pipefail
[[ $# -eq 3 ]] || { echo "Usage: $0 emulator exact-head.nro evidence-dir" >&2;exit 2; }
emu="$1"; nro="$2"; out="$3"
mkdir -p "$out"
guest="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/scroll_demo_guest_v2.txt"
driving="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/driving_guest.txt"
pid=""
cleanup() {
  xdotool keyup q 2>/dev/null || true
  xdotool keyup t 2>/dev/null || true
  xdotool keyup r 2>/dev/null || true
  if [[ -n "$pid" ]];then
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
timeout --signal=TERM --kill-after=5s 100s "$emu" "$nro" >"$out/neXium-stdout.txt" 2>&1 &
pid=$!
printf 'nro_sha256=%s\n' "$(sha256sum "$nro" | cut -d ' ' -f1)" >"$out/host-events.txt"
sleep 10
win="$(xdotool search --onlyvisible --name '[Nn]e[Xx]ium' | tail -n 1)"
[[ -n "$win" ]] || { echo "BLOCKED: NeXium GUI window not visible" >&2;exit 1; }
xdotool windowfocus "$win"
# Default upstream map: E=R, C=A, R=ZL, T=ZR, V=X, Q=L.
xdotool keydown --clearmodifiers e
sleep 0.20
xdotool key --clearmodifiers --delay 150 c
xdotool keyup e
sleep 0.16
xdotool keydown --clearmodifiers r
xdotool keydown --clearmodifiers t
sleep 0.10
xdotool key --clearmodifiers --delay 150 v
sleep 0.14
xdotool keyup t
xdotool keyup r
entered=no
for ((i=0;i<200;++i));do
  if [[ -f "$driving" ]] &&
    grep -q '^VPD_DRIVING_GUEST_V1 seq=1 event=enter ' "$driving";then
    entered=yes;break
  fi
  sleep 0.05
done
printf 'native_driving_enter=%s\n' "$entered" >>"$out/host-events.txt"
[[ "$entered" == yes ]] || { echo "INCONCLUSIVE: no actual manual driving guest entry" >&2;exit 1; }
cp -- "$driving" "$out/guest-driving-enter.txt"
# The fresh L-down edge is the real ZL+ZR+L chord. Capture only actual X11.
xdotool keydown --clearmodifiers r
xdotool keydown --clearmodifiers t
sleep 0.07
printf 'physical_keyboard_chord=R+T+Q Switch=ZL+ZR+L\n' >>"$out/host-events.txt"
xdotool keydown --clearmodifiers q
for ((i=0;i<4;++i));do
  xwd -root -screen -silent -out "$out/screen-demo-$i.xwd" || true
  sleep 0.06
done
xdotool keyup q
xdotool keyup t
xdotool keyup r
count=0
first=no
last=no
for ((i=0;i<300;++i));do
  if [[ -f "$guest" ]];then
    count="$(wc -l <"$guest" | tr -d ' ')"
    [[ "$count" -ge 1 ]] && grep -q '^VPD_STAGE365_NUMERIC_DEMO_V2 event=on ' "$guest" && first=on
    [[ "$count" -ge 1 ]] && grep -q '^VPD_STAGE365_NUMERIC_DEMO_V2 event=last ' "$guest" && last=last
  fi
  [[ "$count" -ge 41 && "$first" == on && "$last" == last ]] && break
  sleep 0.06
done
printf 'guest_v2_records=%s\nguest_v2_first=%s\nguest_v2_last=%s\n' "$count" "$first" "$last" >>"$out/host-events.txt"
[[ -f "$guest" ]] || { echo "INCONCLUSIVE: real guest trace file missing" >&2;exit 1; }
cp -- "$guest" "$out/guest-scroll-demo-v2.txt"
sha256sum "$out/guest-scroll-demo-v2.txt" >>"$out/host-events.txt"
cp -- "$driving" "$out/guest-driving-enter.txt"
for img in "$out"/screen-demo-*.xwd;do
  [[ -s "$img" ]] || continue
  convert "$img" -strip "png:$out/$(basename "$img" .xwd).png"
done
[[ "$count" == 41 && "$first" == on && "$last" == last ]] || {
  echo "INCONCLUSIVE: expected exactly 41 real guest states, got $count" >&2;exit 1;
}
echo 'STAGE365_REAL_NEXIUM_FULL_SEQUENCE_OBSERVED' >>"$out/host-events.txt"
