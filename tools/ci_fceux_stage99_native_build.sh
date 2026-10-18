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
# Stage128: verify source-level sprite compositor semantics at the pinned
# upstream revision, independent of our later synthetic PPU instrumentation.
python3 "${PROJECT}/tools/audit_fceux_stage128_sprite_compositor.py" \
  "${FCEUX}/src/ppu.cpp"
python3 "${PROJECT}/tools/audit_stage130_two_sprite_order.py" \
  "${FCEUX}/src/ppu.cpp"
python3 "${PROJECT}/tools/audit_stage132_sprite_flips.py" \
  "${FCEUX}/src/ppu.cpp"
python3 "${PROJECT}/tools/audit_stage136_oam_eight_limit.py" \
  "${FCEUX}/src/ppu.cpp"

python3 "${PROJECT}/tools/build_fceux_newppu_probe_patch.py" \
  "${FCEUX}/src/ppu.cpp" "${PATCH}"
test -f "${PATCH}/src/ppu.cpp"
test -f "${PATCH}/src/vpd_newppu_raw_step_probe.h"
python3 "${PROJECT}/tools/inject_fceux_vblank_status_probe.py" \
  "${FCEUX}/src/ppu.cpp" "${PATCH}/src/ppu.cpp" "${PATCH}/src/ppu_stage102.cpp"
python3 "${PROJECT}/tools/inject_fceux_ppustatus_read_probe.py" \
  "${FCEUX}/src/ppu.cpp" "${PATCH}/src/ppu_stage102.cpp" \
  "${PATCH}/src/ppu_stage103.cpp"
python3 "${PROJECT}/tools/inject_fceux_frame_preclear_probe.py" \
  "${FCEUX}/src/ppu.cpp" "${PATCH}/src/ppu_stage103.cpp" \
  "${PATCH}/src/ppu_stage105.cpp"
python3 "$PROJECT/tools/inject_fceux_stage107_bg_pixel_probe.py" \
  "$PATCH/src/ppu_stage105.cpp" "$PATCH/src/ppu_stage107.cpp"
python3 "$PROJECT/tools/inject_fceux_stage108_bg_fetch_probe.py" \
  "$PATCH/src/ppu_stage107.cpp" "$PATCH/src/ppu_stage108.cpp"
python3 "$PROJECT/tools/inject_fceux_stage110_raster_probe.py" \
  "$PATCH/src/ppu_stage108.cpp" "$PATCH/src/ppu_stage110.cpp"
python3 "$PROJECT/tools/inject_fceux_stage111_tile_probe.py" \
  "$PATCH/src/ppu_stage110.cpp" "$PATCH/src/ppu_stage111.cpp"
python3 "$PROJECT/tools/inject_fceux_stage113_prefetch_probe.py" \
  "$PATCH/src/ppu_stage111.cpp" "$PATCH/src/ppu_stage113.cpp"
python3 "$PROJECT/tools/inject_fceux_stage114_plane_pairs.py" \
  "$PATCH/src/ppu_stage113.cpp" "$PATCH/src/ppu_stage114.cpp"
python3 "$PROJECT/tools/inject_fceux_stage115_edge_carry.py" \
  "$PATCH/src/ppu_stage114.cpp" "$PATCH/src/ppu_stage115.cpp"
python3 "$PROJECT/tools/inject_fceux_stage116_fine_scroll.py" \
  "$PATCH/src/ppu_stage115.cpp" "$PATCH/src/ppu_stage116.cpp"
python3 "$PROJECT/tools/inject_fceux_stage117_dynamic_scroll.py" \
  "$PATCH/src/ppu_stage116.cpp" "$PATCH/src/ppu_stage117.cpp"
python3 "$PROJECT/tools/inject_fceux_stage118_two_scrolls.py" \
  "$PATCH/src/ppu_stage117.cpp" "$PATCH/src/ppu_stage118.cpp"
python3 "$PROJECT/tools/inject_fceux_stage119_nametable_pixels.py" \
  "$PATCH/src/ppu_stage118.cpp" "$PATCH/src/ppu_stage119.cpp"
python3 "$PROJECT/tools/inject_fceux_stage121_attributes.py" \
  "$PATCH/src/ppu_stage119.cpp" "$PATCH/src/ppu_stage121.cpp"
python3 "$PROJECT/tools/inject_fceux_stage124_quadrants.py" \
  "$PATCH/src/ppu_stage121.cpp" "$PATCH/src/ppu_stage124.cpp"
python3 "$PROJECT/tools/inject_fceux_stage129_sprite_compositor.py" \
  "$PATCH/src/ppu_stage124.cpp" "$PATCH/src/ppu_stage129.cpp"
python3 "$PROJECT/tools/inject_fceux_stage131_dual_sprite.py" \
  "$PATCH/src/ppu_stage129.cpp" "$PATCH/src/ppu_stage131.cpp"
python3 "$PROJECT/tools/inject_fceux_stage133_sprite_flips.py" \
  "$PATCH/src/ppu_stage131.cpp" "$PATCH/src/ppu_stage133.cpp"
python3 "$PROJECT/tools/inject_fceux_stage135_sprite_8x16.py" \
  "$PATCH/src/ppu_stage133.cpp" "$PATCH/src/ppu_stage135.cpp"
python3 "$PROJECT/tools/inject_fceux_stage137_nine_oam.py" \
  "$PATCH/src/ppu_stage135.cpp" "$PATCH/src/ppu_stage137.cpp"
cp "$PATCH/src/ppu_stage137.cpp" "$FCEUX/src/ppu.cpp"
python3 "${PROJECT}/tools/inject_fceux_mmc3_chr_probe.py" \
  "${FCEUX}/src/boards/mmc3.cpp" "${PATCH}/src/mmc3_stage106.cpp"
cp "${PATCH}/src/mmc3_stage106.cpp" "${FCEUX}/src/boards/mmc3.cpp"
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
  -DCMAKE_CXX_FLAGS="-DVPD_NATIVE_RAW_PPU_PROBE -DVPD_NATIVE_SYNTHETIC_SMOKE -DVPD_NATIVE_SYNTHETIC_VBLANK -DVPD_NATIVE_SYNTHETIC_PPUSTATUS_READ -DVPD_NATIVE_SYNTHETIC_EVENT_ORDER -DVPD_NATIVE_SYNTHETIC_PRECLEAR -DVPD_NATIVE_SYNTHETIC_MMC3_CHR -DVPD_NATIVE_SYNTHETIC_BG_PIXELS -DVPD_NATIVE_SYNTHETIC_BG_FETCH -DVPD_NATIVE_SYNTHETIC_CHR_TIMELINE -DVPD_NATIVE_SYNTHETIC_MIDFRAME_CHR -DVPD_NATIVE_SYNTHETIC_BG_TILES -DVPD_NATIVE_SYNTHETIC_BG_PREFETCH -DVPD_NATIVE_SYNTHETIC_BG_PLANE_PAIRS -DVPD_NATIVE_SYNTHETIC_SCANLINE_CARRY -DVPD_NATIVE_SYNTHETIC_FINE_SCROLL -DVPD_NATIVE_SYNTHETIC_DYNAMIC_SCROLL -DVPD_NATIVE_SYNTHETIC_TWO_SCROLLS -DVPD_NATIVE_SYNTHETIC_NAMETABLE_IDS -DVPD_NATIVE_SYNTHETIC_BG_ATTRIBUTES -DVPD_NATIVE_SYNTHETIC_QUADRANT_COLORS -DVPD_NATIVE_SYNTHETIC_SPRITE_COLLISION -DVPD_NATIVE_SYNTHETIC_DUAL_SPRITE -DVPD_NATIVE_SYNTHETIC_SPRITE_FLIPS -DVPD_NATIVE_SYNTHETIC_SPRITE_8X16" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build "${BUILD}" --target fceux --parallel 2
test -x "${BUILD}/src/fceux"
file "${BUILD}/src/fceux"
# Stage101: unstable dummy Qt/SDL driver is diagnostic only; it sometimes
# SIGSEGVs even though the very same binary passes under Xvfb/X11.
if python3 "${PROJECT}/tools/run_stage100_fceux_synthetic_smoke.py" \
    "${BUILD}/src/fceux" "${RUNNER_TEMP}"; then
  echo "STAGE102_DUMMY_BACKEND_DIAGNOSTIC status=completed"
else
  echo "STAGE102_DUMMY_BACKEND_DIAGNOSTIC status=unverified_early_exit"
fi
# Independent X11 virtual framebuffer, not Qt offscreen/SDL dummy.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "${PROJECT}/tools/run_stage100_fceux_synthetic_smoke.py" \
    "${BUILD}/src/fceux" "${RUNNER_TEMP}" --backend xvfb
# Stage102: independent native source status transitions, on synthetic ROM.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "${PROJECT}/tools/run_stage102_native_status_window.py" \
    "${BUILD}/src/fceux" "${RUNNER_TEMP}"
# Stage103: original synthetic 6502 repeatedly LDA $2002, proving real reads.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "${PROJECT}/tools/run_stage103_native_ppustatus_reads.py" \
    "${BUILD}/src/fceux" "${RUNNER_TEMP}"
# Stage104: same internal advancing runppu clock for source writes and CPU reads.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "${PROJECT}/tools/run_stage104_native_event_order.py" \
    "${BUILD}/src/fceux" "${RUNNER_TEMP}"
# Stage105: pre/post source frame clear correlated to CPU $2002 status reads.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "${PROJECT}/tools/run_stage105_native_frame_preclear.py" \
    "${BUILD}/src/fceux" "${RUNNER_TEMP}"
# Stage106: ROM-free original iNES mapper-4 CHR bank toggles ($8000/$8001).
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "${PROJECT}/tools/run_stage106_native_mmc3_chr.py" \
    "${BUILD}/src/fceux" "${RUNNER_TEMP}"
# Stage107: paired synthetic nonblank CHR banks and final framebuffer evidence.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage107_native_bg_pixels.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage108: same-run BG pattern fetch and framebuffer A/B evidence.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage108_native_bg_fetch.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage109: source-clock order for actual MMC3 write, BG CHR fetch, and pixels.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage109_native_chr_timeline.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage110: mid-frame CHR bank switch: same frame, two final framebuffer windows.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage110_native_midframe.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage111: actual buffered BG pattern bytes, same-frame XBuf and control.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage111_native_tile_boundary.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage112: phase-controlled CHR changes at multiple positions within one row.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage112_native_subscanline_sweep.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage113: correlate actual BGData.Read buffering with rendered same-frame tiles.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage113_native_prefetch.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage114: audit low/high CHR plane pairs observed in renderer.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage114_native_plane_pairs.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage115: verify two BGData records prepared at the previous scanline edge.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage115_native_scanline_carry.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage116: real $2005 fine scroll pixel-to-carried-buffer correspondence.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage116_native_fine_scroll.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage117: mid-render $2005 CPU writes and shifted BG buffer sources.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage117_native_dynamic_scroll.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage118: two $2005 X/Y writes with coarse horizontal increment.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage118_native_two_scrolls.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage119: real alternating nametable tile IDs and post-scroll XBuf pixels.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage119_native_nametable.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage124: actual attribute quadrant, palette selection and XBuf color on
# synthetic-only Mapper-4 ROM, with independent negative controls.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage124_native_quadrants.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage126: run four paired palette-only interventions on the SAME pinned
# FCEUX binary and reject an unchanged ROM falsely claiming one mutation.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage126_palette_delta.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage127: observe zero-CHR universal backdrop through four actually fetched
# attribute quadrants; modify backdrop, then reject an opaque-CHR control.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage127_transparent_bg.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage129: newppu generated OAM sprite0, CHR pattern, priority and PPU
# sprite-hit status linked to the actual final XBuf output.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage129_native_sprite_oam.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage131: real two-entry OAM selection, sprite0-hit and final framebuffer
# observation, including a forced both-transparent negative control.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage131_native_dual_sprite.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage133: native asymmetric CHR pixels, real fetched row, all OAM H/V
# flip combinations, and strict forged-attribute rejection controls.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage133_native_sprite_flips.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
# Stage135: observe real two-tile 8x16 sprite, parity-selected CHR bank,
# source-half reversal and sixteen XBuf samples in four controlled ROMs.
xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp' \
  python3 "$PROJECT/tools/run_stage135_native_sprite_8x16.py" \
    "$BUILD/src/fceux" "$RUNNER_TEMP"
printf 'STAGE99_PINNED_FCEUX_NATIVE_BUILD_PASS commit=%s opt_in_probe=yes real_fceux_linked=yes gameplay_raster_verified=no\n' "${PIN}"
