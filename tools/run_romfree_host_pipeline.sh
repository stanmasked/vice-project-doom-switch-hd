#!/usr/bin/env bash
# Native, ROM-free host validation of the actual checked-out repository.
# No Nintendo Switch SDK, original ROM, original screenshots or game assets.
set -euo pipefail
if [[ $# -gt 1 || (${1:-} != "" && ${1:-} != "--core-only") ]]; then
  printf 'Usage: %s [--core-only]\n' "$0" >&2
  exit 2
fi

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
mode="${1:-all}"
# Keep all generated files within the ignored build tree. No commercial
# game data are fetched, opened or uploaded.
build_root="${VPD_HOST_BUILD_DIR:-$root/build/romfree_host_validation}"
cmake_cmd="${VPD_HOST_CMAKE:-cmake}"
ctest_cmd="${VPD_HOST_CTEST:-ctest}"
case "$build_root" in
  /|"$root"|"$root/"|"$root/."|"$root/..")
    echo "Refusing unsafe build output path" >&2; exit 2 ;;
esac

require_ctest() {
  local build="$1" name="$2" listing
  listing="$("$ctest_cmd" --test-dir "$build" -N)"
  if ! grep -Fq "$name" <<< "$listing"; then
    printf 'Required ROM-free test not registered: %s\n' "$name" >&2
    exit 1
  fi
}

printf 'ROM-free host source root: %s\n' "$root"
"$cmake_cmd" -S "$root/game_core" -B "$build_root/game_core" \
  -DCMAKE_BUILD_TYPE=Release
"$cmake_cmd" --build "$build_root/game_core" --parallel 2
for name in deterministic_simulation romfree_combat_replay \
            romfree_combat_replay_csv romfree_combat_replay_invalid \
            romfree_combat_full_trace romfree_combat_matrix; do
  require_ctest "$build_root/game_core" "$name"
done
"$ctest_cmd" --test-dir "$build_root/game_core" --output-on-failure
python3 "$root/tools/audit_romfree_combat_trace.py" \
  --binary "$build_root/game_core/vpd_combat_replay"

if [[ "$mode" != "--core-only" ]]; then
  "$cmake_cmd" -S "$root/graphics_core" -B "$build_root/graphics_core" \
    -DCMAKE_BUILD_TYPE=Release
  "$cmake_cmd" --build "$build_root/graphics_core" --parallel 2
  for name in scene_renderer_unit game_to_graphics_integration \
              romfree_combat_to_raster_integration; do
    require_ctest "$build_root/graphics_core" "$name"
  done
  "$ctest_cmd" --test-dir "$build_root/graphics_core" --output-on-failure
fi
printf 'VPD_ROMFREE_HOST_PIPELINE_PASS scope=%s synthetic_only=yes switch_runtime_proven=no original_game_proven=no\n' "$mode"
