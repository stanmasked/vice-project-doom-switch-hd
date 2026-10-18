#!/usr/bin/env bash
# Runs INSIDE Xvfb against the actual NeXium executable, not a stub.
set -euo pipefail
if [[ $# -ne 3 ]]; then echo "Usage: visual_probe.sh emulator nro evidence-dir" >&2; exit 2; fi
emulator="$1"; nro="$2"; out="$3"
mkdir -p "$out"
echo "visual_probe=started" > "$out/visual-probe.txt"
timeout --signal=TERM --kill-after=5s 38s \
 "$emulator" "$nro" > "$out/emulator-stdout.txt" 2>&1 &
emu_pid=$!
# Root screenshots include the real native X11/Vulkan presentation child.
capture() {
  local label="$1"
  if ! kill -0 "$emu_pid" 2>/dev/null; then
    echo "CAPTURE_BLOCKED: emulator exited before $label" >> "$out/visual-probe.txt"
    return 1
  fi
  xwd -root -screen -silent -out "$out/$label.xwd"
  # ImageMagick -compress none selects ASCII P3 (not binary P6). Explicitly
  # require raw 8-bit P6, matching the independent strict visual auditor.
  convert "$out/$label.xwd" -depth 8 -define ppm:format=raw "ppm:$out/$label.ppm"
  convert "$out/$label.xwd" -strip "png:$out/$label.png"
  echo "capture=$label" >> "$out/visual-probe.txt"
}
sleep 9
xdotool search --onlyvisible --name '[Nn]e[Xx]ium' > "$out/ne-x11-windows.txt" 2>&1 || true
capture screen-before
sleep 10
capture screen-after
# QuackShot-proven NeXium keyboard defaults: E=R, C=A, D=right,
# Z=Y (fire), X=B (jump), A=left, M=Plus. A held under R is an
# explicit Vice test-only R+A mode switch. Only guest records are proof.
if [[ -s "$out/ne-x11-windows.txt" ]]; then
  win="$(tail -n 1 "$out/ne-x11-windows.txt")"
  if xdotool windowfocus "$win" >> "$out/input-probe.txt" 2>&1; then
    xdotool keydown --clearmodifiers e
    sleep 0.2
    xdotool key --clearmodifiers --delay 120 c
    xdotool keyup e
    sleep 0.45
    xdotool keydown --clearmodifiers d
    sleep 0.9
    xdotool keyup d
    sleep 0.3
    xdotool keydown --clearmodifiers z
    sleep 0.5
    xdotool keyup z
    sleep 0.4
    xdotool keydown --clearmodifiers x
    sleep 0.4
    xdotool keyup x
    sleep 0.35
    xdotool keydown --clearmodifiers a
    sleep 0.9
    xdotool keyup a
    sleep 0.3
    echo "host_manual_probe_sent=yes R+A/right/fire/jump/left" >> "$out/input-probe.txt"
    xdotool key --clearmodifiers --delay 150 m >> "$out/input-probe.txt" 2>&1 &&
      echo "host_plus_key_sent=yes" >> "$out/input-probe.txt"
  fi
else
  echo "host_manual_probe_sent=no window_not_found=yes" > "$out/input-probe.txt"
fi
sleep 3
# Inspect the original NeXium window independently of the timeout wrapper.
# Losing a window alone does NOT prove that the GUI process exited.
xdotool search --onlyvisible --name '[Nn]e[Xx]ium' > "$out/ne-x11-windows-after-plus.txt" 2>/dev/null || true
if [[ -n "${win:-}" ]]; then
  echo "target_window_before_plus=yes" > "$out/host-gui-lifecycle.txt"
  if grep -Fxq "$win" "$out/ne-x11-windows-after-plus.txt"; then
    echo "target_window_visible_after_plus=yes" >> "$out/host-gui-lifecycle.txt"
  else
    echo "target_window_visible_after_plus=no" >> "$out/host-gui-lifecycle.txt"
  fi
else
  echo "target_window_before_plus=no" > "$out/host-gui-lifecycle.txt"
  echo "target_window_visible_after_plus=unknown" >> "$out/host-gui-lifecycle.txt"
fi
if kill -0 "$emu_pid" 2>/dev/null; then
  echo "emulator_still_alive_after_plus_trial=yes" >> "$out/input-probe.txt"
else
  echo "emulator_still_alive_after_plus_trial=no" >> "$out/input-probe.txt"
fi
set +e
wait "$emu_pid"
rc=$?
set -e
echo "emulator_exit_code=$rc" >> "$out/metadata.txt"
echo "timeout_wrapper_wait_rc=$rc" >> "$out/host-gui-lifecycle.txt"
# timeout(1) returns 124 when it terminates its child on deadline.
# 137 can also represent a signal or an escalated watchdog kill.
case "$rc" in
  0)   echo "host_process_outcome=returned_zero" >> "$out/host-gui-lifecycle.txt" ;;
  124) echo "host_process_outcome=watchdog" >> "$out/host-gui-lifecycle.txt" ;;
  137) echo "host_process_outcome=signal_or_watchdog" >> "$out/host-gui-lifecycle.txt" ;;
  *)   echo "host_process_outcome=returned_nonzero" >> "$out/host-gui-lifecycle.txt" ;;
esac
echo "visual_probe=finished" >> "$out/visual-probe.txt"
# The guest state and screenshots, not process exit, decide whether this
# stage passed. Exit 137/124 means watchdog, not proof of guest crash.
exit 0
