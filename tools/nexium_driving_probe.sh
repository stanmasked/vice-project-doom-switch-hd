#!/usr/bin/env bash
# Stage 163 independent second NeXium process: no modification to the
# existing long four-run platform/manual/FX input transcript.
set -euo pipefail
if [[ $# -ne 3 ]]; then
  echo "Usage: nexium_driving_probe.sh emulator nro out" >&2
  exit 2
fi
emulator="$1"; nro="$2"; out="$3"
mkdir -p "$out"
timeout --signal=TERM --kill-after=5s 90s "$emulator" "$nro" \
  > "$out/emulator-stdout.txt" 2>&1 &
emu_pid=$!
cleanup() {
  kill "$emu_pid" 2>/dev/null || true
  wait "$emu_pid" 2>/dev/null || true
}
trap cleanup EXIT
file="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/driving_guest.txt"
wait_for_event() {
  local seq="$1" event="$2" observed=no
  for (( i=0; i<260; ++i )); do
    if [[ -f "$file" ]] &&
       grep -q "^VPD_DRIVING_GUEST_V1 seq=$seq event=$event " "$file"; then
      observed=yes
      break
    fi
    sleep 0.07
  done
  printf 'native_event_%s=%s\n' "$event" "$observed" >> "$out/host-input.txt"
  [[ "$observed" == yes ]]
}
capture() {
  local name="$1"
  xwd -root -screen -silent -out "$out/$name.xwd"
  convert "$out/$name.xwd" -depth 8 -define ppm:format=raw "ppm:$out/$name.ppm"
  convert "$out/$name.xwd" -strip "png:$out/$name.png"
}
sleep 10
win="$(xdotool search --onlyvisible --name '[Nn]e[Xx]ium' | tail -n 1)"
[[ -n "$win" ]] || { echo "BLOCKED: no NeXium window" >&2; exit 1; }
xdotool windowfocus "$win"
# Known NeXium defaults, cross-checked against its public controller_config.rs:
# E=R, C=A, D=Right, A=Left, X=B, R=ZL, T=ZR, V=X, M=Plus.
xdotool keydown --clearmodifiers e
sleep 0.2
xdotool key --clearmodifiers --delay 150 c
xdotool keyup e
sleep 0.2
toggle_drive() {
  xdotool keydown --clearmodifiers r
  xdotool keydown --clearmodifiers t
  sleep 0.12
  xdotool key --clearmodifiers --delay 150 v
  sleep 0.15
  xdotool keyup t
  xdotool keyup r
}
toggle_drive
wait_for_event 1 enter
# These keys must produce *state changes inside the guest*, not merely X11.
xdotool keydown --clearmodifiers d
xdotool keydown --clearmodifiers c
wait_for_event 2 right_throttle
xdotool keyup c
xdotool keyup d
sleep 0.18
capture screen-drive-right
xdotool keydown --clearmodifiers a
xdotool keydown --clearmodifiers x
wait_for_event 3 left_brake
xdotool keyup x
xdotool keyup a
sleep 0.18
capture screen-drive-left
# Return to the centered obstacle's AABB, build enough forward speed,
# and await the actual 5->4 HP guest tick; no host-side HP manipulation.
xdotool keydown --clearmodifiers c
sleep 0.65
xdotool keyup c
wait_for_event 4 impact
sleep 0.16
capture screen-drive-impact
toggle_drive
wait_for_event 5 exit
sleep 0.20
capture screen-drive-exit
cp "$file" "$out/guest-driving-witness.txt"
xdotool key --clearmodifiers --delay 130 m
echo "host_probe=completed guest_five_events=yes" >> "$out/host-input.txt"
