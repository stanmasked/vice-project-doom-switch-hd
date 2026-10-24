#!/usr/bin/env bash
# Stage365/369: deterministic handshake for real manual mode and 41 guest states.
# Never writes a guest record. No original NES ROM/FM2 is used.
set -euo pipefail
[[ $# -eq 3 ]] || { echo "Usage: $0 emulator exact-head.nro evidence-dir" >&2;exit 2; }
emu="$1"; nro="$2"; out="$3"
mkdir -p "$out"
sd="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom"
manual="$sd/manual_witness.txt"
guest="$sd/scroll_demo_guest_v2.txt"
driving="$sd/driving_guest.txt"
pid=""
capture() {
  local name="$1"
  if xwd -root -screen -silent -out "$out/$name.xwd" 2>/dev/null &&
     [[ -s "$out/$name.xwd" ]];then
    convert "$out/$name.xwd" -strip "png:$out/$name.png" 2>/dev/null || true
  fi
}
cleanup() {
  xdotool keyup q 2>/dev/null || true
  xdotool keyup t 2>/dev/null || true
  xdotool keyup r 2>/dev/null || true
  xdotool keyup c 2>/dev/null || true
  xdotool keyup e 2>/dev/null || true
  if [[ -n "$pid" ]];then
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
timeout --signal=TERM --kill-after=5s 100s "$emu" "$nro" >"$out/neXium-stdout.txt" 2>&1 &
pid=$!
printf 'nro_sha256=%s\n' "$(sha256sum "$nro" | cut -d ' ' -f1)" >"$out/host-events.txt"
# Wait for guest startup's own reset file; window existence alone is not readiness.
ready=no
for ((i=0;i<300;++i));do
  if [[ -f "$manual" && -f "$driving" && -f "$guest" ]];then ready=yes;break;fi
  sleep 0.10
done
printf 'guest_sd_witness_files_ready=%s\n' "$ready" >>"$out/host-events.txt"
[[ "$ready" == yes ]] || { capture "screen-startup-failed";echo "INCONCLUSIVE: NRO did not initialize its own SD witness files" >&2;exit 1; }
win=""
for ((i=0;i<100;++i));do
  win="$(xdotool search --onlyvisible --name '[Nn]e[Xx]ium' 2>/dev/null | tail -n 1 || true)"
  [[ -n "$win" ]] && break
  sleep 0.10
done
[[ -n "$win" ]] || { capture "screen-window-missing";echo "BLOCKED: NeXium GUI window not visible" >&2;exit 1; }
xdotool windowfocus --sync "$win"
sleep 0.35
focus="$(xdotool getwindowfocus 2>/dev/null || true)"
printf 'neXium_window=%s\nneXium_focused_window=%s\n' "$win" "$focus" >>"$out/host-events.txt"
[[ "$focus" == "$win" ]] || { capture "screen-focus-failed";echo "INCONCLUSIVE: NeXium did not receive keyboard focus" >&2;exit 1; }
capture "screen-startup"
# Upstream default key map: E=R, C=A, R=ZL, T=ZR, V=X, Q=L.
# Manual mode is confirmed by the NRO's own manual_witness.txt, not by keypress alone.
xdotool keydown e
sleep 0.25
xdotool keydown c
sleep 0.22
xdotool keyup c
sleep 0.12
xdotool keyup e
manual_entered=no
for ((i=0;i<100;++i));do
  if grep -q '^VPD_ROMFREE_MANUAL_V1 seq=1 event=enter frame=0 metric=1 mode=manual original_game_proven=no$' "$manual";then
    manual_entered=yes;break
  fi
  sleep 0.05
done
printf 'native_manual_entry=%s\n' "$manual_entered" >>"$out/host-events.txt"
cp -- "$manual" "$out/manual-witness.txt"
[[ "$manual_entered" == yes ]] || { capture "screen-manual-entry-failed";echo "INCONCLUSIVE: no actual NRO manual-mode entry witness after ready handshake" >&2;exit 1; }
capture "screen-manual-entry"
# Fresh X edge while both shoulders are down enters the manual driving preview.
xdotool keydown r
xdotool keydown t
sleep 0.12
xdotool keydown v
sleep 0.22
xdotool keyup v
xdotool keyup t
xdotool keyup r
entered=no
for ((i=0;i<100;++i));do
  if grep -q '^VPD_DRIVING_GUEST_V1 seq=1 event=enter ' "$driving";then entered=yes;break;fi
  sleep 0.05
done
printf 'native_driving_enter=%s\n' "$entered" >>"$out/host-events.txt"
cp -- "$driving" "$out/guest-driving-enter.txt"
[[ "$entered" == yes ]] || { capture "screen-driving-entry-failed";echo "INCONCLUSIVE: manual mode witnessed but no real driving-preview entry" >&2;exit 1; }
# The fresh L-down edge is the actual ZL+ZR+L chord.
xdotool keydown r
xdotool keydown t
sleep 0.10
printf 'physical_keyboard_chord=R+T+Q Switch=ZL+ZR+L\n' >>"$out/host-events.txt"
xdotool keydown q
for ((i=0;i<4;++i));do
  capture "screen-demo-$i"
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
[[ -f "$guest" ]] || { capture "screen-no-guest-trace";echo "INCONCLUSIVE: real guest trace file missing" >&2;exit 1; }
cp -- "$guest" "$out/guest-scroll-demo-v2.txt"
sha256sum "$out/guest-scroll-demo-v2.txt" >>"$out/host-events.txt"
for img in "$out"/screen-demo-*.xwd;do
  [[ -s "$img" ]] || continue
  convert "$img" -strip "png:$out/$(basename "$img" .xwd).png" 2>/dev/null || true
done
[[ "$count" == 41 && "$first" == on && "$last" == last ]] || {
  capture "screen-incomplete-sequence";echo "INCONCLUSIVE: expected exactly 41 real guest states, got $count" >&2;exit 1;
}
echo 'STAGE365_REAL_NEXIUM_FULL_SEQUENCE_OBSERVED' >>"$out/host-events.txt"
