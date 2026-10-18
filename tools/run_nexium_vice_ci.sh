#!/usr/bin/env bash
# NeXium native Switch NRO smoke test. No commercial ROM or firmware.
# Uses the pinned public Linux emulator archive already verified in QuackShot CI.
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
# Reuse the digest of the identical Linux release proven by the QuackShot
# project on 2026-10-18. The nightly tag is mutable: if it changes, fail.
expected="0ec2da5d58b6b362a9f0a4c927af0e55d36a0b50d1ab3f035dd075ea12d76761"
{
  echo "emulator=NeXium experimental nightly"
  echo "archive_url=$release"
  echo "expected_archive_sha256=$expected"
  echo "nro_sha256=$(sha256sum "$nro" | cut -d ' ' -f 1)"
  echo "runner=$(uname -m)"
  echo "glibc=$(getconf GNU_LIBC_VERSION)"
} > "$out/metadata.txt"
if ! curl -fL --retry 3 --connect-timeout 20 --max-time 240 \
    "$release" -o "$scratch/nexium.tar.gz" > "$out/download.log" 2>&1; then
  echo "BLOCKED: emulator release download failed" > "$out/result.txt"
  exit 1
fi
if ! printf '%s  %s\n' "$expected" "$scratch/nexium.tar.gz" |
    sha256sum -c - > "$out/emulator-sha256.txt" 2>&1; then
  echo "BLOCKED: nightly archive changed; refusing unknown executable" > "$out/result.txt"
  exit 1
fi
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
