#!/usr/bin/env bash
# Stage371: real NeXium DEMO start -> cancel -> off -> fresh-edge restart.
# Never injects guest witness records and never loads original NES ROM/FM2.
set -euo pipefail
[[ $# -eq 3 ]] || { echo "Usage: $0 emulator exact-head.nro evidence-dir" >&2;exit 2; }
emu="$1"; nro="$2"; out="$3"
mkdir -p "$out"
sd="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom"
manual="$sd/manual_witness.txt"
guest="$sd/scroll_demo_guest_v2.txt"
driving="$sd/driving_guest.txt"
pid=""
completed=no
capture_raw() {
  local name="$1"
  xwd -root -screen -silent -out "$out/$name.xwd" 2>/dev/null
}
convert_screens() {
  for img in "$out"/*.xwd;do
    [[ -s "$img" ]] || continue
    convert "$img" -strip "png:$out/$(basename "$img" .xwd).png" 2>/dev/null || true
  done
}
cleanup() {
  xdotool keyup q 2>/dev/null || true
  xdotool keyup t 2>/dev/null || true
  xdotool keyup r 2>/dev/null || true
  xdotool keyup c 2>/dev/null || true
  xdotool keyup e 2>/dev/null || true
  if [[ "$completed" != yes ]];then capture_raw "screen-failure" 2>/dev/null || true;fi
  convert_screens
  if [[ -n "$pid" ]];then
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
timeout --signal=TERM --kill-after=5s 100s "$emu" "$nro" >"$out/neXium-stdout.txt" 2>&1 &
pid=$!
printf 'nro_sha256=%s\n' "$(sha256sum "$nro" | cut -d ' ' -f1)" >"$out/host-events.txt"
ready=no
for ((i=0;i<300;++i));do
  if [[ -f "$manual" && -f "$driving" && -f "$guest" ]];then ready=yes;break;fi
  sleep 0.10
done
printf 'guest_sd_witness_files_ready=%s\n' "$ready" >>"$out/host-events.txt"
[[ "$ready" == yes ]] || { echo "INCONCLUSIVE: NRO did not initialize its own SD witness files" >&2;exit 1; }
win=""
for ((i=0;i<100;++i));do
  win="$(xdotool search --onlyvisible --name '[Nn]e[Xx]ium' 2>/dev/null | tail -n 1 || true)"
  [[ -n "$win" ]] && break
  sleep 0.10
done
[[ -n "$win" ]] || { echo "BLOCKED: NeXium GUI window not visible" >&2;exit 1; }
xdotool windowfocus --sync "$win"
sleep 0.35
focus="$(xdotool getwindowfocus 2>/dev/null || true)"
printf 'neXium_window=%s\nneXium_focused_window=%s\n' "$win" "$focus" >>"$out/host-events.txt"
[[ "$focus" == "$win" ]] || { echo "INCONCLUSIVE: NeXium did not receive keyboard focus" >&2;exit 1; }
capture_raw "screen-startup"
# Real Switch R+A chord (X11 E+C in the verified upstream key map).
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
[[ "$manual_entered" == yes ]] || { echo "INCONCLUSIVE: no NRO-owned manual entry witness" >&2;exit 1; }
# Real ZL+ZR+X driving-preview entry.
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
[[ "$entered" == yes ]] || { echo "INCONCLUSIVE: no NRO-owned driving entry witness" >&2;exit 1; }
# First fresh ZL+ZR+L edge starts the source-safe DEMO.
xdotool keydown r;xdotool keydown t;sleep 0.12;xdotool keydown q
first_started=no
for ((i=0;i<200;++i));do
  if [[ -f "$guest" ]] && [[ "$(wc -l <"$guest" | tr -d ' ')" -ge 6 ]] &&
     grep -q '^VPD_STAGE365_NUMERIC_DEMO_V2 event=on original_pair_start=519 ' "$guest";then
    first_started=yes;break
  fi
  sleep 0.03
done
[[ "$first_started" == yes ]] || { echo "INCONCLUSIVE: first real DEMO session did not produce six guest states" >&2;exit 1; }
capture_raw "screen-demo-start"
printf 'physical_keyboard_chord_start=R+T+Q Switch=ZL+ZR+L\n' >>"$out/host-events.txt"
# Release then send a fresh edge; this must cancel the active DEMO.
xdotool keyup q;xdotool keyup t;xdotool keyup r
xdotool keydown r;xdotool keydown t;sleep 0.07;xdotool keydown q;sleep 0.12
xdotool keyup q;xdotool keyup t;xdotool keyup r
printf 'physical_keyboard_chord_cancel=R+T+Q Switch=ZL+ZR+L\n' >>"$out/host-events.txt"
sleep 0.15
capture_raw "screen-cancelled"
first_count="$(wc -l <"$guest" | tr -d ' ')"
[[ "$first_count" -ge 6 && "$first_count" -le 16 ]] || {
  echo "INCONCLUSIVE: first DEMO was not cancelled before its terminal state" >&2;exit 1;
}
sleep 0.20
stable_count="$(wc -l <"$guest" | tr -d ' ')"
printf 'first_session_records=%s\nguest_trace_after_off_count=%s\n' "$first_count" "$stable_count" >>"$out/host-events.txt"
[[ "$stable_count" == "$first_count" ]] || {
  echo "INCONCLUSIVE: guest trace continued while DEMO was supposed to be off" >&2;exit 1;
}
echo 'guest_trace_stable_while_off=yes' >>"$out/host-events.txt"
echo 'cancel_screenshot_captured=yes' >>"$out/host-events.txt"
# A new physical edge must restart from numeric pair 519, not resume old pair.
xdotool keydown r;xdotool keydown t;sleep 0.12;xdotool keydown q
printf 'physical_keyboard_chord_restart=R+T+Q Switch=ZL+ZR+L\n' >>"$out/host-events.txt"
second_started=no
for ((i=0;i<200;++i));do
  if [[ "$(grep -c '^VPD_STAGE365_NUMERIC_DEMO_V2 event=on original_pair_start=519 ' "$guest" || true)" -ge 2 ]];then
    second_started=yes;break
  fi
  sleep 0.03
done
[[ "$second_started" == yes ]] || { echo "INCONCLUSIVE: fresh edge did not start a second session at pair 519" >&2;exit 1; }
capture_raw "screen-restart"
xdotool keyup q;xdotool keyup t;xdotool keyup r
expected=$((first_count+41))
complete=no
for ((i=0;i<300;++i));do
  count="$(wc -l <"$guest" | tr -d ' ')"
  starts="$(grep -c '^VPD_STAGE365_NUMERIC_DEMO_V2 event=on original_pair_start=519 ' "$guest" || true)"
  last="$(grep -c '^VPD_STAGE365_NUMERIC_DEMO_V2 event=last original_pair_start=559 ' "$guest" || true)"
  if [[ "$count" == "$expected" && "$starts" == 2 && "$last" == 1 ]];then complete=yes;break;fi
  sleep 0.06
done
printf 'second_session_records=%s\ntotal_guest_records=%s\n' "$((count-first_count))" "$count" >>"$out/host-events.txt"
[[ "$complete" == yes ]] || { echo "INCONCLUSIVE: restarted session did not complete exactly 41 guest states" >&2;exit 1; }
cp -- "$guest" "$out/guest-scroll-demo-v2.txt"
sha256sum "$out/guest-scroll-demo-v2.txt" >>"$out/host-events.txt"
echo 'STAGE371_REAL_NEXIUM_CANCEL_RESTART_OBSERVED' >>"$out/host-events.txt"
completed=yes
