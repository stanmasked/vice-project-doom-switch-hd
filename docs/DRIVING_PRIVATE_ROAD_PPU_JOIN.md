# Stage 186 — complete same-session original road RGB / CPU-PPU join

Stages 181–185 establish *private-only* capture, source file identity,
frame clock, 41-slot RGB scanlines, 37/4 road-gray resegmentation and
sealing to original ROM + FM2 full-file SHA-256. This step connects
those evidence streams to Stage169's **existing strict joint
validator**, without exposing original pixels, local paths or source
movie hashes.

`tools/build_private_road_ppu_join.py` first re-verifies the
SHA-256-sealed private source evidence and **exact reproduction** of
all 41 legacy road-mask observations. It then constructs two
ephemeral in-memory numeric documents:

- a 41-slot `road_image_cross_sections_window_v1` document
  containing exactly the 37 accepted RGB boundaries and the four
  explicitly ambiguous frames;
- a 321-frame `ppu_cpu_writer_phases_v1` document containing the
  actual 1,284 $2005 CPU writer values, fixed store-instruction PCs,
  FCEUX-measured within-frame CPU phase and RAM $0D values.

Both ephemeral documents contain the **same ROM and FM2 full-file
SHA-256** from the already-sealed local source identity manifest.
The existing Stage169 `validate_complete_window` must then
confirm all 41 road frames, 321 CPU frames, source chronology,
37 accepted/4 ambiguous, four independently published PPU/RAM/road
anchor pairs and exact writer phase values. This is a **source-owned
image/CPU trace join**, not a guessed interpolation.

The full derived JSON documents are deliberately never written to
disk, printed, transmitted to GitHub or emitted as artifacts. Only
the redacted aggregate success marker is exposed after all gates.

Owner-local usage, after capture and sealing:

```bash
python3 tools/build_private_road_ppu_join.py \
  --rom /private/owned_original.nes \
  --movie /private/owner_fm2.fm2 \
  --private-dir /private/new_same_session_ppu_rgb \
  --legacy-numeric-report /private/road_geometry_600_920.json
```

**This original private-data command has not yet been executed.**
Passing public CI tests with invented NES/FM2 and arbitrary RGB
pixels is not confirmation of the original game's road mask.

Even a successful true original 321-frame join does **not**
prove effective PPU raster scroll, real source camera speed, world
geometry, enemies' position or original car collision physics.
Those require separate PPU latch/scanline and gameplay investigations.

The original Stage170 numeric file was created without SHA-256.
A matching fresh source-derived mask does not retroactively
authenticate that file; hence this distinction remains explicit.


## Stage 319 — fresh-source alignment without legacy substitution

A separate tool, `tools/audit_private_fresh_road_ppu_join.py`, verifies the **new, SHA-256-sealed same-session source baseline** without treating the old hashless road report as authenticated. It rechecks the source/capture seal, derives the 41 RGB slots and 321 CPU-frame records in memory, then runs the existing Stage169 numeric alignment validator over the 37 accepted image-space intervals and four independently published cross-source anchors.

This is a distinct research result, not a relaxation of the strict Stage186 gate. The strict `tools/build_private_road_ppu_join.py` still requires exact reproduction of the legacy report and must continue to fail closed when that comparison differs. The owner-private original capture has now been repeated in two independent FCEUX 2.6.5 processes: their 41-slot RGB payloads are byte-identical, as are all CPU writer values and post-frame RAM samples. The fresh-source alignment checks all 321 CPU frames, 1,284 writer events, and four road/PPU/RAM anchor pairs. The legacy numeric report remains a separate, unauthenticated comparison target; no legacy-exact-match claim is made.

Owner-local usage:

```bash
python3 tools/audit_private_fresh_road_ppu_join.py \
  --rom /private/owned_original.nes \
  --movie /private/owner_fm2.fm2 \
  --private-dir /private/new_same_session_ppu_rgb
```

Only a redacted aggregate is printed. Raw RGB bytes, source hashes, private CPU cycles and numeric road coordinates remain local. Even this fresh-source alignment does not prove effective PPU scroll, camera speed or collision geometry.
