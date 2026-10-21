# Stage 171 — measured road-image shape features (not car physics)

The already stored **numeric-only** owner-private original FCEUX Stage1-1
road-mask report was independently checked: 41 sample slots, 37
accepted, four ambiguous (frames 712,720,728,736), no callback gaps.
Seven published image-space examples and the summary extrema agree.
It has no ROM or FM2 SHA hashes, so cross-session identity cannot be
proven from this file by itself.

`tools/audit_private_road_profile_features.py` accepts this numeric
report, revalidates it using Stage170's strict reader, then summarizes
only **contiguous accepted sample runs** and *observed image-space*
changes. It does not output original RGB pixels, per-frame image
boundaries, road tiles, source ROM, input movie, PPU snapshot or trace.

Two accepted runs can be measured: frames **600–704** (14 samples)
and **744–920** (23 samples). The gap **712–736** remains explicitly
ambiguous. No interpolated geometry or guessed road boundary can
be accepted across the gap.

The original numeric observations show:
- Width decreases **67 original-image pixels** between documented
  frames 744 and 800 (123 to 56).
- Width increases **32 pixels** between 800 and 840 (56 to 88).
- Road *image-space* center moves **32 pixels** between 864 and 904
  (127.5 to 159.5), while the sampled widths are both 88.

These trends can inform visual art direction for the independent
HD driving prototype. They are **not** proof of camera/world velocity,
car lateral speed, collision boundaries, 3D road curvature, or the
original graphical layer's exact PPU scroll phase. No renderer or
current synthetic car mechanic is modified here.

Run locally against the numeric-only report:

```bash
python3 tools/audit_private_road_profile_features.py \
  --numeric-report /private/road_geometry_600_920.json \
  --output /private/road_image_profile_summary.json
```

CI tests use fabricated frame coordinates and assert the 14/23
contiguous segments, positive/negative width changes, image-center
shift, gap preservation, leak-free output and source-report rejection.
