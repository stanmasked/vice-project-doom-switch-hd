# Stage 185 — reproduce original roadway RGB masks in same session

The older source-observation report recorded an exact neutral road-gray
RGB color **(117,117,117)** over FCEUX rendered image rows
120,140,160,180. Its 41 images at frames 600..920 yielded 37 accepted
median visible road X-intervals, while frames 712,720,728,736 were
ambiguous. These image-space values are not road collision or
original effective scroll coordinates.

Stage184 obtains the relevant RGB scanlines **fresh**, from the same
FCEUX process, source ROM and FM2 playback as the independently timed
321-frame, 1,284-write PPU CPU trace. Its full original private RGB
file and raw PPU evidence are sealed together by Stage183's original
ROM/FM2 full-file SHA-256 check.

Now `tools/audit_private_road_mask_reproduction.py` remeasures only
the exact RGB road-gray occurrences. For each of four 256px source
rows, it rejects spans shorter than 30 or longer than 200 pixels.
If at least three rows are valid, it uses the integer median X
endpoints; otherwise the frame is explicitly ambiguous.

The private CLI has **hard failure** unless all 41 newly measured
statuses, left/right bounds, widths, centers, valid-row counts, and
the seven previously published frame anchors match the old private
numeric report. The capture's sealed CPU/frame-clock/PPU identity is
checked before any RGB comparison.

Example, with owner-only local source paths:

```bash
python3 tools/run_private_road_ppu_321.py \
  --rom /private/owned_original.nes \
  --movie /private/owner_fm2.fm2 \
  --output /private/new_same_session_ppu_rgb
python3 tools/audit_private_road_mask_reproduction.py \
  --rom /private/owned_original.nes \
  --movie /private/owner_fm2.fm2 \
  --private-dir /private/new_same_session_ppu_rgb \
  --legacy-numeric-report /private/road_geometry_600_920.json
```

The old numeric report's own SHA-256 identity remains *unproven*
because it was created without a hash. Successful numeric
reproduction from the **newly sealed** same-session RGB capture is
stronger evidence but not retroactive cryptographic provenance for
the old artifact.

Only **synthetic** RGB pixels and invented source dimensions are used
by public tests. No private image data, original ROM, FM2, hash or
unpublished 37-frame road coordinates should enter GitHub.
The new actual original-game FCEUX run and comparison have **not**
been executed/confirmed merely by passing CI.
