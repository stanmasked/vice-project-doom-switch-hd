# Stage 187 — reproducibility check across two private FCEUX replays

The existing sealed single-session workflow can relate a 41-image
RGB roadway sample series to all 321 original CPU/PPU writer frames.
It cannot independently establish that a source road profile is
reproducible across separate runs, or that a difference is caused
by game dynamics rather than capture instability.

`tools/audit_private_dual_road_ppu_replay.py` supports:

**Verify two existing private captures** (this is an evidence equality
check, not proof that two original FCEUX processes really ran):

```bash
python3 tools/audit_private_dual_road_ppu_replay.py \
  --rom /private/owned_game.nes \
  --movie /private/owner_movie.fm2 \
  --legacy-numeric-report /private/road_geometry_600_920.json \
  --capture-a /private/run_a \
  --capture-b /private/run_b
```

**Execute and validate two new independent FCEUX processes** in fresh,
owner-private directories:

```bash
python3 tools/audit_private_dual_road_ppu_replay.py \
  --execute --rom /private/owned_game.nes \
  --movie /private/owner_movie.fm2 \
  --legacy-numeric-report /private/road_geometry_600_920.json \
  --capture-a /private/new_run_a \
  --capture-b /private/new_run_b
```

In both cases the full SHA-256 source/asset seal, complete 41/321
RGB/PPU join and 37/4 legacy-mask numerical reproduction are verified
**separately for each original capture** before comparison. Then the
host requires exactly matching rendered RGB bytes (not merely
matching gray edges), road masks, all 1,284 CPU writer values and
frame-relative phases, 321 RAM samples and relative CPU frame
durations. The raw **absolute** CPU cycle epoch is deliberately not
compared because different processes can start with different CPU
clock offsets.

A pre-existing duplicate directory cannot independently prove two
distinct emulator processes ran. Only `--execute` actually launches
the two real processes and can report its own orchestration.
Even then, the results don't establish source camera velocity,
effective PPU raster scroll, car road collision or world geometry.

No original source RGB data, unpublished roadway coordinates, source
CPU cycles or SHA-256 file digests are ever displayed or committed.
Public tests fabricate NES/FM2 inputs and 41×4 RGB rows; CPU timestamps
and film frames are invented. Neither the owner-private ROM/FM2 nor
original source has been replayed by adding these tests alone.


## Stage 320 — fresh-source dual replay mode

The existing default mode remains strict: it still requires `--legacy-numeric-report` and the exact Stage186 legacy comparison. A separate `--fresh-source-only` mode is now available for two sealed source captures when the old hashless numeric report cannot be authenticated. It validates each fresh-source join, compares all 41 RGB slots byte-for-byte, all 321 CPU-frame records, 1,284 writer values/phases, post-frame RAM samples and per-frame CPU lengths, while normalizing absolute CPU-cycle epochs.

Example using two already-sealed private directories:

```bash
python3 tools/audit_private_dual_road_ppu_replay.py \
  --rom /private/owned_original.nes \
  --movie /private/owner_fm2.fm2 \
  --capture-a /private/fresh_capture_a \
  --capture-b /private/fresh_capture_b \
  --fresh-source-only
```

Add `--execute` to have the command launch two separate local FCEUX processes into two new private directories. The output explicitly states that the legacy report was not compared and that no legacy-exact-match claim is made. This path does not replace the strict legacy-gated replay mode.

Local original-source investigation has now run two independent FCEUX 2.6.5 processes and observed byte-identical RGB payloads, CPU writer values, RAM samples and frame-relative phases. The old hashless road report still differs in three complete records, so the strict legacy replay gate remains blocked. Effective PPU scroll, camera speed and collision geometry are not proven.
