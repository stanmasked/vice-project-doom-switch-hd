# Stage 169 — full Stage 1-1 private numeric evidence gate

Stage168 aligned four already published pairs; it did not check a full
window. This new auditor adds an **optional complete-window mode** for
the original, independently collected FCEUX Stage 1-1 evidence.

Two local numeric-only JSON reports must refer to the **same ROM and FM2
SHA-256 identity**, with zero-based original movie-frame labels.

The road report is the same identity header used at Stage168 but uses
`schema=road_image_cross_sections_window_v1` and a `slots` array of
**exactly 41** entries at frames 600,608,...,920. Each slot is either
`{"frame":600,"status":"accepted","left":66,"right":188}` or
`{"frame":608,"status":"ambiguous"}` (this ambiguous-frame example is
an **invented schema illustration**, not evidence frame 608 was rejected).
The report must contain **37 accepted, four ambiguous** and preserve all
seven already published image-space frame examples. An ambiguous slot
cannot contain inferred coordinate values.

The CPU writer report keeps the Stage168
`ppu_cpu_writer_phases_v1` format, but must contain **all 321**
contiguous frames 600 through 920 with four exact writer PCs
`E8EC,E8F1,E369,E36C`, values `00,changing,00,00`,
CPU cycle phase and the separately sampled postframe RAM $0D.
Each accepted image slot must join to a corresponding CPU record;
all documented original image/PPU anchors must match.

Run only where the user's **actual original private numeric evidence**
exists:

```bash
python3 tools/audit_private_road_ppu_window.py \
  --road-window /private/road_window_numeric.json \
  --ppu /private/ppu_writer_numeric.json \
  --output /private/sanitized_summary.json
```

The resulting summary contains only *counts, booleans and frame window*:
no source hash, absolute paths, screenshot pixels, ROM bytes, FM2, CPU
event dumps, game sprites or CHR/PPU memory. The CLI is not automatically
run on any proprietary inputs by public GitHub CI; CI executes only
self-contained invented-data negative/positive fixtures. This validator
cannot determine whether its numeric inputs were genuinely captured;
its strongest assurance is consistency with independently verified
anchor values and hash identity supplied by the private captures.

**Not established:** exact effective PPU raster scroll, actual camera
velocity, collision boundaries, opponent patterns, source-level scene
assembly and original Stage1-1 gameplay. This is an evidence intake gate
rather than an original-game restoration claim.
