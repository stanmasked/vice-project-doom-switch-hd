# Stage 352 — preregistered RGB environment-only holdout (before capture)

**Protocol frozen before any original RGB frames 585–609 are captured or inspected.** GitHub commit `692d0f063c4a6aca53389de8e763cb8311e5e730` contains the scoring implementation and 12 fabricated-only tests. Do not edit mask boundaries, candidate shifts, confidence limits or the target window based on later test results. If the preregistered scoring yields an inconclusive interval or a qualified mismatch, record it explicitly without tuning.

## Held-out source input

Owner-private read-only original NTSC Vice: Project Doom ROM and taotao FM2 replay in the independently pinned FCEUX 2.6.5 classic PPU (NewPPU 0) environment. Fresh new 25-frame XBuf RGB capture **585–609**, 24 consecutive pairs. The previous Stage351 original 560–584 interval that motivated the new masks is **training/exploratory** and does not enter the held-out count.

## Frozen, exact RGB windows

All rectangles use half-open coordinates `(x0,x1,y0,y1)` in the original 256×240 native XBuf image:

| Mask | Exact source-image rectangle |
| --- | --- |
| left_env_upper | (0,52,20,98) |
| left_env_lower | (0,52,98,175) |
| right_env_upper | (195,255,20,98) |
| right_env_lower | (195,255,98,175) |

For each environment-only region independently compare integer shifts **-24 through +24** with the source-image RGB pixel mismatch fraction; require best mismatch <=0.16, second-best minus best >=0.045, and all four masks' best shifts identical. Predeclared inconclusive if any mask is blank/ambiguous or masks disagree.

For each qualified pair, compare its RGB shift to the inverse of the minimal signed **modulo-240** delta of the *first second-phase $2005 Y* source byte. Values 240–255 or an ambiguous 120-pixel step are **unsupported**, not reduced/forced. All contradictions and unsupported cases are counted, never filtered away. This is software register/image correlation, **not physical camera or vehicle speed**.

## Source authentication and retention

Before scoring, require an independently held SHA-256 of the **new manifest**, separately pinned previous Stage335 CPU and Stage341 classic PPU complete TSV digests, read-only FM2 completion, 261-frame original CPU/native event coverage, 25 authentic 256×240 GD RGB files, 150 independent RGB/palette probes and three whole indexed-palette planes; reject any source SHA mismatch. Do not use the private manifest's self-declared seals instead of independent owner-held pins.

The owner-private capture and numerical reports go to the canonical private Google Drive Project Evidence Archive. Public GitHub receives only source-free scripts, synthetic tests and safe counts. Never commit original ROM/FM2, private capture Lua, RGB pixels, raw CPU/PPU trace rows or owner-only digests.

**Pre-capture protocol status:** prepared and versioned, no Stage352 original 585–609 RGB results claimed. Subsequent source results belong in a separate results document without rewriting this preregistration.
