#!/usr/bin/env bash
# Runs INSIDE Xvfb against the actual NeXium executable, not a stub.
set -euo pipefail
if [[ $# -ne 3 ]]; then echo "Usage: visual_probe.sh emulator nro evidence-dir" >&2; exit 2; fi
emulator="$1"; nro="$2"; out="$3"
mkdir -p "$out"
echo "visual_probe=started" > "$out/visual-probe.txt"
timeout --signal=TERM --kill-after=5s 225s \
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
    # A short single-shot probe avoids killing the optional guard before
    # the later genuine right-input contact encounter. Still require guest
    # Fire event/shot count, never the host keystroke alone.
    xdotool keydown --clearmodifiers z
    sleep 0.20
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
    # NeXium's controller_config.rs defaults T=ZR, D=left-stick right.
    # Distinct guest SD evidence, NOT this host input log, proves the dash.
    xdotool keydown --clearmodifiers d
    sleep 0.1
    xdotool keydown --clearmodifiers t
    sleep 0.6
    xdotool keyup t
    # Keep Right continuously pressed after releasing ZR. Previous CI
    # observed the guard first alerting at frame 133 under input=0 during
    # the idle keyup/sleep gap, which correctly invalidated the native
    # strict live-contact witness. Do not fake or relax the guard alert:
    # ensure the real pad supplies Right when the guard detects the hero.
    echo "host_dash_probe_sent=yes keys=D+T expected=ZR+Right" >> "$out/input-probe.txt"
    # The same held Right now drives the visible, pad-controlled guard to
    # first melee contact; do not send a duplicate keydown or idle gap.
    live_guard_path="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/guard_live_witness.txt"
    saw_strike=no
    for (( attempt=0; attempt<165; ++attempt )); do
      if [[ -f "$live_guard_path" ]] &&
         grep -q '^VPD_ROMFREE_GUARD_LIVE_V1 seq=2 event=strike ' "$live_guard_path"; then
        saw_strike=yes
        break
      fi
      sleep 0.05
    done
    xdotool keyup d
    sleep 0.1
    echo "host_guard_live_move_sent=yes key=D until_guest_strike=$saw_strike" >> "$out/input-probe.txt"
    if [[ "$saw_strike" == yes ]]; then
      # Allow the native framebuffer to present the reported melee state.
      # Capture a *real* X11 raster, not a software-generated rendering.
      sleep 0.12
      capture screen-live-strike
      echo "live_raster_strike_after_guest_event=yes" >> "$out/visual-probe.txt"
      # Keep the preceding one-shot control test unchanged.
      xdotool keydown --clearmodifiers z
      sleep 1.6
      xdotool keyup z
      echo "host_guard_live_fire_sent=yes key=Z after_guest_strike=yes" >> "$out/input-probe.txt"
      live_defeat_path="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/guard_live_defeat_witness.txt"
      saw_defeat=no
      for (( attempt=0; attempt<20; ++attempt )); do
        if [[ -f "$live_defeat_path" ]] &&
           grep -q '^VPD_ROMFREE_GUARD_LIVE_DEFEAT_V1 seq=[234] event=defeat ' "$live_defeat_path"; then
          saw_defeat=yes
          break
        fi
        sleep 0.05
      done
      if [[ "$saw_defeat" == yes ]]; then
        sleep 0.12
        capture screen-live-defeat
        echo "live_raster_defeat_after_guest_event=yes" >> "$out/visual-probe.txt"
      fi
      echo "host_guard_live_defeat_observed=$saw_defeat" >> "$out/input-probe.txt"
      # Next genuinely manual encounter: continue the SAME running game by
      # pressing Right+Fire, until the native guest itself reports the exit.
      # No offscreen source-script evidence may satisfy this condition.
      if [[ "$saw_defeat" == yes ]]; then
        live_wave_path="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/second_wave_live_witness.txt"
        saw_live_wave=no
        saw_live_exit=no
        xdotool keydown --clearmodifiers d
        # Advance using real Right control until the guest reports crossing
        # the wave gate. Do not fire early into distant dummy targets.
        for (( attempt=0; attempt<150; ++attempt )); do
          if [[ -f "$live_wave_path" ]] &&
             grep -q '^VPD_ROMFREE_WAVE2_LIVE_V1 seq=1 event=wave ' "$live_wave_path"; then
            saw_live_wave=yes
            break
          fi
          sleep 0.05
        done
        echo "host_second_wave_gate_sent=yes key=D guest_wave=$saw_live_wave" >> "$out/input-probe.txt"
        if [[ "$saw_live_wave" == yes ]]; then
          xdotool keydown --clearmodifiers z
          for (( attempt=0; attempt<650; ++attempt )); do
            if [[ -f "$live_wave_path" ]] &&
               grep -q '^VPD_ROMFREE_WAVE2_LIVE_V1 seq=5 event=exit ' "$live_wave_path"; then
              saw_live_exit=yes
              break
            fi
            sleep 0.05
          done
          xdotool keyup z
        fi
        xdotool keyup d
        echo "host_second_wave_controls_sent=yes keys=D+Z guest_exit=$saw_live_exit" >> "$out/input-probe.txt"
        if [[ "$saw_live_exit" == yes ]]; then
          sleep 0.12
          capture screen-live-stage-clear
          echo "live_second_wave_exit_raster_after_guest_event=yes" >> "$out/visual-probe.txt"
          # NeXium controller_config.rs defaults N=Minus (retry).
          # Press only after the actual visible native guest-stage exit,
          # then independently wait for the guest-created state-reset record.
          xdotool keydown --clearmodifiers n
          sleep 0.22
          xdotool keyup n
          echo "host_manual_retry_key_sent=yes key=N expected=Minus" >> "$out/input-probe.txt"
          retry_guest_path="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/manual_retry_witness.txt"
          saw_retry=no
          for (( attempt=0; attempt<30; ++attempt )); do
            if [[ -f "$retry_guest_path" ]] &&
               grep -q '^VPD_ROMFREE_MANUAL_RETRY_V1 event=restart reason=victory ' "$retry_guest_path"; then
              saw_retry=yes
              break
            fi
            sleep 0.05
          done
          echo "host_manual_retry_guest_observed=$saw_retry" >> "$out/input-probe.txt"
          if [[ "$saw_retry" == yes ]]; then
            sleep 0.18
            capture screen-live-restart
            echo "live_manual_restart_raster_after_guest_event=yes" >> "$out/visual-probe.txt"
            # New, entirely separate guest-visible losing scenario: use
            # genuine Right input until its first source melee, release
            # Right, allow 4 more real guard blows and witness hero HP=0.
            defeat_path="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/live_defeat_retry_witness.txt"
            observed_contact=no
            observed_death=no
            observed_defeat_retry=no
            xdotool keydown --clearmodifiers d
            for (( attempt=0; attempt<240; ++attempt )); do
              if [[ -f "$defeat_path" ]] &&
                 grep -q '^VPD_ROMFREE_DEFEAT_RETRY_V1 seq=1 event=contact ' "$defeat_path"; then
                observed_contact=yes
                break
              fi
              sleep 0.05
            done
            xdotool keyup d
            echo "host_post_victory_guard_contact_sent=yes key=D observed=$observed_contact" >> "$out/input-probe.txt"
            if [[ "$observed_contact" == yes ]]; then
              for (( attempt=0; attempt<240; ++attempt )); do
                if [[ -f "$defeat_path" ]] &&
                   grep -q '^VPD_ROMFREE_DEFEAT_RETRY_V1 seq=2 event=death ' "$defeat_path"; then
                  observed_death=yes
                  break
                fi
                sleep 0.05
              done
              echo "host_guard_death_observed=$observed_death" >> "$out/input-probe.txt"
              if [[ "$observed_death" == yes ]]; then
                sleep 0.16
                capture screen-live-game-over
                echo "live_game_over_raster_after_guest_death=yes" >> "$out/visual-probe.txt"
                xdotool keydown --clearmodifiers n
                sleep 0.22
                xdotool keyup n
                echo "host_defeat_minus_key_sent=yes key=N expected=Minus" >> "$out/input-probe.txt"
                for (( attempt=0; attempt<35; ++attempt )); do
                  if [[ -f "$defeat_path" ]] &&
                     grep -q '^VPD_ROMFREE_DEFEAT_RETRY_V1 seq=3 event=restart ' "$defeat_path"; then
                    observed_defeat_retry=yes
                    break
                  fi
                  sleep 0.05
                done
                echo "host_defeat_retry_guest_observed=$observed_defeat_retry" >> "$out/input-probe.txt"
                if [[ "$observed_defeat_retry" == yes ]]; then
                  sleep 0.16
                  capture screen-live-defeat-restart
                  echo "live_defeat_replay_raster_after_guest_event=yes" >> "$out/visual-probe.txt"
                  # Test the *third* playthrough using actual Right input;
                  # a reset frame or an isolated source script is insufficient.
                  # The NRO must witness positive world-space displacement.
                  third_path="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/post_defeat_control_witness.txt"
                  third_seen=no
                  xdotool keydown --clearmodifiers d
                  for (( attempt=0; attempt<80; ++attempt )); do
                    if [[ -f "$third_path" ]] &&
                       grep -q '^VPD_ROMFREE_THIRD_RUN_V1 event=move ' "$third_path"; then
                      third_seen=yes
                      break
                    fi
                    sleep 0.05
                  done
                  xdotool keyup d
                  echo "host_third_run_control_sent=yes key=D guest_observed=$third_seen" >> "$out/input-probe.txt"
                  if [[ "$third_seen" == yes ]]; then
                    sleep 0.12
                    capture screen-live-third-run-move
                    echo "live_third_run_movement_raster_after_guest_event=yes" >> "$out/visual-probe.txt"
                    # Third-run combat: press actual Z=Y/Fire ONLY after
                    # the real restored hero moved. Release immediately
                    # upon native shot evidence so exactly one projectile
                    # is launched. Wait for the game's swept guard collision.
                    third_fire_path="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/post_defeat_fire_witness.txt"
                    third_fire_seen=no
                    third_hit_seen=no
                    xdotool keydown --clearmodifiers z
                    for (( attempt=0; attempt<100; ++attempt )); do
                      if [[ -f "$third_fire_path" ]] &&
                         grep -q '^VPD_ROMFREE_THIRD_FIRE_V1 seq=1 event=fire ' "$third_fire_path"; then
                        third_fire_seen=yes
                        break
                      fi
                      sleep 0.05
                    done
                    xdotool keyup z
                    echo "host_third_run_fire_sent=yes key=Z guest_fire=$third_fire_seen" >> "$out/input-probe.txt"
                    if [[ "$third_fire_seen" == yes ]]; then
                      for (( attempt=0; attempt<120; ++attempt )); do
                        if [[ -f "$third_fire_path" ]] &&
                           grep -q '^VPD_ROMFREE_THIRD_FIRE_V1 seq=2 event=impact ' "$third_fire_path"; then
                          third_hit_seen=yes
                          break
                        fi
                        sleep 0.05
                      done
                      echo "host_third_run_hit_observed=$third_hit_seen" >> "$out/input-probe.txt"
                      if [[ "$third_hit_seen" == yes ]]; then
                        sleep 0.10
                        capture screen-live-third-run-impact
                        echo "live_third_run_impact_raster_after_guest_event=yes" >> "$out/visual-probe.txt"
                        # Continue only after a true third-run first impact:
                        # hold Fire while source collision logic eliminates
                        # the same guard on its third actual swept hit.
                        clear_path="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/third_guard_clear_witness.txt"
                        saw_clear=no
                        xdotool keydown --clearmodifiers z
                        for (( attempt=0; attempt<180; ++attempt )); do
                          if [[ -f "$clear_path" ]] &&
                             grep -q '^VPD_ROMFREE_THIRD_GUARD_CLEAR_V1 event=guard_clear ' "$clear_path"; then
                            saw_clear=yes
                            break
                          fi
                          sleep 0.05
                        done
                        xdotool keyup z
                        echo "host_third_guard_clear_sent=yes key=Z observed=$saw_clear" >> "$out/input-probe.txt"
                        if [[ "$saw_clear" == yes ]]; then
                          sleep 0.12
                          capture screen-live-third-guard-clear
                          echo "live_third_guard_clear_raster_after_guest_event=yes" >> "$out/visual-probe.txt"
                          # New playable third attempt must actually beat
                          # the second wave, not merely kill the first guard.
                          third_stage_path="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/third_stage_witness.txt"
                          third_wave=no
                          third_exit=no
                          xdotool keydown --clearmodifiers d
                          for (( attempt=0; attempt<260; ++attempt )); do
                            if [[ -f "$third_stage_path" ]] &&
                               grep -q '^VPD_ROMFREE_THIRD_STAGE_V1 seq=1 event=wave ' "$third_stage_path"; then
                              third_wave=yes
                              break
                            fi
                            sleep 0.05
                          done
                          echo "host_third_stage_gate_sent=yes key=D observed=$third_wave" >> "$out/input-probe.txt"
                          if [[ "$third_wave" == yes ]]; then
                            xdotool keydown --clearmodifiers z
                            for (( attempt=0; attempt<650; ++attempt )); do
                              if [[ -f "$third_stage_path" ]] &&
                                 grep -q '^VPD_ROMFREE_THIRD_STAGE_V1 seq=2 event=exit ' "$third_stage_path"; then
                                third_exit=yes
                                break
                              fi
                              sleep 0.05
                            done
                            xdotool keyup z
                          fi
                          xdotool keyup d
                          echo "host_third_stage_exit_sent=yes keys=D+Z observed=$third_exit" >> "$out/input-probe.txt"
                          if [[ "$third_exit" == yes ]]; then
                            sleep 0.14
                            capture screen-live-third-stage-clear
                            echo "live_third_stage_clear_raster_after_guest_event=yes" >> "$out/visual-probe.txt"
                            # Fourth independent native attempt: actual Minus
                            # after the THIRD earned stage victory, then Right.
                            fourth_path="$XDG_CONFIG_HOME/NeXium/sdmc/switch/vice_project_doom/fourth_retry_witness.txt"
                            fourth_restarted=no
                            fourth_moved=no
                            xdotool keydown --clearmodifiers n
                            sleep 0.22
                            xdotool keyup n
                            for (( attempt=0; attempt<70; ++attempt )); do
                              if [[ -f "$fourth_path" ]] &&
                                 grep -q '^VPD_ROMFREE_FOURTH_RETRY_V1 seq=1 event=restart ' "$fourth_path"; then
                                fourth_restarted=yes
                                break
                              fi
                              sleep 0.05
                            done
                            echo "host_fourth_retry_minus_sent=yes key=N guest_restart=$fourth_restarted" >> "$out/input-probe.txt"
                            if [[ "$fourth_restarted" == yes ]]; then
                              sleep 0.14
                              capture screen-live-fourth-restart
                              xdotool keydown --clearmodifiers d
                              for (( attempt=0; attempt<110; ++attempt )); do
                                if [[ -f "$fourth_path" ]] &&
                                   grep -q '^VPD_ROMFREE_FOURTH_RETRY_V1 seq=2 event=move ' "$fourth_path"; then
                                  fourth_moved=yes
                                  break
                                fi
                                sleep 0.05
                              done
                              xdotool keyup d
                              echo "host_fourth_retry_right_sent=yes key=D guest_move=$fourth_moved" >> "$out/input-probe.txt"
                              if [[ "$fourth_moved" == yes ]]; then
                                sleep 0.12
                                capture screen-live-fourth-move
                                echo "live_fourth_movement_raster_after_guest_event=yes" >> "$out/visual-probe.txt"
                              fi
                            fi
                          fi
                        fi
                      fi
                    fi
                  fi
                fi
              fi
            fi
          fi
        fi
      fi
    fi
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
  echo "timeout_wrapper_alive_after_plus_trial=yes" >> "$out/input-probe.txt"
else
  echo "timeout_wrapper_alive_after_plus_trial=no" >> "$out/input-probe.txt"
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
