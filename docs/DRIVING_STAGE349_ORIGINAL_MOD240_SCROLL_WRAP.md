# Stage 349 — 240-pixel PPU vertical-wrap model across three original RGB windows

## Original-source evidence retained and reauthenticated

Three **separately reproduced** owner-private original FCEUX v2.6.5 classic PPU captures cover exact 25-frame windows **420–444, 445–469, and 470–494**, totaling 75 native 256×240 RGB frames and 72 adjacent frame comparisons. Each window has 25 sampled live RAM `$0D` / first second-phase `$2005` Y / classic temporary PPU vertical states and four independent masked non-HUD RGB texture regions. Prior Stage344/346/347 source member hashes, external owner-private original CPU and PPU seals, ZIP integrity and Google Drive readback receipts were verified. No synthetic game pixels substitute for any original raster sample.

## A single model explains the previously observed register discontinuity

At Stage347 one original transition moved the background **+2 screen pixels** even though the first signed **8-bit** `$2005` Y step appeared as **−18**, contradicting a simple one-to-one register/pixel rule. Stage348 scanned all shifts −24…+24 in the four independent RGB areas and unambiguously found exactly +2 in each; the +18-pixel hypothesis produced much worse pixel mismatches.

The original first-vertical-scroll samples across all 75 captured frames are within the ordinary **0…239** interval. Instead of treating a conventional NES vertical scroll position as an arbitrary signed 8-bit difference, calculate the minimal signed vertical difference **modulo 240**:

```python
def scroll_step_240(old_y: int, new_y: int) -> int:
    if not (0 <= old_y < 240 and 0 <= new_y < 240):
        raise ValueError('outside verified ordinary NES scroll range')
    step = ((new_y - old_y + 120) % 240) - 120
    if step == -120:
        raise ValueError('half-period displacement is ambiguous')
    return step
```

This accounts for the one apparent signed-8-bit discontinuity by wrapping over a **240-pixel nametable height**, rather than inventing an abrupt increase in physical background motion. NESdev describes the PPU's vertical nametable wrapping (coarse Y last ordinary row 29 and nametable change) in [PPU scrolling](https://www.nesdev.org/wiki/PPU_scrolling). This public NES behavior is explanatory context, while the three bounded original-image comparisons are independent project evidence.

| Independently captured original image frames | Adjacent pairs | Image shifts match signed 8-bit Y steps | Image shifts match modulo-240 Y steps |
| --- | ---: | ---: | ---: |
| 420–444 | 24 | 24 | 24 |
| 445–469 | 24 | 24 | 24 |
| 470–494 | 24 | 23 | 24 |
| **Total** | **72** | **71** | **72** |

Observed background motion counts across the 72 adjacent pairs: **11 stationary**, **31 at +1 pixel**, and **30 at +2 pixels**. The modulo-240 model agrees with the independently selected four-band image shift for **72/72** pairs. This is a strong bounded correlation consistent with ordinary NES vertical scroll wrapping, **not** a proof of all game levels, CPU/PPU dot positions, split-scroll raster paths, attribute-table byte values 240…255, nametable mirroring, camera physics, road geometry, steering or collisions.

## Fail-closed public research tooling

- `tools/audit_private_stage349_periodic_scroll.py`: requires all three exact owner-private frame windows, independently sealed individual manifests and Stage335 CPU/Stage341 PPU trace digests, reexecutes the original per-pixel four-region source checks and returns only aggregate counts. Rejects ambiguous ±120-pixel paths and input Y bytes 240…255; these cannot be silently folded into this ordinary 240-pixel model.
- `tests/test_stage349_periodic_scroll.py`: **16 manufactured-only regression tests**, including valid 240 wrap, misleading −18 signed-8-bit delta, out-of-range attribute-table scroll bytes, false universality claims, missing/duplicate windows and tampered pixel motion.
- `docs/stage349_public_aggregate.json`: safe bounded counts only, no original RGB, ROM/FM2, source SHA-256, raw PPU cycles, gameplay registers or full private paths.

## Owner-private evidence and reproducibility

- [Original window 420–444 ZIP](https://drive.google.com/file/d/1a4JoMHf4wnd6QoJ3gEnVNZsuO46W3Gc0/view)
- [Original window 445–469 ZIP](https://drive.google.com/file/d/1hfVZYeBSwIERdx1D5XW6pIZxtT0wos4K/view)
- [Original window 470–494 ZIP](https://drive.google.com/file/d/1khw-pYXTVDGbmimSny4QlZKIwI6P9osO/view)

The original sources, manifest SHA-256 and private aggregate stay exclusively in the owner-private Project Evidence Archive, with readback SHA and ZIP CRC. Public CI may only run ROM-free fabricated tests. PR #99 stays Draft and `main` is untouched.

## Next research gate

Independently capture and validate additional consecutive RGB windows with scroll changes and alternate render/split phases; compare the observed frame motion with effective classic PPU Y plus nametable selection, particularly at page boundaries. Do not change driving controls, collision or road perspective solely from this register-image correspondence.
