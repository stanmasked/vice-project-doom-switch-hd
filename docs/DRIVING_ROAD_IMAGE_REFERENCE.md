# Stage 167 — Original roadway image-space measurements

Seven example cross-sections documented from owner-private original
USA Vice: Project Doom ROM/FM2 FCEUX RGB frames. The existing
[original transition contract](ORIGINAL_STAGE_TRANSITION_CONTRACT.md)
reports 41 captured frames (600–920 at 8-frame cadence), 37 usable
cross-sections and four rejected ambiguous samples. **These seven examples
are not the complete set of 37 usable observations.** The median used
at least three of approximately Y=120,140,160,180 in the original 256×240
RGB image.

| FM2 frame | Approx left | Approx inclusive right | Width | Center |
|---:|---:|---:|---:|---:|
| 600 | 66 | 188 | 123 | 127.0 |
| 744 | 66 | 188 | 123 | 127.0 |
| 760 | 82 | 173 | 92 | 127.5 |
| 784 | 98 | 156 | 59 | 127.0 |
| 800 | 100 | 155 | 56 | 127.5 |
| 840 | 84 | 171 | 88 | 127.5 |
| 920 | 116 | 203 | 88 | 159.5 |

The observed neutral roadway fill narrows and widens, and its image
center shifts toward the right by 32.5 original pixels between these
selected frames 600 and 920. Screenshot color segmentation can be affected
by sprite occlusion, transitions and palette effects.

`game_core/driving_road_reference.hpp` preserves these original numeric
observations, with **exact-frame lookup only** and no guessed interpolation.
`toHdImageSpace()` maps source X positions to the 1280-wide display at
5× scale, preserving inclusive right bounds. It is not a camera, physics
or collision-coordinate conversion. The original 240→720 vertical image
scale is 3×, but the median spans several source rows, so no exact
pixel Y is asserted for the observation.

The regression test verifies observed widths and centers, exact frame
identities, HD image scaling and rejection of unobserved frames. No ROM,
FM2, graphics, CHR, PPU snapshots or original screenshots are committed.

**Next:** correlate these image-space road observations with independently
captured $2005 writers, source execution at $E8DE/$E369 and renderer/scroll
phases. Do not use these visible RGB boundaries as an authentic roadway
collision mesh or speed model without new evidence.
