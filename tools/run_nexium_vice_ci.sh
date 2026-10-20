#!/usr/bin/env bash
# NeXium native Switch NRO smoke test. No commercial ROM or firmware.
# Validates the mutable upstream nightly against GitHub's published asset
# SHA-256, size, asset ID and release URL; records identity for reproducibility.
set -euo pipefail
if [[ "$#" -ne 2 ]]; then
  echo "Usage: bash tools/run_nexium_vice_ci.sh app.nro evidence-directory" >&2
  exit 2
fi
nro="$(realpath "$1")"
out="$(realpath -m "$2")"
mkdir -p "$out"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
release="https://github.com/nexium-emu/nexium-nightly/releases/download/nightly/nexium-linux-x86_64.tar.gz"
release_api="https://api.github.com/repos/nexium-emu/nexium-nightly/releases/tags/nightly"
{
  echo "emulator=NeXium experimental nightly"
  echo "archive_url=$release"
  echo "release_metadata_url=$release_api"
  echo "nro_sha256=$(sha256sum "$nro" | cut -d ' ' -f 1)"
  echo "runner=$(uname -m)"
  echo "glibc=$(getconf GNU_LIBC_VERSION)"
} > "$out/metadata.txt"
if ! curl -fL --retry 3 --connect-timeout 20 --max-time 240 \
    "$release" -o "$scratch/nexium.tar.gz" > "$out/download.log" 2>&1; then
  echo "BLOCKED: emulator release download failed" > "$out/result.txt"
  exit 1
fi
# Fetch trusted publisher metadata *after* downloading the archive, to
# avoid silently treating the mutable nightly URL as an immutable binary.
# A release change during acquisition fails closed on digest/size mismatch.
if ! curl -fLsS --retry 3 --connect-timeout 20 --max-time 60 \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$release_api" -o "$scratch/release.json" > "$out/release-api.log" 2>&1; then
  echo "BLOCKED: official GitHub NeXium release metadata unavailable" > "$out/result.txt"
  exit 1
fi
if ! python3 tools/verify_nexium_release.py \
    --release-json "$scratch/release.json" \
    --archive "$scratch/nexium.tar.gz" \
    --out "$out/emulator-release-attestation.txt" > "$out/emulator-sha256.txt" 2>&1; then
  echo "BLOCKED: nightly archive fails official GitHub release digest attestation" > "$out/result.txt"
  exit 1
fi
cat "$out/emulator-release-attestation.txt" >> "$out/metadata.txt"
tar -tzf "$scratch/nexium.tar.gz" > "$out/archive-list.txt"
mkdir -p "$scratch/emulator"
tar -xzf "$scratch/nexium.tar.gz" -C "$scratch/emulator" --no-same-owner
emulator="$(find "$scratch/emulator" -type f \( -name 'nexium-gui' -o -name 'nexium' \) -print -quit)"
if [[ -z "$emulator" ]]; then
  echo "BLOCKED: downloaded archive has no emulator binary" > "$out/result.txt"
  exit 1
fi
chmod +x "$emulator"
echo "emulator_binary=$(basename "$emulator")" >> "$out/metadata.txt"
ldd "$emulator" > "$out/emulator-libraries.txt" 2>&1 || true
export LIBGL_ALWAYS_SOFTWARE=1
driver="$(find /usr/share/vulkan/icd.d -maxdepth 1 -name '*lvp*json' -type f -print -quit 2>/dev/null || true)"
if [[ -n "$driver" ]]; then
  export VK_ICD_FILENAMES="$driver"
  echo "vulkan_icd=$driver" >> "$out/metadata.txt"
else
  unset VK_ICD_FILENAMES
  echo "vulkan_icd=auto" >> "$out/metadata.txt"
fi
export WGPU_BACKEND=vulkan
export GDK_BACKEND=x11
export NEXIUM_VIDEO_FFMPEG=0
export XDG_DATA_HOME="$out/xdg-data"
export XDG_CONFIG_HOME="$out/xdg-config"
export XDG_CACHE_HOME="$out/xdg-cache"
export HOME="$out/emulator-home"
mkdir -p "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME"
vulkaninfo --summary > "$out/vulkan.txt" 2>&1 || true
# The NRO automatically plays a ROM-free scene. Capture real X11
# framebuffer pixels while the emulator runs; do not render mock screens.
# Guest state and host visual output are audited independently.
xvfb-run -a -s "-screen 0 1280x720x24" \
  bash tools/nexium_visual_probe.sh "$emulator" "$nro" "$out"
python3 tools/audit_nexium_vice_visual.py --evidence "$out"
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name demo_witness.txt -print > "$out/guest-trace-paths.txt"
if [[ -s "$out/guest-trace-paths.txt" ]]; then
  IFS= read -r guest < "$out/guest-trace-paths.txt"
  cp "$guest" "$out/guest-demo-witness.txt"
fi
python3 tools/audit_nexium_vice_witness.py --evidence "$out" --require-guest
# Separate guest-produced SD report for real input, effects and cleanup.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name manual_witness.txt -print > "$out/manual-trace-paths.txt"
if [[ -s "$out/manual-trace-paths.txt" ]]; then
  IFS= read -r guest < "$out/manual-trace-paths.txt"
  cp "$guest" "$out/guest-manual-witness.txt"
fi
python3 tools/audit_nexium_vice_manual.py --evidence "$out"
# Host X11/process status is a separate, conservative diagnostic; it must
# not substitute for the seven verified guest input/cleanup events.
python3 tools/audit_nexium_gui_lifecycle.py --evidence "$out"
# NeXium kernel logs, not window state or guest SD self-report, establish
# whether the guest svcExitProcess completed and the runner stopped its cores.
python3 tools/audit_nexium_guest_process_exit.py --evidence "$out"
# Validate a separate SD trace written by the actual guest gameplay loop.
# Host keyboard injection and hand-authored fixtures cannot replace this.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name dash_witness.txt -print > "$out/dash-trace-paths.txt"
if [[ -s "$out/dash-trace-paths.txt" ]]; then
  IFS= read -r guest < "$out/dash-trace-paths.txt"
  cp "$guest" "$out/guest-dash-witness.txt"
fi
python3 tools/audit_nexium_dash_guest.py --evidence "$out"
# A second optional game-system witness: actual first and eighth patrol
# steps were produced by the guest enemy simulation in manual mode.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name guard_witness.txt -print > "$out/guard-trace-paths.txt"
if [[ -s "$out/guard-trace-paths.txt" ]]; then
  IFS= read -r guest < "$out/guard-trace-paths.txt"
  cp "$guest" "$out/guest-guard-witness.txt"
fi
python3 tools/audit_nexium_guard_guest.py --evidence "$out"
# Isolated source-shared guard detection / contact / bullet-hit probe, run by
# the NRO itself, not the host or on-screen manual input.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name guard_combat_witness.txt -print > "$out/guard-combat-trace-paths.txt"
if [[ -s "$out/guard-combat-trace-paths.txt" ]]; then
  IFS= read -r guest < "$out/guard-combat-trace-paths.txt"
  cp "$guest" "$out/guest-guard-combat-witness.txt"
fi
python3 tools/audit_nexium_guard_combat.py --evidence "$out"
# Forensics only; optional file MUST NOT be used as native PASS evidence.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name guard_live_debug.txt -print > "$out/guard-live-debug-paths.txt"
if [[ -s "$out/guard-live-debug-paths.txt" ]]; then
  IFS= read -r guest < "$out/guard-live-debug-paths.txt"
  cp "$guest" "$out/guest-guard-live-debug.txt"
fi
# Unlike the previous offscreen diagnostic, these two events arise from
# the visible manual game.tick(Input{pad}) instance after real X11 controls.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name guard_live_witness.txt -print > "$out/guard-live-trace-paths.txt"
if [[ -s "$out/guard-live-trace-paths.txt" ]]; then
  IFS= read -r guest < "$out/guard-live-trace-paths.txt"
  cp "$guest" "$out/guest-guard-live-witness.txt"
fi
python3 tools/audit_nexium_guard_live.py --evidence "$out"
# Same visible manual gameplay instance: actual post-contact Fire buttons,
# swept projectile hits, and enemy death, never the separate guest script.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name guard_live_defeat_witness.txt -print > "$out/guard-live-defeat-trace-paths.txt"
if [[ -s "$out/guard-live-defeat-trace-paths.txt" ]]; then
  IFS= read -r guest < "$out/guard-live-defeat-trace-paths.txt"
  cp "$guest" "$out/guest-guard-live-defeat-witness.txt"
fi
python3 tools/audit_nexium_guard_live_defeat.py --evidence "$out"
# Two actual X11 captures, aligned by native guest manual melee and defeat
# records, must show disappearance of the guard's alert-colored torso.
# Real screenshots complement but cannot replace guest state/exit audits.
python3 tools/audit_nexium_guard_live_raster.py --evidence "$out"
# Independent X11 probe of the NEW real-guard melee cooldown pips. Reuse
# source-verified strike/death PNG/P6 screenshots; no new gameplay actions.
python3 tools/audit_nexium_guard_cooldown_x11.py --evidence "$out"
# Source-triggered real X11 readiness glyph from the same first alert,
# before first authentic guard melee strike switches to cooldown pips.
python3 tools/audit_nexium_guard_ready_x11.py --evidence "$out"
# Same physical manual guard combat: passive libnx source marker when
# 12 genuine idle ticks naturally refill its melee 32->20 cooldown.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name guard_cooldown_refill_guest.txt -print > "$out/guard-refill-trace-paths.txt"
if [[ -s "$out/guard-refill-trace-paths.txt" ]]; then
  IFS= read -r guest < "$out/guard-refill-trace-paths.txt"
  cp "$guest" "$out/guest-guard-cooldown-refill-witness.txt"
fi
python3 tools/audit_nexium_guard_refill_x11.py --evidence "$out"
# Independent AArch64 guest script for guard gate + sentry hostile projectile
# + real player swept hits + level exit. Not keyboard-driven wave-two play.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name second_wave_witness.txt -print > "$out/second-wave-trace-paths.txt"
if [[ -s "$out/second-wave-trace-paths.txt" ]]; then
  IFS= read -r guest < "$out/second-wave-trace-paths.txt"
  cp "$guest" "$out/guest-second-wave-witness.txt"
fi
python3 tools/audit_nexium_second_wave.py --evidence "$out"
# Finally require *live controller-driven* wave-two progression. The separate
# guest-scripted proof above cannot substitute for this pad-input witness.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name second_wave_live_witness.txt -print > "$out/second-wave-live-trace-paths.txt"
if [[ -s "$out/second-wave-live-trace-paths.txt" ]]; then
  IFS= read -r guest < "$out/second-wave-live-trace-paths.txt"
  cp "$guest" "$out/guest-second-wave-live-witness.txt"
fi
# Diagnostic-only native position snapshots; available in failure artifacts
# even if the strict wave-two control audit subsequently fails.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name wave_exit_progress.txt -print > "$out/wave-exit-progress-paths.txt"
if [[ -s "$out/wave-exit-progress-paths.txt" ]]; then
  IFS= read -r guest < "$out/wave-exit-progress-paths.txt"
  cp "$guest" "$out/guest-wave-exit-progress.txt"
fi
python3 tools/audit_nexium_second_wave_live.py --evidence "$out"
# Separate positive proof that the *same pad-driven live NRO* accepts
# Minus after earned stage completion and resets to a clean first wave.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name manual_retry_witness.txt -print > "$out/manual-retry-trace-paths.txt"
if [[ -s "$out/manual-retry-trace-paths.txt" ]]; then
  IFS= read -r guest < "$out/manual-retry-trace-paths.txt"
  cp "$guest" "$out/guest-manual-retry-witness.txt"
fi
python3 tools/audit_nexium_manual_retry.py --evidence "$out"
# Independent real pad-controlled *second* playthrough: guard kills the
# hero after the first victory restart, and real Minus starts a third run.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name live_defeat_retry_witness.txt -print > "$out/live-defeat-retry-paths.txt"
if [[ -s "$out/live-defeat-retry-paths.txt" ]]; then
  IFS= read -r guest < "$out/live-defeat-retry-paths.txt"
  cp "$guest" "$out/guest-live-defeat-retry-witness.txt"
fi
python3 tools/audit_nexium_defeat_retry.py --evidence "$out"
# Separate passive HP2 third-strike witness plus native X11 warning in
# the SAME second playthrough, before the already proved guard death.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name hd_low_health_guest.txt -print > "$out/hd-low-health-paths.txt"
if [[ -s "$out/hd-low-health-paths.txt" ]]; then
  IFS= read -r guest < "$out/hd-low-health-paths.txt"
  cp "$guest" "$out/guest-hd-low-health-witness.txt"
fi
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name hd_low_health_phase_guest.txt -print > "$out/hd-low-health-phase-paths.txt"
if [[ -s "$out/hd-low-health-phase-paths.txt" ]]; then
  IFS= read -r guest < "$out/hd-low-health-phase-paths.txt"
  cp "$guest" "$out/guest-hd-low-health-phase-witness.txt"
fi
python3 tools/audit_nexium_hd_low_health.py --evidence "$out"
# The same native screenshots must show warning ON, then OFF at unchanged
# HP2, no warning after real guard death, and no warning after Minus HP5.
python3 tools/audit_nexium_hd_low_health_lifecycle.py --evidence "$out"
# After the two genuinely completed terminal retries, confirm that a third
# attempt is still pad-controlled in the SAME visible NRO process.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name post_defeat_control_witness.txt -print > "$out/post-defeat-control-paths.txt"
if [[ -s "$out/post-defeat-control-paths.txt" ]]; then
  IFS= read -r guest < "$out/post-defeat-control-paths.txt"
  cp "$guest" "$out/guest-post-defeat-control-witness.txt"
fi
python3 tools/audit_nexium_third_run_control.py --evidence "$out"
# Last check: the restored third attempt must create a genuine source
# projectile and produce its first swept guard HP=3->2 impact under X11.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name post_defeat_fire_witness.txt -print > "$out/post-defeat-fire-paths.txt"
if [[ -s "$out/post-defeat-fire-paths.txt" ]]; then
  IFS= read -r guest < "$out/post-defeat-fire-paths.txt"
  cp "$guest" "$out/guest-post-defeat-fire-witness.txt"
fi
python3 tools/audit_nexium_third_run_fire.py --evidence "$out"
# Native pad Fire must also finish the restored first guard's HP through
# two more actual swept projectile impacts, with an independent X11 frame.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name third_guard_clear_witness.txt -print > "$out/third-guard-clear-paths.txt"
if [[ -s "$out/third-guard-clear-paths.txt" ]]; then
  IFS= read -r guest < "$out/third-guard-clear-paths.txt"
  cp "$guest" "$out/guest-third-guard-clear-witness.txt"
fi
python3 tools/audit_nexium_third_guard_clear.py --evidence "$out"
# Second earned stage exit on the restored third attempt, through real
# X11 Right/Fire and native guest source. Not the first run's old proof.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name third_stage_witness.txt -print > "$out/third-stage-paths.txt"
if [[ -s "$out/third-stage-paths.txt" ]]; then
  IFS= read -r guest < "$out/third-stage-paths.txt"
  cp "$guest" "$out/guest-third-stage-witness.txt"
fi
python3 tools/audit_nexium_third_stage.py --evidence "$out"
# Four distinct manual runs. This native source record can appear only
# after third stage completion and real fourth-try Minus then Right.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name fourth_retry_witness.txt -print > "$out/fourth-retry-paths.txt"
if [[ -s "$out/fourth-retry-paths.txt" ]]; then
  IFS= read -r guest < "$out/fourth-retry-paths.txt"
  cp "$guest" "$out/guest-fourth-retry-witness.txt"
fi
python3 tools/audit_nexium_fourth_retry.py --evidence "$out"
# Additional unaltered fourth pad Right evidence: both un-dusted and
# dusted native framebuffer samples must come from the SAME move frame.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name hd_footstep_evidence.txt -print > "$out/hd-footstep-paths.txt"
if [[ -s "$out/hd-footstep-paths.txt" ]]; then
  IFS= read -r guest < "$out/hd-footstep-paths.txt"
  cp "$guest" "$out/guest-hd-footstep-witness.txt"
fi
python3 tools/audit_nexium_hd_footstep.py --evidence "$out"
# Fourth NRO iteration must also fire one source-spawned projectile and
# cause the first genuine 3->2 guard HP loss under actual X11 Fire input.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name fourth_combat_witness.txt -print > "$out/fourth-combat-paths.txt"
if [[ -s "$out/fourth-combat-paths.txt" ]]; then
  IFS= read -r guest < "$out/fourth-combat-paths.txt"
  cp "$guest" "$out/guest-fourth-combat-witness.txt"
fi
python3 tools/audit_nexium_fourth_combat.py --evidence "$out"
# Same exact real fourth guard hit, rendered twice on the live guest.
# This proves optional HD lighting changes real framebuffer pixels.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name hd_hit_light_evidence.txt -print > "$out/hd-hit-light-paths.txt"
if [[ -s "$out/hd-hit-light-paths.txt" ]]; then
  IFS= read -r guest < "$out/hd-hit-light-paths.txt"
  cp "$guest" "$out/guest-hd-hit-light-witness.txt"
fi
python3 tools/audit_nexium_hd_impact.py --evidence "$out"
# Require two more real swept hits in the same restored fourth run.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name fourth_guard_clear_witness.txt -print > "$out/fourth-guard-clear-paths.txt"
if [[ -s "$out/fourth-guard-clear-paths.txt" ]]; then
  IFS= read -r guest < "$out/fourth-guard-clear-paths.txt"
  cp "$guest" "$out/guest-fourth-guard-clear-witness.txt"
fi
python3 tools/audit_nexium_fourth_guard_clear.py --evidence "$out"
# A separate pair of real pad L+R edges must be sourced while this
# fourth guard is still alive after its first genuine projectile hit.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name hd_fx_combat_guest.txt -print > "$out/hd-fx-combat-paths.txt"
if [[ -s "$out/hd-fx-combat-paths.txt" ]]; then
  IFS= read -r guest < "$out/hd-fx-combat-paths.txt"
  cp "$guest" "$out/guest-hd-fx-combat-witness.txt"
fi
python3 tools/audit_nexium_hd_fx_combat.py --evidence "$out"

# Fourth earned victory is separate from the preceding third run.
# Require both native new source events and real X11 key/screen evidence.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name fourth_stage_witness.txt -print > "$out/fourth-stage-paths.txt"
if [[ -s "$out/fourth-stage-paths.txt" ]]; then
  IFS= read -r guest < "$out/fourth-stage-paths.txt"
  cp "$guest" "$out/guest-fourth-stage-witness.txt"
fi
python3 tools/audit_nexium_fourth_stage.py --evidence "$out"
# Live fourth-stage active turret shot, sampled twice without a source tick.
# Require the independently confirmed physical pad/X11 stage before PASS.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name hd_hostile_halo_witness.txt -print > "$out/hd-hostile-halo-paths.txt"
if [[ -s "$out/hd-hostile-halo-paths.txt" ]]; then
  IFS= read -r guest < "$out/hd-hostile-halo-paths.txt"
  cp "$guest" "$out/guest-hd-hostile-halo-witness.txt"
fi
python3 tools/audit_nexium_hd_hostile_halo.py --evidence "$out"
# Two physical L+R transitions must occur on the SAME first hostile bullet
# while the fourth wave is active. Preserve the old post-clear proof.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name hd_fx_sentry_guest.txt -print > "$out/hd-fx-sentry-paths.txt"
if [[ -s "$out/hd-fx-sentry-paths.txt" ]]; then
  IFS= read -r guest < "$out/hd-fx-sentry-paths.txt"
  cp "$guest" "$out/guest-hd-fx-sentry-witness.txt"
fi
python3 tools/audit_nexium_hd_fx_sentry.py --evidence "$out"
# The first source-confirmed hostile projectile must also be the one that
# actually damages the hero AFTER native L+R OFF/ON in the same guest run.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name hd_fx_sentry_hit_guest.txt -print > "$out/hd-fx-sentry-hit-paths.txt"
if [[ -s "$out/hd-fx-sentry-hit-paths.txt" ]]; then
  IFS= read -r guest < "$out/hd-fx-sentry-hit-paths.txt"
  cp "$guest" "$out/guest-hd-fx-sentry-hit-witness.txt"
fi
python3 tools/audit_nexium_hd_fx_sentry_hit.py --evidence "$out"
# On those exact authentic source-hit X11 frames require separate actor-body
# flash evidence; HUD changes or scenery bloom alone must not count.
python3 tools/audit_nexium_sentry_hero_impact.py --evidence "$out"
# A third native X11 capture must show the hero's authentic hit flash
# EXPIRED after 16 guest-owned idle simulation ticks (while HP remains 4).
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name hd_fx_sentry_recover_guest.txt -print > "$out/hd-fx-sentry-recover-paths.txt"
if [[ -s "$out/hd-fx-sentry-recover-paths.txt" ]]; then
  IFS= read -r guest < "$out/hd-fx-sentry-recover-paths.txt"
  cp "$guest" "$out/guest-hd-fx-sentry-recover-witness.txt"
fi
python3 tools/audit_nexium_sentry_hero_recovery.py --evidence "$out"
# Independent native HD-effects L+R gesture after fourth-run completion.
find "$HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" \
  -type f -name hd_fx_toggle_guest.txt -print > "$out/hd-fx-guest-paths.txt"
if [[ -s "$out/hd-fx-guest-paths.txt" ]]; then
  IFS= read -r guest < "$out/hd-fx-guest-paths.txt"
  cp "$guest" "$out/guest-hd-fx-toggle-witness.txt"
fi
python3 tools/audit_nexium_hd_fx_guest.py --evidence "$out"
