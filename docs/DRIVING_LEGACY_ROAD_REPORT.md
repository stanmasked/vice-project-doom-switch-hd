# Stage 170 — validate existing owner-private 41-frame road report

The user already owns a local numeric aggregate created from original
FCEUX 2.6.5 Stage1-1 RGB captures and not uploaded to the GitHub
repository. Its schema is `vice-stage1-private-road-mask-scan-v1`.

The report covers 600–920 inclusive at eight-frame cadence (41 slots),
with 37 accepted road-gray measurements and four rejected ambiguous
image frames: **712,720,728,736**. Only previously published numeric
cross-sections are used as sanity anchors. The per-slot source RGB
buffers and FCEUX original image files remain private.

Run against the local numeric file only:

```bash
python3 tools/audit_private_legacy_road_geometry.py \
  --numeric-report /private/road_geometry_600_920.json \
  --summary /private/validated_road_summary.json
```

The strict legacy audit independently recalculates all integer widths
and half-pixel centers from accepted left/right RGB color mask bounds,
refuses inferred road bounds on ambiguous frames, checks callback
continuity, all 41 ordered frame indices, summary extrema and seven
previously published road-image examples.

The resulting summary has counts and explicit limitations, not
original FM2, ROM, PPU traces or copyrighted pixels. The existing
legacy aggregate contains **no independently verifiable source ROM/FM2
SHA hashes**, so validating it cannot establish ROM/FM2 cross-session
identity. This is intentionally separate from Stage169's full
two-source hash-identity join. The latter still needs the independently
captured 321-frame PPU numeric report and valid private identifiers.

The public regression suite generates independent invented fixture
data and tests malformed frames, rejected regions, summary disagreement,
width/center arithmetic, input provenance, and data-field privacy.

No original camera velocity, collision mesh, original sprites, PPU
scanline/dot timing, or effective scroll has been recovered by this test.
