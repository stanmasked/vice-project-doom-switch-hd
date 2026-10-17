#!/usr/bin/env bash
# Stage99: build a temporary, patched upstream FCEUX from a pinned revision.
# No ROM is loaded, no capture is performed, and no binary is published.
set -euo pipefail

PIN="8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8"
: "${RUNNER_TEMP:?Expected GitHub Actions temporary directory}"
: "${GITHUB_WORKSPACE:?Expected GitHub Actions checked-out project}"
FCEUX="${RUNNER_TEMP}/fceux-stage99-source"
PATCH="${RUNNER_TEMP}/fceux-stage99-patch"
BUILD="${RUNNER_TEMP}/fceux-stage99-build"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "${SCRIPT_DIR}/.." && pwd)"
test "${PROJECT}" = "${GITHUB_WORKSPACE}"

# Fresh checkout and verify both commit and ppu.cpp Git blob.
test ! -e "${FCEUX}" && test ! -e "${PATCH}" && test ! -e "${BUILD}"
git init -q "${FCEUX}"
git -C "${FCEUX}" remote add origin https://github.com/TASEmulators/fceux.git
git -C "${FCEUX}" -c advice.detachedHead=false fetch --quiet --depth 1 origin "${PIN}"
git -C "${FCEUX}" -c advice.detachedHead=false checkout -q --detach FETCH_HEAD
test "$(git -C "${FCEUX}" rev-parse HEAD)" = "${PIN}"
python3 "${PROJECT}/tools/audit_fceux_native_ppu_hook_sites.py" \
  "${FCEUX}/src/ppu.cpp" --require-exact-blob

python3 "${PROJECT}/tools/build_fceux_newppu_probe_patch.py" \
  "${FCEUX}/src/ppu.cpp" "${PATCH}"
test -f "${PATCH}/src/ppu.cpp"
test -f "${PATCH}/src/vpd_newppu_raw_step_probe.h"
python3 "${PROJECT}/tools/inject_fceux_vblank_status_probe.py" \
  "${FCEUX}/src/ppu.cpp" "${PATCH}/src/ppu.cpp" "${PATCH}/src/ppu_stage102.cpp"
cp "${PATCH}/src/ppu_stage102.cpp" "${FCEUX}/src/ppu.cpp"
cp "${PATCH}/src/vpd_newppu_raw_step_probe.h" "${FCEUX}/src/vpd_newppu_raw_step_probe.h"

# A real native PPU translation-unit change must be present and compile-guarded.
# Upstream ppu.cpp uses CRLF; Git must not mistake CR as trailing whitespace.
git -C "${FCEUX}" -c core.whitespace=cr-at-eol diff --check
git -C "${FCEUX}" diff -- src/ppu.cpp | grep -q 'vpd_ppu_probe::observe'
grep -q '^#ifdef VPD_NATIVE_RAW_PPU_PROBE' "${FCEUX}/src/ppu.cpp"

# Produce and link the real FCEUX executable, not only a stand-alone stub.
# Probe is explicitly enabled in this temporary build. No sink is installed.
cmake -S "${FCEUX}" -B "${BUILD}" \
  -DQT=5 -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-DVPD_NATIVE_RAW_PPU_PROBE -DVPD_NATIVE_SYNTHETIC_SMOKE -DVPD_NATIVE_SYNTHETIC_VBLANK" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "${BUILD}" --target fceux --parallel 2
test -x "${BUILD}/src/fceux"
file "${BUILD}/src/fceux"
python3 "${PROJECT}/tools/run_stage100_fceux_synthetic_smoke.py" \
  "${BUILD}/src/fceux" "${RUNNER_TEMP}"
# Independent X11 virtual framebuffer, not Qt offscreen/SDL dummy.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "${PROJECT}/tools/run_stage100_fceux_synthetic_smoke.py" \
    "${BUILD}/src/fceux" "${RUNNER_TEMP}" --backend xvfb
# Stage102: independent native source status transitions, on synthetic ROM.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "${PROJECT}/tools/run_stage102_native_status_window.py" \
    "${BUILD}/src/fceux" "${RUNNER_TEMP}"
printf 'STAGE99_PINNED_FCEUX_NATIVE_BUILD_PASS commit=%s opt_in_probe=yes real_fceux_linked=yes gameplay_raster_verified=no\n' "${PIN}"
