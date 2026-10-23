#!/usr/bin/env bash
# Stage 315: independent NeXium process for a full automatic route completion.
# Uses real X11 pad input and source-owned guest state; never presses Minus.
set -euo pipefail
if [[ $# -ne 3 ]]; then
  echo "Usage: nexium_driving_route_probe.sh emulator nro out" >&2
  exit 2
fi
emulator="$1"; nro="$2"; out="$3"
mkdir -p "$out"
held_key=""
timeout --signal=TERM --kill-after=5s 170s "$emulator" "$nro" \
  > "$out/emulator-stdout.txt" 2>&1 &
emu_pid=$!
cleanup() {
  if [[ -n "${held_key:-}" ]]; then xdotool keyup "$held_key" 2>/dev/null || true; fi
  xdotool keyup a 2>/dev/null || true
  xdotool keyup d 2>/dev/null || true
  xdotool keyup c 2>/dev/null || true
  xdotool keyup x 2>/dev/null || true
  xdotool keyup n 2>/dev/null || true
  kill "$emu_pid" 2>/dev/null || true
  wait "$emu_pid" 2>/dev/null || true
}
trap cleanup EXIT
route_file="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/driving_route_guest.txt"
exit_file="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/driving_exit_guest.txt"
capture() {
  local name="$1"
  xwd -root -screen -silent -out "$out/$name.xwd"
  convert "$out/$name.xwd" -depth 8 -define ppm:format=raw "ppm:$out/$name.ppm"
  convert "$out/$name.xwd" -strip "png:$out/$name.png"
}
await_exit() {
  local seq="$1" scene="$2" found=no
  for (( check=0; check<240; ++check )); do
    if [[ -f "$exit_file" ]] &&
       grep -q "^VPD_DRIVING_EXIT_V1 seq=$seq scene=$scene " "$exit_file"; then
      found=yes
      break
    fi
    sleep 0.04
  done
  echo "native_transition_$scene=$found seq=$seq" >> "$out/host-route-input.txt"
  [[ "$found" == yes ]]
}

sleep 10
win="$(xdotool search --onlyvisible --name '[Nn]e[Xx]ium' | tail -n 1)"
[[ -n "$win" ]] || { echo "BLOCKED: no NeXium window" >&2; exit 1; }
xdotool windowfocus "$win"
# E=R and C=A enter manual platform mode; R+T+V toggles the road preview.
xdotool keydown --clearmodifiers e
sleep 0.2
xdotool key --clearmodifiers --delay 150 c
xdotool keyup e
sleep 0.2
xdotool keydown --clearmodifiers r
xdotool keydown --clearmodifiers t
sleep 0.12
xdotool key --clearmodifiers --delay 150 v
sleep 0.15
xdotool keyup t
xdotool keyup r
sleep 0.28
capture screen-exit-road

last_line=""
route_seen=no
start_seconds=$SECONDS
while (( SECONDS - start_seconds < 150 )); do
  if [[ -f "$route_file" ]]; then
    line="$(tail -n 1 "$route_file")"
    if [[ -n "$line" && "$line" != "$last_line" ]]; then
      last_line="$line"
      event=""; frame=""; car_x=""; obstacle_x=""; health=""
      throttle=""; brake=""; manual_exit=""; route_complete=""
      for token in $line; do
        case "$token" in
          event=*) event="${token#*=}" ;;
          frame=*) frame="${token#*=}" ;;
          car_x=*) car_x="${token#*=}" ;;
          obstacle_x=*) obstacle_x="${token#*=}" ;;
          health=*) health="${token#*=}" ;;
          throttle=*) throttle="${token#*=}" ;;
          brake=*) brake="${token#*=}" ;;
          manual_exit=*) manual_exit="${token#*=}" ;;
          route_complete=*) route_complete="${token#*=}" ;;
        esac
      done
      if [[ "$event" == "exit_request" ]]; then
        [[ "$manual_exit" == 0 && "$route_complete" == 1 ]] || {
          echo "BLOCKED: exit was not earned by route progress frame=$frame" >&2
          exit 1
        }
        route_seen=yes
        break
      fi
      if [[ "$event" == "sample" ]]; then
        [[ -n "$frame" && -n "$car_x" && -n "$obstacle_x" && -n "$health" ]] || {
          echo "BLOCKED: incomplete guest route telemetry" >&2
          exit 1
        }
        [[ "$health" -gt 0 && "$throttle" == 0 && "$brake" == 0 ]] || {
          echo "BLOCKED: route driver died or speed controls changed" >&2
          exit 1
        }
        case "$obstacle_x" in
          640|570) target=810 ;;
          710) target=560 ;;
          840) target=600 ;;
          440) target=700 ;;
          *) echo "BLOCKED: unknown obstacle lane $obstacle_x" >&2; exit 1 ;;
        esac
        delta=$((target-car_x))
        if (( delta > 25 )); then desired=d
        elif (( delta < -25 )); then desired=a
        else desired=none
        fi
        if [[ "$desired" != "$held_key" ]]; then
          if [[ -n "$held_key" ]]; then xdotool keyup "$held_key"; fi
          if [[ "$desired" != none ]]; then
            xdotool keydown --clearmodifiers "$desired"
            held_key="$desired"
          else
            held_key=""
          fi
        fi
      fi
    fi
  fi
  sleep 0.05
done
if [[ "$route_seen" != yes ]]; then
  echo "BLOCKED: automatic route exit not observed within 150 seconds" >&2
  exit 1
fi
if [[ -n "$held_key" ]]; then xdotool keyup "$held_key"; held_key=""; fi
echo "host_route_completion=observed manual_minus_sent=no" >> "$out/host-route-input.txt"
await_exit 0 last_road
await_exit 17 black
sleep 0.08
capture screen-exit-black
await_exit 41 black
await_exit 42 platform
sleep 0.16
capture screen-exit-platform
cp "$route_file" "$out/guest-driving-route-witness.txt"
cp "$exit_file" "$out/guest-driving-exit-witness.txt"
echo "VPD_NEXIUM_DRIVING_ROUTE_PROBE_PASS" >> "$out/host-route-input.txt"
