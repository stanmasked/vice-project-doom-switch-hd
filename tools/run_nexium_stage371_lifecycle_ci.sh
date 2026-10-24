#!/usr/bin/env bash
# Stage372 real NeXium cancel/restart/terminal-off run. The guest NRO is ROM-free.
set -euo pipefail
[[ $# -eq 2 ]] || { echo "Usage: $0 guest.nro output-dir" >&2;exit 2; }
nro="$(realpath "$1")"; out="$(realpath -m "$2")"
mkdir -p "$out"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
release="https://github.com/nexium-emu/nexium-nightly/releases/download/nightly/nexium-linux-x86_64.tar.gz"
api="https://api.github.com/repos/nexium-emu/nexium-nightly/releases/tags/nightly"
sha256sum "$nro" >"$out/guest-nro-sha256.txt"
curl -fLsS --retry 3 --connect-timeout 20 --max-time 240 "$release" -o "$scratch/nexium.tar.gz"
curl -fLsS --retry 3 --connect-timeout 20 --max-time 60 \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" "$api" -o "$scratch/release.json"
python3 tools/verify_nexium_release.py --release-json "$scratch/release.json" \
  --archive "$scratch/nexium.tar.gz" \
  --out "$out/neXium-release-attestation.txt" >"$out/release-verification.txt"
mkdir -p "$scratch/unpacked"
tar -xzf "$scratch/nexium.tar.gz" -C "$scratch/unpacked" --no-same-owner
emulator="$(find "$scratch/unpacked" -type f \( -name 'nexium-gui' -o -name 'nexium' \) -print -quit)"
[[ -n "$emulator" ]] || { echo "BLOCKED: no NeXium GUI executable" >&2;exit 1; }
chmod +x "$emulator"
export LIBGL_ALWAYS_SOFTWARE=1
driver="$(find /usr/share/vulkan/icd.d -maxdepth 1 -name '*lvp*json' -type f -print -quit 2>/dev/null || true)"
if [[ -n "$driver" ]];then export VK_ICD_FILENAMES="$driver";else unset VK_ICD_FILENAMES;fi
export WGPU_BACKEND=vulkan GDK_BACKEND=x11 NEXIUM_VIDEO_FFMPEG=0
export XDG_CONFIG_HOME="$out/xdg-config" XDG_DATA_HOME="$out/xdg-data"
export XDG_CACHE_HOME="$out/xdg-cache" HOME="$out/home"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$HOME"
xvfb-run -a -s "-screen 0 1280x720x24" \
  bash tools/nexium_stage371_lifecycle_probe.sh "$emulator" "$nro" "$out"
python3 tools/audit_nexium_stage371_lifecycle.py \
  --evidence "$out" --output "$out/stage372-lifecycle-verdict.json"
echo "STAGE372_NEXIUM_REAL_CANCEL_RESTART_TERMINAL_OFF_PASS"
